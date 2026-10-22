#!/usr/bin/env python3
"""Paper risk engine. Auto: SL (vol-aware grace), breakeven move, trailing stop, danger exits. Ask (TG buttons): dynamic TP, time stop.
DRY: RISK_DRY=1 -> no Telegram, no sells (logs only)."""
import json, os, sys, time, statistics, datetime as D
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
sys.path.insert(0, _ROOT + "/lib"); import common as C
import core, addr as A, clips as CL
log = C.logger("risk"); DRY = os.environ.get("RISK_DRY") == "1"
mc = C.mdb(); below = {}; last = {"tp": {}, "trades": {}, "hp": {}, "rest_px": {}}; seen_tx = set()
BOOK = os.environ.get("BOOK", "human")   # 'auto' = AI autonomous book (PAPER_DB=auto.db): everything automatic
if BOOK == "auto": log = C.logger("risk-auto")
def cfg():
    k = C.risk_cfg()
    if BOOK == "auto":
        try:
            pol = json.load(open(f"{C.BASE}/auto/policy.json"))
            for sec, v in (pol.get("risk_overrides") or {}).items():
                if isinstance(v, dict): k.setdefault(sec, {}).update(v)
        except Exception: pass
    return k
def notify(text, kb=None, ca=None):
    if BOOK == "auto":   # read-only book: queue a quiet notice (autotrader batches to <=1 TG msg/min)
        try:
            import sqlite3 as _s; n = _s.connect(f"{C.BASE}/auto.db", timeout=30); n.execute("pragma busy_timeout=30000")
            n.execute("create table if not exists notices(id integer primary key autoincrement, ts text, text text, sent integer default 0)")
            n.execute("insert into notices(ts,text) values(?,?)", (C.now_iso(), "🤖 " + text)); n.commit(); n.close()
        except Exception as e: log("notice err", e)
        return {"ok": True, "result": {"message_id": 0}}
    if DRY: log("DRY notify:", text.replace("\n", " | ")[:300]); return {"ok": True, "result": {"message_id": 0}}
    own = core.owner()
    if not own: return {}
    r = core.send(own["chat_id"], text, reply_markup=kb)
    if r.get("ok") and ca:
        c = core.db(); core.remember(c, own["chat_id"], r["result"]["message_id"], ca, "risk"); c.close()
    return r
def pos_kb(ca, auto=1):
    return {"inline_keyboard": [core.clip_row(ca), [{"text": "Sell 50%", "callback_data": f"s:50:{ca}"}, {"text": "Sell all", "callback_data": f"s:all:{ca}"}],
        [{"text": "⚙️ Adjust SL/TP", "callback_data": f"ra:{ca}"}, {"text": ("⏸ Disable auto" if auto else "▶️ Enable auto"), "callback_data": f"rx:{ca}"}],
        [{"text": "📊 Positions", "callback_data": "p"}]]}
def event(c, ca, kind, detail, action):
    c.execute("insert into risk_events(ts,ca,kind,detail,action) values(?,?,?,?,?)", (C.now_iso(), ca, kind, json.dumps(detail, default=str), action)); c.commit()
def ensure_plan(c, p, new_notify):
    r = c.execute("select * from risk_plans where ca=?", (p["ca"],)).fetchone()
    if r: return r
    k = cfg(); entry = p["cost_usd"] / p["qty"]; slp = k["stop_loss"]["pct"]
    tp = [{"multiple": l["multiple"], "sell_pct": l["sell_pct"], "clip": l.get("clip", f"{l['sell_pct']}%"), "status": "open"} for l in k["take_profit"]["base_ladder"]]
    c.execute("insert into risk_plans(ca,network,pool,entry_px,opened_at,sl_pct,sl_px,tp,peak_px,auto,updated_at) values(?,?,?,?,?,?,?,?,?,1,?)",
              (p["ca"], p["network"], p["pool"], entry, p["opened_at"], slp, entry * (1 + slp / 100), json.dumps(tp), entry, C.now_iso())); c.commit()
    try: C.backfill(mc, p["network"], p["pool"], ("1m", "15s"))
    except Exception as e: log("backfill", e)
    log("plan attached", p["symbol"], "entry", entry)
    if new_notify:
        notify(f"🛡 <b>Plan attached</b> {core.esc(p['symbol'])}\nSL {slp}% (needs 60s close below in first 10 min) · BE at 2x\n"
               f"TP (dynamic, asks you): " + " / ".join(f"{t['sell_pct']}% @ ~{t['multiple']}x" for t in tp) +
               f"\nTrailing {k['trailing_stop']['trail_pct']}% from peak after +{k['trailing_stop']['activate_at_gain_pct']}% (auto) · time stop asks at {k['time_stop']['hours']}h",
               pos_kb(p["ca"]), p["ca"])
    return c.execute("select * from risk_plans where ca=?", (p["ca"],)).fetchone()
