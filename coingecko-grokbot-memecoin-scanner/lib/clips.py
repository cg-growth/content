"""Clipping (partial sells on the way up) for the PAPER book.
spec: "10%" | "25%" (of current qty) | "initial" (sell enough to recover cost) | "orig:20" (20% of ORIGINAL qty) | "all".
Liquidity-aware: each tranche keeps constant-product price impact <= MAX_IMPACT; the excess is queued as tranches
(executed by the risk engine every TRANCHE_GAP_S). Realistic fees: per-chain gas+tip, DEX fee, CP slippage."""
import json, time, sys
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
sys.path.insert(0, _ROOT + "/telegram"); sys.path.insert(0, _ROOT + "/lib")
import core
GAS_USD = {"solana": 0.003 + 0.02, "base": 0.03, "bsc": 0.06, "robinhood": 0.03, "eth": 2.5}   # gas + priority tip per swap
MAX_IMPACT = 0.025; TRANCHE_GAP_S = 90; FEE_WARN = 0.10
SCHEMA = """create table if not exists position_meta(ca text primary key, orig_qty real, initial_usd real, initial_out integer default 0,
  clips integer default 0, clip_realized real default 0, auto_clip integer default 0, house_since text);
create table if not exists clip_tranches(id integer primary key autoincrement, ca text, qty real, due real, reason text, status text default 'open', created text);"""
def init(c): c.executescript(SCHEMA); return c
def meta(c, ca):
    init(c); m = c.execute("select * from position_meta where ca=?", (ca,)).fetchone()
    if m: return m
    p = c.execute("select * from positions where ca=?", (ca,)).fetchone()
    if not p: return None
    b = c.execute("select coalesce(sum(qty),0) q, coalesce(sum(usd_notional),0) u from trades where ca=? and side='buy'", (ca,)).fetchone()
    import os as _o; ac = 1 if _o.environ.get("BOOK") == "auto" else 0   # AI book: auto-clip ON by default
    c.execute("insert or ignore into position_meta(ca,orig_qty,initial_usd,auto_clip) values(?,?,?,?)", (ca, max(b["q"], p["qty"]), max(b["u"], p["cost_usd"]), ac)); c.commit()
    return c.execute("select * from position_meta where ca=?", (ca,)).fetchone()
def gas(net): return GAS_USD.get(net, 0.05)
def fill(value_mid, liq, net):
    """-> dict(gross, dex_fee, impact_usd, gas, net, drag_pct, impact_pct) for selling tokens worth value_mid at mid."""
    y = (liq or 0) / 2
    if y <= 0: out = 0.0
    else: out = y * value_mid / (y + value_mid)
    dex = out * core.FEE; g = gas(net); netp = max(0.0, out - dex - g)
    return {"gross": value_mid, "impact_usd": value_mid - out, "impact_pct": (1 - out / value_mid) if value_mid else 0, "dex_fee": dex, "gas": g,
            "net": netp, "drag_pct": (value_mid - netp) / value_mid if value_mid else 1}
def max_tranche_usd(liq, imp=MAX_IMPACT): y = (liq or 0) / 2; return y * imp / (1 - imp) if y > 0 else 0.0
def min_clip_for_fees(liq, net, cap=FEE_WARN):
    """smallest clip (USD at mid) where gas+dex+impact <= cap"""
    for v in (5, 10, 20, 35, 50, 75, 100, 150, 250, 400, 600, 1000):
        if fill(v, liq, net)["drag_pct"] <= cap: return v
    return None