def price(p):
    px, src = _raw_price(p)
    if not px: return px, src
    import ticks; spx, si = ticks.sane(p["ca"], p["pool"], px, src)   # SL/trail/clip/TP triggers use sanitized price
    return spx, (src if si.get("ok") else src + "~sanitized")
def _raw_price(p):
    lp = C.last_price(mc, p["ca"], 30)
    if lp: return lp[0], lp[1]
    t = last["rest_px"].get(p["ca"])
    if t and time.time() - t[1] < 15: return t[0], "rest"
    d = C.cg(f"/simple/networks/{p['network']}/token_price/{p['ca']}", None, mc)
    tp_ = (((d or {}).get("data") or {}).get("attributes", {}).get("token_prices") or {}); px = float(tp_.get(p["ca"]) or next((v for k, v in tp_.items() if A.same(k, p["ca"])), 0) or 0) or None
    if px: last["rest_px"][p["ca"]] = (px, time.time())
    return px, "rest"
def sell(c, p, amt, why, kind):
    if DRY: log("DRY sell", p["symbol"], amt, why); event(c, p["ca"], kind, {"why": why}, "dry"); return
    pc = core.db(); out = core.sell(pc, p["ca"], amt, source="risk-" + kind); pc.close()
    event(c, p["ca"], kind, {"why": why, "result": out[:200]}, "sold" if out.startswith("🔴") else "failed")
    notify(f"🤖 <b>AUTO {kind.upper()}</b> — {core.esc(why)}\n\n{out}", pos_kb(p["ca"]), p["ca"])
def ask(c, p, kind, sell_pct, reason, spec=None, level=None):
    if BOOK == "auto":   # no human in the loop: execute
        spec = spec or f"{sell_pct:g}%"; pc = core.db()
        out = CL.clip(pc, p["ca"], "all" if kind == "Time stop" else spec, source="auto-" + kind.split()[0].lower()); pc.close()
        event(c, p["ca"], kind, {"reason": reason, "spec": spec, "out": out[:200]}, "auto"); notify(f"<b>{kind}</b> {core.esc(p['symbol'])}: {core.esc(reason)}\n{out}"); return
    try: c.execute("alter table risk_prompts add column spec text")
    except Exception: pass
    try: c.execute("alter table risk_prompts add column level integer")
    except Exception: pass
    spec = spec or f"{sell_pct:g}%"
    cur = c.execute("insert into risk_prompts(ca,kind,sell_pct,reason,created,status,spec,level) values(?,?,?,?,?,'open',?,?)", (p["ca"], kind, sell_pct, reason, time.time(), spec, level)); c.commit()
    pid = cur.lastrowid; lab = "Take initial out" if spec == "initial" else f"Clip {spec.replace('orig:', '')}%" + (" of orig" if spec.startswith("orig:") else "")
    kb = {"inline_keyboard": [[{"text": f"✂️ {lab}", "callback_data": f"ry:{pid}"}, {"text": "✋ Hold", "callback_data": f"rh:{pid}"}, {"text": "⏭ Skip level", "callback_data": f"rk:{pid}"}],
                              [{"text": "🤖 Auto-clip ON", "callback_data": f"ac:{p['ca']}"}, {"text": "⚙️ Adjust", "callback_data": f"ra:{p['ca']}"}]]}
    notify(f"🎯 <b>{kind}</b> {core.esc(p['symbol'])}: {core.esc(reason)}\n{lab}?", kb, p["ca"]); event(c, p["ca"], kind, {"reason": reason, "spec": spec}, "asked")
def dyn_tp(p, plan, px):
    """Scale base ladder by volatility, momentum/flow, run-from-launch, liquidity depth."""
    k = cfg()["take_profit"]; cs = mc.execute("select o,h,l,c,t from ohlcv where pool=? and iv='1m' order by t desc limit 30", (p["pool"],)).fetchall()
    if len(cs) < 5: cs = mc.execute("select o,h,l,c,t from ohlcv where pool=? and iv='15s' order by t desc limit 60", (p["pool"],)).fetchall()
    f = {"vol": 1.0, "mom": 1.0, "run": 1.0, "liq": 1.0}
    if len(cs) >= 5:
        atr = statistics.mean((r["h"] - r["l"]) / r["c"] for r in cs if r["c"]); f["vol"] = max(0.8, min(1.8, 0.8 + atr * 8))
        slope = (cs[0]["c"] - cs[min(14, len(cs) - 1)]["c"]) / cs[min(14, len(cs) - 1)]["c"]
        tr = mc.execute("select ty, sum(usd) u from trades where pool=? and t>? group by ty", (p["pool"], time.time() - 300)).fetchall()
        b = sum(r["u"] or 0 for r in tr if r["ty"] == "b"); s = sum(r["u"] or 0 for r in tr if r["ty"] == "s"); flow = b / (b + s) if b + s else 0.5
        f["mom"] = 1.2 if (slope > 0 and flow > 0.6) else 0.85 if (slope < 0 and flow < 0.45) else 1.0; f["flow"] = round(flow, 2); f["slope"] = round(slope, 3)
    first = mc.execute("select o from ohlcv where pool=? order by t asc limit 1", (p["pool"],)).fetchone()
    if first and first["o"]: run = px / first["o"]; f["run"] = 0.8 if run > 20 else 0.9 if run > 8 else 1.0; f["run_x"] = round(run, 1)
    r = mc.execute("select r from prices where ta=? and r is not null order by t desc limit 1", (p["ca"],)).fetchone()
    if r and r["r"]: f["liq"] = 0.85 if r["r"] < 15000 else 1.1 if r["r"] > 100000 else 1.0
    m = f["vol"] * f["mom"] * f["run"] * f["liq"]; tp = json.loads(plan["tp"])
    for t in tp:
        if t.get("override"): continue
        i_ = tp.index(t); base = k["base_ladder"][i_]["multiple"] if i_ < len(k["base_ladder"]) else t["multiple"]
        t["multiple"] = round(max(k["min_multiple"], min(k["max_multiple"], 1 + (base - 1) * m)), 2)
    return tp, f
def check_trades(c, p, plan):
    """Insider/dev wallet sells via REST pool trades (WS trade feed has no wallet field)."""
    if time.time() - last["trades"].get(p["ca"], 0) < 20: return None
    last["trades"][p["ca"]] = time.time(); k = cfg()["danger"]
    d = C.cg(f"/networks/{p['network']}/pools/{p['pool']}/trades", None, mc) or {}
    sells = [x["attributes"] for x in d.get("data", []) if x["attributes"]["kind"] == "sell"]
    if not sells: return None
    import sqlite3; w = sqlite3.connect(f"{C.BASE}/wallets.db", timeout=30); w.execute("PRAGMA busy_timeout=30000")
    dev = (last["hp"].get(p["ca"]) or {}).get("dev")
    for s in sells:
        if s["tx_hash"] in seen_tx: continue
        seen_tx.add(s["tx_hash"]); a = A.norm(s["tx_from_address"], p["network"]); usd = float(s["volume_in_usd"] or 0)
        lab = w.execute("select label from wallets where address=?", (a,)).fetchone()
        ts = D.datetime.fromisoformat(s["block_timestamp"].replace("Z", "+00:00")).timestamp()
        if ts < D.datetime.fromisoformat(plan["opened_at"]).timestamp(): continue
        if usd >= k["insider_sell_min_usd"] and ((lab and lab[0] in k["insider_labels"]) or (dev and a == dev)):
            return f"{'dev' if dev and a == dev else lab[0]} wallet {a[:10]}… sold ${usd:,.0f}"
    return None