def qty_for(c, p, m, q, spec):
    spec = str(spec).strip().lower()
    if spec in ("all", "100%"): return p["qty"]
    if spec == "initial":
        need = (m["initial_usd"] if m else p["cost_usd"]); lo, hi = 0.0, p["qty"]
        if fill(hi * q["price"], q["liquidity"], p["network"])["net"] < need: return None
        for _ in range(40):
            mid = (lo + hi) / 2
            if fill(mid * q["price"], q["liquidity"], p["network"])["net"] < need: lo = mid
            else: hi = mid
        return hi
    if spec.startswith("orig:"): return min(p["qty"], (m["orig_qty"] if m else p["qty"]) * float(spec[5:]) / 100)
    return p["qty"] * float(spec.rstrip("%")) / 100
def _execute(c, p, q, qty, source, kind):
    """Sell qty now with realistic fill; updates position, ledger, meta. -> (text, fill dict)"""
    v = qty * q["price"]; f = fill(v, q["liquidity"], p["network"]); frac = min(1.0, qty / p["qty"])
    basis = p["cost_usd"] * frac; pnl = f["net"] - basis; t = core.now(); newcash = core.cash(c) + f["net"]
    fp = f["net"] / qty if qty else 0
    c.execute("update account set v=? where k='cash'", (newcash,))
    if frac >= 0.999999: c.execute("delete from positions where ca=?", (p["ca"],))
    else: c.execute("update positions set qty=qty-?, cost_usd=cost_usd-?, updated_at=? where ca=?", (qty, basis, t, p["ca"]))
    c.execute("insert into trades(ts,side,ca,network,pool,symbol,usd_notional,qty,mid_price,fill_price,slippage_pct,fee_usd,liquidity_usd,realized_pnl,cash_after,tag,confidence,human_score,source) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (t, "sell", p["ca"], p["network"], p["pool"], p["symbol"], f["net"], qty, q["price"], fp, f["impact_pct"] * 100, f["dex_fee"] + f["gas"], q["liquidity"], pnl, newcash,
               p["entry_tag"], p["entry_confidence"], p["entry_human_score"], f"{source}|{kind}"))
    m = meta(c, p["ca"])
    if m and frac < 0.999999:
        io = m["initial_out"] or (1 if (m["clip_realized"] or 0) + f["net"] >= (m["initial_usd"] or 1e18) * 0.98 else 0)
        c.execute("update position_meta set clips=clips+1, clip_realized=clip_realized+?, initial_out=?, house_since=coalesce(house_since, case when ?=1 then ? end) where ca=?",
                  (f["net"], io, io, t, p["ca"]))
        if io:   # risk: SL at least breakeven on the remainder
            c.execute("update risk_plans set sl_px=max(sl_px, entry_px), be_moved=1 where ca=?", (p["ca"],))
    c.commit()
    return pnl, f, frac, newcash