def check_honeypot(p):
    k = cfg()["danger"]; h = last["hp"].get(p["ca"])
    if h and time.time() - h["t"] < k["honeypot_check_min"] * 60: return h.get("flip")
    d = C.cg(f"/networks/{p['network']}/tokens/{p['ca']}/info", None, mc) or {}; a = (d.get("data") or {}).get("attributes") or {}
    prev = h.get("hp") if h else None; hp = a.get("is_honeypot")
    last["hp"][p["ca"]] = {"t": time.time(), "hp": hp, "dev": A.norm(a.get("developer_address") or "", p["network"]) or None, "flip": hp is True and prev is not True}
    return last["hp"][p["ca"]]["flip"]
RUG = {}
def pool_reserve(p):
    """Latest pool reserve USD: WS G1 'r' (<=60s) else REST pool endpoint (cached 15s)."""
    r = mc.execute("select r, t from prices where ta=? and r is not null and (pa=? or ? is null) order by t desc limit 1", (p["ca"], p["pool"], p["pool"])).fetchone()   # same pool only
    if r and time.time() - r["t"] <= 60: return float(r["r"]), "G1"
    k = ("pool", p["ca"]); h = last.get(k)
    if h and time.time() - h[1] < 15: return h[0], "rest"
    d = C.cg(f"/networks/{p['network']}/pools/{p['pool']}", None, mc) or {}
    v = ((d.get("data") or {}).get("attributes") or {}).get("reserve_in_usd")
    if v is None: return None, None
    last[k] = (float(v), time.time()); return float(v), "rest"
def check_rug(c, p, plan):
    """-> reason str when liquidity collapsed (confirmed on >=confirm_reads reads >=confirm_gap_s apart)."""
    k = cfg()["danger"].get("rug") or {}
    liq, src = pool_reserve(p)
    if liq is None: return None
    ent = c.execute("select max(liquidity_usd) from trades where ca=? and side='buy' and liquidity_usd>0", (p["ca"],)).fetchone()[0]
    win = mc.execute("select max(r) from prices where ta=? and r>0 and t>?", (p["ca"], time.time() - k.get("window_min", 10) * 60)).fetchone()[0]
    why = None
    if liq < k.get("floor_usd", 1000): why = f"pool liquidity ${liq:,.0f} < ${k.get('floor_usd',1000):,} floor"
    elif ent and liq <= ent * (1 - k.get("drop_from_entry_pct", 60) / 100): why = f"liquidity -{(1-liq/ent)*100:.0f}% vs entry (${ent:,.0f}→${liq:,.0f})"
    elif win and liq <= win * (1 - k.get("window_drop_pct", 60) / 100): why = f"liquidity -{(1-liq/win)*100:.0f}% in {k.get('window_min',10)}m"
    st = RUG.setdefault(p["ca"], [])
    if not why: st.clear(); return None
    if not st or time.time() - st[-1] >= k.get("confirm_gap_s", 15): st.append(time.time())
    return f"{why} [{src}]" if len(st) >= k.get("confirm_reads", 2) else None
def rug_exit(c, p, why):
    liq, _ = pool_reserve(p)
    if DRY: log("DRY rug exit", p["symbol"], why); event(c, p["ca"], "rug", {"why": why}, "dry"); return
    pc = core.db(); out = core.sell(pc, p["ca"], "all", source="risk-rug", rug_reason="rug/liquidity collapse", liq_override=liq or 0.0); pc.close()
    event(c, p["ca"], "rug", {"why": why, "liq": liq, "result": out[:200]}, "sold" if out.startswith("🔴") else "failed")
    notify(f"🚨 <b>AUTO EXIT — rug/liquidity collapse</b>\n{core.esc(why)}\nFilled into remaining reserve (constant-product).\n\n{out}", None, p["ca"])
    log("rug exit", p["symbol"], why)
def step(c, p, plan):
    k = cfg(); px, src = price(p)
    if not px: return
    e = plan["entry_px"]; mult = px / e; age = time.time() - D.datetime.fromisoformat(plan["opened_at"]).timestamp()
    peak = max(plan["peak_px"] or e, px); c.execute("update risk_plans set peak_px=?, updated_at=? where ca=?", (peak, C.now_iso(), p["ca"])); c.commit()
    auto = plan["auto"]
    rg = check_rug(c, p, plan)
    if rg: return rug_exit(c, p, rg)   # always automatic, no confirmation
    # --- danger exits (auto) ---
    dz = []
    rs = mc.execute("select r,t from prices where ta=? and r is not null and t>? order by t", (p["ca"], time.time() - k["danger"]["reserve_window_min"] * 60)).fetchall()
    if len(rs) >= 2:
        mx = max(r["r"] for r in rs); drop = (1 - rs[-1]["r"] / mx) * 100 if mx else 0
        if drop >= k["danger"]["reserve_drop_pct"]: dz.append(f"liquidity reserve fell {drop:.0f}% in {k['danger']['reserve_window_min']}m")
    it = check_trades(c, p, plan)
    if it: dz.append(it)
    if check_honeypot(p): dz.append("honeypot flag flipped to TRUE")
    if dz:
        if auto: return sell(c, p, "all", "; ".join(dz), "danger")
        if not below.get(("dz", p["ca"])): below[("dz", p["ca"])] = 1; notify(f"⚠️ <b>DANGER</b> {core.esc(p['symbol'])}: {core.esc('; '.join(dz))} (auto off)", pos_kb(p["ca"], 0), p["ca"])
    # --- breakeven ---
    if not plan["be_moved"] and mult >= k["stop_loss"]["breakeven_at_multiple"]:
        c.execute("update risk_plans set sl_px=?, be_moved=1 where ca=?", (e, p["ca"])); event(c, p["ca"], "breakeven", {"px": px}, "sl->entry")
        notify(f"🔒 {core.esc(p['symbol'])} hit {mult:.2f}x — stop moved to breakeven.", pos_kb(p["ca"], auto), p["ca"]); plan = c.execute("select * from risk_plans where ca=?", (p["ca"],)).fetchone()
    # --- stop loss (vol-aware grace) ---
    sl = plan["sl_px"]
    if px <= sl:
        if age < k["stop_loss"]["grace_minutes"] * 60:
            st = below.setdefault(p["ca"], time.time()); held = time.time() - st
            cl = mc.execute("select max(c) m from ohlcv where pool=? and iv='1s' and t>=?", (p["pool"], int(st))).fetchone()
            if held >= k["stop_loss"]["grace_confirm_seconds"] and (cl["m"] is None or cl["m"] <= sl):
                if auto: return sell(c, p, "all", f"stop loss: {held:.0f}s below ${sl:.6g} (in grace window)", "stop_loss")
        else:
            if auto: return sell(c, p, "all", f"stop loss {(px/e-1)*100:+.1f}% (level ${sl:.6g})", "stop_loss")
    else: below.pop(p["ca"], None)
    # --- trailing (auto) ---
    ts = k["trailing_stop"]
    if peak >= e * (1 + ts["activate_at_gain_pct"] / 100):
        if not plan["trail_active"]: c.execute("update risk_plans set trail_active=1 where ca=?", (p["ca"],)); event(c, p["ca"], "trail_on", {"peak": peak}, "armed")
        if px <= peak * (1 - ts["trail_pct"] / 100) and auto:
            return sell(c, p, "all", f"trailing stop: {((px/peak)-1)*100:.0f}% from peak ${peak:.6g}", "trailing")
    # --- dynamic TP (ask) ---
    if time.time() - last["tp"].get(p["ca"], 0) > 60:
        tp, f = dyn_tp(p, plan, px); last["tp"][p["ca"]] = time.time()
        c.execute("update risk_plans set tp=?, notes=? where ca=?", (json.dumps(tp), json.dumps({"tp_factors": f}), p["ca"]))
    tp = json.loads(c.execute("select tp from risk_plans where ca=?", (p["ca"],)).fetchone()[0]); ap = k["take_profit"]["approach_pct"] / 100
    for i, t in enumerate(tp):
        if t["status"] == "open" and mult >= t["multiple"] * (1 - ap):
            spec = t.get("clip") or f"{t['sell_pct']}%"
            m_ = CL.meta(c, p["ca"])
            if m_ and m_["auto_clip"] and mult >= t["multiple"]:   # user opted in: clip without asking
                t["status"] = "auto"; c.execute("update risk_plans set tp=? where ca=?", (json.dumps(tp), p["ca"])); c.commit()
                pc = core.db(); out = CL.clip(pc, p["ca"], spec, source="auto-clip"); pc.close()
                event(c, p["ca"], f"clip{i+1}", {"spec": spec, "out": out[:200]}, "auto"); notify(f"🤖 <b>AUTO-CLIP</b> L{i+1} @ {mult:.2f}x\n\n{out}", pos_kb(p["ca"], auto), p["ca"]); break
            if m_ and m_["auto_clip"]: continue   # auto mode waits for the actual hit, no 'approaching' prompt
            t["status"] = "asked"; c.execute("update risk_plans set tp=? where ca=?", (json.dumps(tp), p["ca"]))
            ask(c, p, f"Clip L{i+1} {'hit' if mult >= t['multiple'] else 'approaching'}", t["sell_pct"], f"{mult:.2f}x now, level {t['multiple']}x (dynamic)", spec, i); break
    # --- time stop (ask) ---
    tsc = k["time_stop"]
    if age > tsc["hours"] * 3600 and mult < 1 + tsc["min_gain_pct"] / 100 and not plan["time_stop_asked"]:
        c.execute("update risk_plans set time_stop_asked=1 where ca=?", (p["ca"],)); ask(c, p, "Time stop", 100, f"{age/3600:.1f}h in, only {(mult-1)*100:+.1f}%")
    c.commit()