def clip(c, target, spec, source="clip", allow_split=True):
    init(c)
    ca, _ = core.resolve(target, c, prefer_ca=target)
    p = c.execute("select * from positions where ca=?", (ca,)).fetchone() if ca else None
    if not p: return f"❌ No open position for <b>{core.esc(target)}</b>."
    q = core.cached_quote(p["ca"], p["network"]) or core.quote(p["ca"], p["network"])
    if not q or not q.get("price"): return "❌ No price right now; try again."
    if q.get("liquidity") is None: q = core.quote(p["ca"], p["network"]) or q
    m = meta(c, ca); qty = qty_for(c, p, m, q, spec)
    if qty is None: return f"❌ Position value (after fees) is below your initial ${m['initial_usd']:,.2f} — can't take initial out yet."
    if qty <= 0: return "❌ Nothing to clip."
    cap_usd = max_tranche_usd(q["liquidity"]); want_usd = qty * q["price"]; notes = []
    pv = p["qty"] * q["price"]
    if spec != "all" and q.get("liquidity") and pv > q["liquidity"] * 5:   # position "worth" >5x the pool: price/qty artifact, refuse
        return f"❌ Clip refused: position value ${pv:,.0f} vs pool ${q['liquidity']:,.0f} (price sanity)."
    tranches = 1
    if allow_split and cap_usd > 0 and want_usd > cap_usd * 1.05:
        now_qty = cap_usd / q["price"]; rest = qty - now_qty; tranches = min(20, 1 + int(rest * q["price"] // cap_usd) + (1 if (rest * q["price"]) % cap_usd > 1e-9 else 0))
        due = time.time() + TRANCHE_GAP_S; per = rest / max(1, tranches - 1)
        for i in range(tranches - 1):
            c.execute("insert into clip_tranches(ca,qty,due,reason,created) values(?,?,?,?,?)", (ca, per, due + i * TRANCHE_GAP_S, f"{spec} split", core.now()))
        notes.append(f"🧊 Thin pool: ${want_usd:,.0f} would move price >{MAX_IMPACT*100:.1f}%. Split into {tranches} tranches of ≤${cap_usd:,.0f}, one every {TRANCHE_GAP_S}s (ghost-liquidity protection).")
        qty = now_qty
    pnl, f, frac, newcash = _execute(c, p, q, qty, source, "clip" if frac_lt(qty, p) else "exit")
    m = meta(c, ca)
    if f["drag_pct"] > FEE_WARN:
        mn = min_clip_for_fees(q["liquidity"], p["network"])
        notes.append(f"⚠️ Fee erosion: fees+impact ate {f['drag_pct']*100:.1f}% of this clip." + (f" Clip ≥${mn} to keep drag under {FEE_WARN*100:.0f}%." if mn else ""))
    house = " · 🏠 <b>HOUSE MONEY</b> (initial out, SL ≥ breakeven)" if m and m["initial_out"] else ""
    return (f"✂️ <b>PAPER CLIP</b> {core.esc(p['symbol'])} {frac*100:.1f}% of position ({core.esc(str(spec))})\n<code>{ca}</code>\n"
            f"{qty:,.4f} tokens @ mid ${q['price']:.8g} → net <b>${f['net']:,.2f}</b>\n"
            f"Fee drag {f['drag_pct']*100:.2f}%: impact ${f['impact_usd']:,.2f} ({f['impact_pct']*100:.2f}%) · DEX ${f['dex_fee']:,.2f} · gas+tip ${f['gas']:.2f}\n"
            f"Realized on clip: <b>{pnl:+,.2f}</b> · clips {m['clips'] if m else 1} · from clips ${(m['clip_realized'] if m else f['net']):,.2f}{house}\nCash ${newcash:,.2f}"
            + ("\n" + "\n".join(notes) if notes else ""))
def frac_lt(qty, p): return qty < p["qty"] * 0.999999
def process_tranches(c, log=print):
    init(c); out = []
    for t in c.execute("select * from clip_tranches where status='open' and due<=? order by due", (time.time(),)).fetchall():
        p = c.execute("select * from positions where ca=?", (t["ca"],)).fetchone()
        if not p: c.execute("update clip_tranches set status='void' where id=?", (t["id"],)); c.commit(); continue
        q = core.cached_quote(p["ca"], p["network"]) or core.quote(p["ca"], p["network"])
        if not q: continue
        if q.get("liquidity") is None: q = core.quote(p["ca"], p["network"]) or q
        cap = max_tranche_usd(q["liquidity"]) / q["price"]; qty = min(t["qty"], cap, p["qty"])
        pnl, f, frac, _ = _execute(c, p, q, qty, "tranche", "clip")
        left = t["qty"] - qty
        if left > 1e-12: c.execute("update clip_tranches set qty=?, due=? where id=?", (left, time.time() + TRANCHE_GAP_S, t["id"]))
        else: c.execute("update clip_tranches set status='done' where id=?", (t["id"],))
        c.commit(); out.append((p["symbol"], f["net"], pnl)); log("tranche", p["symbol"], round(f["net"], 2))
    return out
def house(c, ca):
    try: m = init(c).execute("select initial_out, clips, clip_realized from position_meta where ca=?", (ca,)).fetchone(); return m
    except Exception: return None