def main():
    log("start", "DRY" if DRY else "RUN (paper)"); c = C.pinit(core.db()); start = time.time(); beat = 0
    known = {r[0] for r in c.execute("select ca from risk_plans")}
    while True:
        try:
            ps = c.execute("select * from positions").fetchall(); live = {p["ca"] for p in ps}
            c.execute("delete from risk_plans where ca not in (%s)" % ",".join("?" * len(live)) if live else "delete from risk_plans", tuple(live)); c.commit()
            if time.time() - last.setdefault("tr", 0) > 10:
                last["tr"] = time.time()
                try:
                    pc = core.db()
                    for sym, netp, pnl in CL.process_tranches(pc, log): notify(f"🧊 Tranche filled {core.esc(sym)}: net ${netp:,.2f} (realized {pnl:+,.2f})")
                    pc.close()
                except Exception as e: log("tranche err", C.redact(e))
            for p in ps:
                plan = ensure_plan(c, p, new_notify=p["ca"] not in known and D.datetime.fromisoformat(p["opened_at"]).timestamp() > start - 120)
                known.add(p["ca"])
                try: step(c, p, plan)
                except Exception as e: log("step err", p["symbol"], C.redact(e))
                finally:
                    try: c.commit()   # never leave a write txn open across loop sleeps / network calls
                    except Exception: pass
        except Exception as e: log("loop err", C.redact(e))
        if time.time() - beat > 60: log("heartbeat positions", len(live) if 'live' in dir() else 0); beat = time.time()
        time.sleep(2)
if __name__ == "__main__": main()
