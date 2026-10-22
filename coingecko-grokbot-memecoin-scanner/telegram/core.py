"""Shared core for the Telegram alert + paper-trading bridge.
The bot token is read ONLY from env TELEGRAM_BOT_TOKEN and never printed/logged/written."""
import json, os, re, sqlite3, time, urllib.request, urllib.parse, urllib.error, sys
from datetime import datetime, timezone, timedelta
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
sys.path.insert(0, _ROOT + "/lib"); import addr as A
BASE = _ROOT; TG = f"{BASE}/telegram"
OWNER = f"{TG}/owner.json"; STATE = f"{BASE}/state.json"
DB = os.environ.get("PAPER_DB", f"{BASE}/paper.db")
START_CASH = float(os.environ.get("PAPER_START_CASH", "10000"))   # paper bankroll per book (default $10,000)
FEE = 0.003        # 0.3% swap fee per side
SLIP = 0.007       # 0.7% base slippage per side  (=> ~1% all-in each side)
IMPACT_THRESHOLD = 0.02   # extra impact when size > 2% of pool liquidity
CHAINS = ["solana", "robinhood", "base", "bsc", "eth"]  # Solana first: X buzz often lands there
GT = "https://api.geckoterminal.com/api/v2"
PRO = "https://pro-api.coingecko.com/api/v3/onchain"
from localtz import LOCAL_TZ as MYT, TZ_LABEL  # local zone (MEMESCAN_TZ); name kept for compatibility
def nca(a, chain=None): return A.norm(a, chain)
def now(): return datetime.now(MYT).isoformat(timespec="seconds")

# ---------------- Telegram ----------------
def _tok():
    t = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not t: raise RuntimeError("TELEGRAM_BOT_TOKEN not set in environment")
    return t
def redact(s):
    t = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    s = str(s)
    return s.replace(t, "<redacted>") if t else s
import threading as _th
_SESS = _th.local()
def session():
    """Per-thread keep-alive HTTPS session (avoids a fresh TLS handshake per Telegram call — handshakes were 5-20s)."""
    import requests
    s = getattr(_SESS, "s", None)
    if s is None:
        s = requests.Session(); a = requests.adapters.HTTPAdapter(pool_connections=4, pool_maxsize=8, max_retries=1)
        s.mount("https://", a); _SESS.s = s
    return s
def tg(method, timeout=40, **params):
    data = {k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in params.items() if v is not None}
    try:
        r = session().post(f"https://api.telegram.org/bot{_tok()}/{method}", data=data, timeout=(10, timeout))
        try: return r.json()
        except Exception: return {"ok": False, "description": f"HTTP {r.status_code}"}
    except Exception as e:
        _SESS.s = None
        return {"ok": False, "description": redact(f"{type(e).__name__}: {e}")}
def send(chat_id, text, parse_mode="HTML", reply_to=None, reply_markup=None):
    r = tg("sendMessage", chat_id=chat_id, text=text[:4000], parse_mode=parse_mode,
           disable_web_page_preview="true", reply_to_message_id=reply_to, reply_markup=reply_markup)
    if not r.get("ok") and parse_mode:  # formatting error -> plain retry
        r = tg("sendMessage", chat_id=chat_id, text=re.sub(r"<[^>]+>", "", text)[:4000], reply_to_message_id=reply_to, reply_markup=reply_markup)
    return r
def owner():
    """Authorized chat. TELEGRAM_CHAT_ID (env) wins; otherwise the first private chat that sends /start is saved to owner.json."""
    cid = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if cid.lstrip("-").isdigit(): return {"chat_id": int(cid)}
    try: return json.load(open(OWNER))
    except Exception: return None
def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# ---------------- DB ----------------
SCHEMA = """
create table if not exists account(k text primary key, v real);
create table if not exists alerts(message_id integer, chat_id integer, ca text, network text, pool text, token text,
  tag text, confidence text, human_score real, text text, sent_at text, primary key(chat_id,message_id));
create table if not exists trades(id integer primary key autoincrement, ts text, side text, ca text, network text, pool text,
  symbol text, usd_notional real, qty real, mid_price real, fill_price real, slippage_pct real, fee_usd real,
  liquidity_usd real, realized_pnl real, cash_after real, tag text, confidence text, human_score real, source text);
create table if not exists positions(ca text primary key, network text, pool text, symbol text, qty real, cost_usd real,
  entry_tag text, entry_confidence text, entry_human_score real, opened_at text, updated_at text);
create table if not exists snapshots(ts text, cash real, positions_value real, equity real, unrealized real, realized real);
"""
def db():
    c = sqlite3.connect(DB, timeout=30); c.row_factory = sqlite3.Row
    c.execute("PRAGMA busy_timeout=30000"); c.execute("PRAGMA journal_mode=WAL"); c.executescript(SCHEMA)
    if c.execute("select v from account where k='cash'").fetchone() is None:
        c.execute("insert into account values('cash',?)", (START_CASH,)); c.commit()
    return c
def cash(c): return c.execute("select v from account where k='cash'").fetchone()[0]

# ---------------- Prices (GeckoTerminal public) ----------------
def _get(url):
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "cg-memecoin-scanner/1.0"})
            with urllib.request.urlopen(req, timeout=15) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            if e.code == 429: time.sleep(2 + 3 * i); continue
            raise
    return None
def quote(ca, chain=None):
    """Return {network,ca,symbol,price,liquidity,pool} or None. Tries solana, robinhood, base, bsc, eth.
    Preserves Solana base58 casing (lowercasing breaks CG lookups). Prefers Pro API, falls back to GeckoTerminal public."""
    nets = [chain] if chain else CHAINS
    key = os.environ.get("COINGECKO_PRO_API_KEY", "").strip()
    for net in nets:
        ca_n = nca(ca, net)
        d = None
        if key:
            try:
                req = urllib.request.Request(f"{PRO}/networks/{net}/tokens/{ca_n}?include=top_pools",
                    headers={"accept": "application/json", "x-cg-pro-api-key": key, "User-Agent": "cg-memecoin-scanner/1.0"})
                with urllib.request.urlopen(req, timeout=15) as r: d = json.load(r)
            except Exception: d = None
        if not d or "data" not in d:
            d = _get(f"{GT}/networks/{net}/tokens/{urllib.parse.quote(ca_n)}?include=top_pools")
        if not d or "data" not in d: continue
        a = d["data"]["attributes"]; price = float(a.get("price_usd") or 0)
        if price <= 0: continue
        pools = d.get("included") or []
        # prefer deepest pool
        if pools:
            pools = sorted(pools, key=lambda x: float((x.get("attributes") or {}).get("reserve_in_usd") or 0), reverse=True)
            pool = pools[0]["attributes"]["address"]; liq = float(pools[0]["attributes"].get("reserve_in_usd") or 0)
            # price from THAT pool (token-level price_usd can come from a dust pool -> wrong-pool artifact, e.g. WAP 4.7e-12)
            pa_ = pools[0]["attributes"]; bt = (((pools[0].get("relationships") or {}).get("base_token") or {}).get("data") or {}).get("id", "")
            pp = pa_.get("base_token_price_usd") if (not bt or bt.split("_", 1)[-1].lower() == ca_n.lower()) else pa_.get("quote_token_price_usd")
            try:
                if pp and float(pp) > 0: price = float(pp)
            except Exception: pass
        else:
            pool = None; liq = float(a.get("total_reserve_in_usd") or 0)
        try:
            import ticks; price, _si = ticks.sane(ca_n, pool, price, "rest")   # tape/median sanitation (same pool)
        except Exception: _si = {}
        return {"network": net, "ca": ca_n, "symbol": a.get("symbol") or "?", "name": a.get("name"),
                "price": price, "liquidity": liq, "pool": pool, "sanity": _si}
    return None
def cp_exit(value_mid, liq):
    """Constant-product exit: selling tokens worth value_mid (at mid) into a pool whose quote side ~= liq/2.
    out = y*V/(y+V), minus fee. liq<=0 -> 0 (full rug)."""
    y = max(0.0, (liq or 0) / 2.0)
    if y <= 0 or value_mid <= 0: return 0.0
    return y * value_mid / (y + value_mid) * (1 - FEE)
def slippage(usd, liq):
    s = SLIP
    if liq and liq > 0: s += min(0.9, usd / (liq / 2))   # constant-product buy impact: avg price = mid*(y+U)/y, y = liq/2
    elif not liq: s += 0.05
    return s

# ---------------- Scanner metadata ----------------
def state():
    try: return json.load(open(STATE))
    except Exception: return {}
def _ca_eq(a, b): return nca(a) == nca(b)
def scanner_meta(ca, c=None):
    ca_n = nca(ca); out = {}
    for k, v in (state().get("assessed") or {}).items():
        if _ca_eq(v.get("ca") or "", ca_n):
            hs = v.get("human_score")
            if hs is None:
                m = re.search(r"human[^0-9]{0,20}(\d{1,3})", json.dumps(v), re.I); hs = int(m.group(1)) if m else None
            out = {"tag": v.get("verdict"), "confidence": v.get("confidence"), "human_score": hs,
                   "network": k.partition("_")[0], "pool": k.partition("_")[2], "token": v.get("token")}
    if c is not None:
        # case-insensitive match for EVM; exact for Solana (alerts store as sent)
        for r in c.execute("select * from alerts order by sent_at desc limit 200"):
            if _ca_eq(r["ca"], ca_n):
                out = {"tag": r["tag"], "confidence": r["confidence"], "human_score": r["human_score"],
                       "network": r["network"], "pool": r["pool"], "token": r["token"]}; break
    return out
def _ticker_hits(t, c):
    """All distinct (ca, network, source, at, verdict, liq_hint) for a ticker. Prefer alerted > non-discard > newest."""
    t = t.lstrip("$").lower(); hits = {};  # key=(nca,net)
    if c is not None:
        for r in c.execute("select ca,network,token,tag,sent_at,pool from alerts where lower(token)=? order by sent_at desc", (t,)):
            key = (nca(r["ca"], r["network"]), r["network"] or "")
            if key[0] and key not in hits:
                hits[key] = {"ca": nca(r["ca"], r["network"]), "network": r["network"], "source": "alert",
                             "at": r["sent_at"], "verdict": r["tag"], "pool": r["pool"], "symbol": r["token"]}
    for k, v in (state().get("assessed") or {}).items():
        sym = (v.get("token") or "").split("(")[0].strip().lower()
        if sym != t and (v.get("token") or "").lower() != t: continue
        ca = v.get("ca"); net = k.partition("_")[0]
        if not ca: continue
        key = (nca(ca, net), net)
        if key not in hits:
            hits[key] = {"ca": nca(ca, net), "network": net, "source": "assessed",
                         "at": v.get("at") or "", "verdict": v.get("verdict"), "pool": k.partition("_")[2],
                         "symbol": (v.get("token") or t).split("(")[0].strip(),
                         "metrics": v.get("metrics") or {}, "xbuzz": str(v.get("source") or "").startswith("x")}
    # enrich with live liq/age when multiple
    out = list(hits.values())
    rank = {"Organic Hype": 3, "Watch": 2, "discard": 0}
    def score(h):
        alerted = 100 if h["source"] == "alert" else 0
        v = (h.get("verdict") or "")
        vr = 50 if "organic" in v.lower() else 30 if "watch" in v.lower() else 0 if "discard" in v.lower() else 10
        return (alerted, 40 if h.get("xbuzz") else 0, vr, h.get("at") or "")
    out.sort(key=score, reverse=True)
    return out
_NS = {}
def live_namesakes(ticker, min_liq=5000):
    """CoinGecko /search/pools for a ticker -> base tokens with that exact symbol on supported chains (liq >= min_liq)."""
    t = ticker.lstrip("$").lower(); hit = _NS.get(t)
    if hit and time.time() - hit[0] < 300: return hit[1]
    out = {}; key = os.environ.get("COINGECKO_PRO_API_KEY", "").strip()
    try:
        url = f"{PRO}/search/pools?query={urllib.parse.quote(t)}&include=base_token"
        req = urllib.request.Request(url, headers={"accept": "application/json", "x-cg-pro-api-key": key})
        with urllib.request.urlopen(req, timeout=15) as r: d = json.load(r)
        toks = {x["id"]: x["attributes"] for x in d.get("included") or [] if x.get("type") == "token"}
        for p in d.get("data") or []:
            a = p["attributes"]; bt = p["relationships"]["base_token"]["data"]["id"]; net, _, ca = bt.partition("_")
            if net not in CHAINS: continue
            sym = (toks.get(bt) or {}).get("symbol") or (a.get("name") or "").split(" / ")[0]
            liq = float(a.get("reserve_in_usd") or 0)
            if sym.lower() != t or liq < min_liq: continue
            k = nca(ca, net)
            if k not in out or liq > (out[k].get("liq") or 0):
                age = None
                try: age = round((time.time() - datetime.fromisoformat(a["pool_created_at"].replace("Z", "+00:00")).timestamp()) / 3600, 1)
                except Exception: pass
                out[k] = {"ca": k, "network": net, "source": "cg-search", "at": "", "verdict": "unassessed",
                          "pool": a.get("address"), "symbol": sym, "liq": liq, "metrics": {"age_min": age * 60 if age is not None else None, "liq": liq}}
    except Exception: pass
    res = sorted(out.values(), key=lambda x: -(x.get("liq") or 0))[:5]; _NS[t] = (time.time(), res); return res
def resolve(sym_or_ca, c, prefer_ca=None, chain=None):
    """CA passthrough (EVM or Solana). Ticker -> unique CA, or (None, None) if unknown.
    When multiple chains/CAs share a ticker, returns (None, {"ambiguous": [hits...]}) so the caller can show pick buttons.
    prefer_ca (reply-to alert / recent alert) wins when it matches the ticker family."""
    s = (sym_or_ca or "").strip()
    if A.is_evm(s): return nca(s, "base"), None
    if A.is_sol(s): return nca(s, "solana"), None
    t = s.lstrip("$")
    hits = _ticker_hits(t, c)
    if prefer_ca:
        pref = nca(prefer_ca)
        for h in hits:
            if h["ca"] == pref: return h["ca"], h["network"]
        # prefer_ca itself may be the intended token even if ticker lookup missed it
        if pref: return pref, chain
    if not hits: return None, None
    if chain:
        ch = [h for h in hits if h["network"] == chain]
        if len(ch) == 1: return ch[0]["ca"], ch[0]["network"]
        if ch: hits = ch
    # unique CA across chains? If it isn't an alerted token, check CoinGecko for live namesakes first.
    cas = {h["ca"] for h in hits}
    if len(cas) == 1 and hits[0]["source"] != "alert":
        hits = hits + [x for x in live_namesakes(t) if x["ca"] not in cas]
        cas = {h["ca"] for h in hits}
    if len(cas) == 1: return hits[0]["ca"], hits[0]["network"]
    # multiple distinct CAs / chains -> ambiguous (never silently pick a namesake)
    return None, {"ambiguous": hits, "ticker": t}

# ---------------- Trading ----------------
def chain_of(c, ca):
    p = c.execute("select network from positions where ca=?", (nca(ca),)).fetchone()
    if p: return p["network"]
    m = scanner_meta(ca, c)
    return m.get("network") or ("solana" if A.is_sol(ca) else None)
def enrich_hits(hits):
    """Add live liq + age_h for picker buttons (best-effort, capped)."""
    out = []
    for h in hits[:6]:
        q = quote(h["ca"], h.get("network"))
        age = None
        m = h.get("metrics") or {}
        if m.get("age_min") is not None: age = round(m["age_min"] / 60, 1)
        out.append({**h, "liq": (q or {}).get("liquidity") or m.get("liq"), "price": (q or {}).get("price"),
                    "symbol": (q or {}).get("symbol") or h.get("symbol"), "age_h": age,
                    "pool": (q or {}).get("pool") or h.get("pool")})
    return out
def pick_kb(hits, usd, ticker):
    """Telegram inline keyboard: one button per (chain, CA) with liq/age."""
    rows = []
    for h in hits:
        ca = h["ca"]; short = ca[:6] + "…" + ca[-4:] if len(ca) > 12 else ca
        liq = h.get("liq"); age = h.get("age_h")
        liq_s = f"${liq:,.0f}" if liq else "?"; age_s = f"{age}h" if age is not None else "?"
        ver = (h.get("verdict") or "?")[:12]
        rows.append([{"text": f"{h.get('symbol') or ticker} · {h['network']} · liq {liq_s} · {ver}",
                      "callback_data": f"pick:{usd:g}:{h['network']}:{ca}"}])
        rows.append([{"text": f"   {short}", "callback_data": f"pick:{usd:g}:{h['network']}:{ca}"}])
    rows.append([{"text": "❌ Cancel", "callback_data": "n:0"}])
    return {"inline_keyboard": rows}
def buy(c, target, usd, chain=None, source="cmd", prefer_ca=None, allow_ambiguous=False):
    """Paper buy. If ticker maps to multiple CAs/chains, returns AMBIGUOUS:… JSON for the daemon to show pick buttons
    (unless allow_ambiguous=False and a single prefer_ca / chain disambiguates). Never silently picks a namesake."""
    got = resolve(target, c, prefer_ca=prefer_ca, chain=chain)
    ca, net = got
    if isinstance(net, dict) and net.get("ambiguous"):
        if not allow_ambiguous:
            hits = enrich_hits(net["ambiguous"])
            return "AMBIGUOUS:" + json.dumps({"ticker": net["ticker"], "usd": usd, "hits": hits, "source": source})
        return f"❌ Ambiguous ticker <b>{esc(net['ticker'])}</b> — pick a CA."
    if not ca: return f"❌ Can't resolve <b>{esc(target)}</b>. Use a contract address (0x… / Solana) or a ticker the scanner has assessed."
    if usd <= 0: return "❌ Amount must be > 0."
    bal = cash(c)
    if usd > bal: return f"❌ Insufficient paper balance: ${bal:,.2f}."
    q = quote(ca, chain or (net if isinstance(net, str) else None))
    if not q: return f"❌ No price found for <code>{esc(ca)}</code> on {', '.join([chain] if chain else CHAINS)}."
    ca = q["ca"]  # normalised
    s = slippage(usd, q["liquidity"]); fee = usd * FEE; fill = q["price"] * (1 + s); qty = (usd - fee) / fill
    m = scanner_meta(ca, c); t = now(); newcash = bal - usd
    for attempt in range(5):
        try:
            c.execute("update account set v=? where k='cash'", (newcash,))
            p = c.execute("select * from positions where ca=?", (ca,)).fetchone()
            if p: c.execute("update positions set qty=qty+?, cost_usd=cost_usd+?, updated_at=? where ca=?", (qty, usd, t, ca))
            else: c.execute("insert into positions values(?,?,?,?,?,?,?,?,?,?,?)", (ca, q["network"], q["pool"], q["symbol"], qty, usd,
                            m.get("tag"), m.get("confidence"), m.get("human_score"), t, t))
            c.execute("insert into trades(ts,side,ca,network,pool,symbol,usd_notional,qty,mid_price,fill_price,slippage_pct,fee_usd,liquidity_usd,realized_pnl,cash_after,tag,confidence,human_score,source) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (t, "buy", ca, q["network"], q["pool"], q["symbol"], usd, qty, q["price"], fill, s * 100, fee, q["liquidity"], None, newcash,
                       m.get("tag"), m.get("confidence"), m.get("human_score"), source))
            c.commit(); break
        except sqlite3.OperationalError as e:
            if "locked" not in str(e) or attempt == 4: raise
            time.sleep(0.4 * (attempt + 1)); c.rollback()
    snapshot(c)
    return (f"🟢 <b>PAPER BUY</b> {esc(q['symbol'])} ({q['network']})\n<code>{ca}</code>\n"
            f"Spent ${usd:,.2f} → {qty:,.4f} tokens\nMid ${q['price']:.8g} · fill ${fill:.8g}\n"
            f"Slippage {s*100:.2f}% · fee ${fee:,.2f} · pool liq ${q['liquidity']:,.0f}\n"
            f"Entry tag: {esc(m.get('tag') or 'n/a')} / {esc(m.get('confidence') or '-')} · human {m.get('human_score') if m.get('human_score') is not None else '-'}\n"
            f"Cash left ${newcash:,.2f}")
def sell(c, target, amt, source="cmd", prefer_ca=None, rug_reason=None, liq_override=None):
    ca, net = resolve(target, c, prefer_ca=prefer_ca)
    if isinstance(net, dict) and net.get("ambiguous"):
        # sell: prefer an open position that matches one of the hits
        for h in net["ambiguous"]:
            p = c.execute("select * from positions where ca=?", (h["ca"],)).fetchone()
            if p: ca = h["ca"]; break
        else:
            return f"❌ Ambiguous ticker <b>{esc(net['ticker'])}</b> and no matching open position. Use the CA."
    p = c.execute("select * from positions where ca=?", (ca,)).fetchone() if ca else None
    if not p:
        # try case-insensitive for legacy lowercased rows
        if ca:
            for r in c.execute("select * from positions"):
                if _ca_eq(r["ca"], ca): p = r; ca = r["ca"]; break
    if not p: return f"❌ No open position for <b>{esc(target)}</b>."
    q = quote(ca, p["network"])
    if not q: return "❌ Couldn't fetch a price right now; try again."
    a = amt.strip().lower().lstrip("$")
    if a in ("all", "100%", "max"): frac = 1.0
    elif a.endswith("%"): frac = float(a[:-1]) / 100
    else: frac = float(a) / (p["qty"] * q["price"])   # usd amount at mid
    if not 0 < frac: return "❌ Amount must be > 0."
    frac = min(frac, 1.0); qty = p["qty"] * frac
    liq = q["liquidity"] if liq_override is None else liq_override
    if rug_reason:   # realistic fill into what's left of the pool (constant product), can be ~0
        proceeds = cp_exit(qty * q["price"], liq); fee = proceeds * FEE / (1 - FEE) if proceeds else 0.0
        fill = proceeds / qty if qty else 0.0; s = 1 - (fill / q["price"]) if q["price"] else 1.0
        source = f"{source}|{rug_reason}"
    else:
        if liq:   # realistic: constant-product impact + DEX fee + per-chain gas/tip
            import clips as _CL
            f_ = _CL.fill(qty * q["price"], liq, p["network"]); proceeds = f_["net"]; fee = f_["dex_fee"] + f_["gas"]
            fill = proceeds / qty if qty else 0.0; s = f_["impact_pct"]
        else:
            s = slippage(qty * q["price"], liq); fill = q["price"] * (1 - s)
            gross = qty * fill; fee = gross * FEE; proceeds = gross - fee
    basis = p["cost_usd"] * frac; pnl = proceeds - basis
    t = now(); newcash = cash(c) + proceeds
    c.execute("update account set v=? where k='cash'", (newcash,))
    if frac >= 0.999999: c.execute("delete from positions where ca=?", (ca,))
    else: c.execute("update positions set qty=qty-?, cost_usd=cost_usd-?, updated_at=? where ca=?", (qty, basis, t, ca))
    c.execute("insert into trades(ts,side,ca,network,pool,symbol,usd_notional,qty,mid_price,fill_price,slippage_pct,fee_usd,liquidity_usd,realized_pnl,cash_after,tag,confidence,human_score,source) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (t, "sell", ca, p["network"], p["pool"], p["symbol"], proceeds, qty, q["price"], fill, s * 100, fee, q["liquidity"], pnl, newcash,
               p["entry_tag"], p["entry_confidence"], p["entry_human_score"], source))
    c.commit(); snapshot(c)
    return (f"🔴 <b>PAPER SELL</b> {esc(p['symbol'])} {frac*100:.1f}%\n<code>{ca}</code>\n"
            f"{qty:,.4f} tokens → ${proceeds:,.2f}\nMid ${q['price']:.8g} · fill ${fill:.8g} · slip {s*100:.2f}% · fee ${fee:,.2f}\n"
            f"Realized PnL: <b>{'+' if pnl>=0 else ''}${pnl:,.2f}</b> ({pnl/basis*100:+.1f}%)\nCash ${newcash:,.2f}")
def cached_quote(ca, net, max_age=60):
    """Fresh stream price (WS G1) from market.db, else REST quote."""
    try:
        m = sqlite3.connect(f"file:{BASE}/market.db?mode=ro", uri=True, timeout=2)
        r = m.execute("select p, r, pa, t from prices where ta=? order by t desc limit 1", (ca,)).fetchone(); m.close()
        if r and r[0] and time.time() - r[3] <= max_age:
            import ticks; px, si = ticks.sane(ca, r[2], r[0], "G1")
            if px: return {"network": net, "ca": ca, "price": px, "liquidity": r[1], "pool": r[2], "cached": True, "sanity": si}
    except Exception: pass
    return quote(ca, net)
def mtm(c):
    rows = []
    for p in c.execute("select * from positions order by opened_at").fetchall():
        q = cached_quote(p["ca"], p["network"]); px = q["price"] if q else None
        val = p["qty"] * px if px else None
        liq = (q or {}).get("liquidity")
        if val is not None and liq is not None and (liq < 1000 or val > 0.02 * liq):
            val = cp_exit(val, liq)   # thin pool: value = what a sale would actually return
        rows.append({**dict(p), "price": px, "value": val, "unrealized": (val - p["cost_usd"]) if val is not None else None})
    return rows
def snapshot(c, rows=None):
    rows = mtm(c) if rows is None else rows
    pv = sum((r["value"] if r["value"] is not None else r["cost_usd"]) for r in rows)
    un = sum((r["unrealized"] or 0) for r in rows); re_ = c.execute("select coalesce(sum(realized_pnl),0) from trades").fetchone()[0]
    cs = cash(c); c.execute("insert into snapshots values(?,?,?,?,?,?)", (now(), cs, pv, cs + pv, un, re_)); c.commit()
    return cs, pv, un, re_

# ---------------- Commands ----------------
HELP = ("<b>Memecoin Scanner · paper-trading bot</b>\n"
        "/buy &lt;CA|ticker&gt; &lt;usd&gt; [chain] — paper buy (chains: solana, robinhood, base, bsc, eth; ambiguous tickers ask you to pick CA)\n"
        "/sell &lt;CA|ticker&gt; &lt;pct|all|usd&gt; — e.g. /sell 0x… 50% · /sell 0x… all · /sell 0x… 25\n"
        "/positions — open positions, marked to market\n/portfolio — chart image (equity, PnL, TP/SL distance)\n/report — report card (realized/unrealized, open + closed trades, by tag)\n/pnl — realized + unrealized PnL\n"
        "/ledger — last 15 trades\n/balance — cash + equity\n/help — this\n"
        "Reply to an alert with <code>buy 100</code> or <code>sell 50%</code> to trade that alert's token.\n"
        f"Start balance ${START_CASH:,.0f} USDC · ~{(FEE+SLIP)*100:.0f}% slippage+fee each side, more if size &gt;2% of pool liquidity.")
def handle(c, text, reply_ca=None):
    """Parse one message; returns HTML reply text (or None to ignore)."""
    t = (text or "").strip()
    if not t: return None
    parts = t.split(); cmd = parts[0].lower().split("@")[0].lstrip("/"); args = parts[1:]
    try:
        if cmd in ("start", "help"): return HELP
        if cmd == "buy":
            if reply_ca and len(args) == 1: return buy(c, reply_ca, float(args[0].lstrip("$")), source="reply", prefer_ca=reply_ca)
            if len(args) < 2: return "Usage: /buy &lt;CA|ticker&gt; &lt;usd&gt; [chain]  (or reply to an alert: buy 100)"
            ch = args[2].lower() if len(args) > 2 else None
            if ch and ch not in CHAINS: return f"❌ Unknown chain {esc(ch)}. Use: {', '.join(CHAINS)}"
            return buy(c, args[0], float(args[1].lstrip("$")), chain=ch, source="cmd", prefer_ca=reply_ca)
        if cmd == "sell":
            if reply_ca and len(args) == 1: return sell(c, reply_ca, args[0], source="reply")
            if len(args) < 2: return "Usage: /sell &lt;CA|ticker&gt; &lt;pct|all|usd&gt;  (or reply to an alert: sell 50%)"
            return sell(c, args[0], args[1])
        if cmd == "positions":
            rows = mtm(c); snapshot(c, rows)
            if not rows: return "No open positions."
            return "<b>Open positions</b>\n" + "\n".join(
                f"• {esc(r['symbol'])} ({r['network']}) <code>{r['ca']}</code>\n   cost ${r['cost_usd']:,.2f} · value {('$%s' % format(r['value'], ',.2f')) if r['value'] is not None else 'n/a'} · "
                f"uPnL {('%+.2f (%+.1f%%)' % (r['unrealized'], r['unrealized']/r['cost_usd']*100)) if r['unrealized'] is not None else 'n/a'} · tag {esc(r['entry_tag'] or '-')}" for r in rows)
        if cmd in ("pnl", "balance"):
            cs, pv, un, re_ = snapshot(c); eq = cs + pv
            n = c.execute("select count(*), sum(realized_pnl>0) from trades where side='sell'").fetchone()
            s = f"<b>{'PnL' if cmd=='pnl' else 'Balance'}</b>\nCash ${cs:,.2f}\nPositions ${pv:,.2f}\nEquity <b>${eq:,.2f}</b> ({(eq/START_CASH-1)*100:+.2f}% vs ${START_CASH:,.0f})"
            if cmd == "pnl": s += f"\nRealized ${re_:+,.2f} · Unrealized ${un:+,.2f}\nClosing sells: {n[0]} · winners {n[1] or 0}"
            return s
        if cmd == "ledger":
            rs = c.execute("select * from trades order by id desc limit 15").fetchall()
            if not rs: return "Ledger empty."
            return "<b>Last trades</b>\n" + "\n".join(f"{r['ts'][5:16].replace('T',' ')} {r['side'].upper()} {esc(r['symbol'])} ${r['usd_notional']:,.2f} @ {r['fill_price']:.6g}"
                   + (f" · PnL {r['realized_pnl']:+,.2f}" if r['realized_pnl'] is not None else "") for r in rs)
        if reply_ca is None and cmd in ("buy", "sell"): return None
        return None if not t.startswith("/") else "Unknown command. /help"
    except ValueError: return "❌ Couldn't parse the amount. /help"
    except Exception as e: return f"⚠️ Error: {esc(redact(e))[:300]}"

# ---------------- v2: buttons, mute, message->CA map, pending confirmations ----------------
MUTED = os.environ.get("TG_MUTED_FILE", f"{TG}/muted.json")
SCHEMA2 = """
create table if not exists msg_ca(chat_id integer, message_id integer, ca text, kind text, primary key(chat_id,message_id));
create table if not exists pending(id integer primary key autoincrement, chat_id integer, payload text, created real, status text);
create table if not exists prompts(chat_id integer, message_id integer, ca text, kind text, created real, primary key(chat_id,message_id));
"""
_db1 = db
def db():
    c = _db1(); c.executescript(SCHEMA2); return c
def muted():
    try: return json.load(open(MUTED))
    except Exception: return {}
def is_muted(ca): m=muted(); return nca(ca) in m or (ca or "").lower() in m
def set_mute(ca, on=True, symbol=None):
    m = muted(); ca = nca(ca)
    if on: m[ca] = {"symbol": symbol, "muted_at": now()}
    else: m.pop(ca, None)
    tmp = MUTED + ".tmp"; json.dump(m, open(tmp, "w"), indent=1); os.replace(tmp, MUTED); return m
def remember(c, chat_id, message_id, ca, kind):
    c.execute("insert or replace into msg_ca values(?,?,?,?)", (chat_id, message_id, nca(ca) if ca else None, kind)); c.commit()
def msg_ctx(c, chat_id, message_id):
    """-> (ca, kind) for a bot message (alert / fill / position / prompt), else (None,None)."""
    r = c.execute("select ca from alerts where chat_id=? and message_id=?", (chat_id, message_id)).fetchone()
    if r: return nca(r["ca"]), "alert"
    r = c.execute("select ca,kind from msg_ca where chat_id=? and message_id=?", (chat_id, message_id)).fetchone()
    return (nca(r["ca"]) if r["ca"] else None, r["kind"]) if r else (None, None)
def symbol_of(c, ca):
    ca_n = nca(ca)
    for q in ("select symbol s from positions where ca=?", "select symbol s from trades where ca=? order by id desc limit 1"):
        r = c.execute(q, (ca_n,)).fetchone()
        if r and r["s"]: return r["s"]
    for r in c.execute("select token s, ca from alerts order by sent_at desc limit 300"):
        if r["s"] and _ca_eq(r["ca"], ca_n): return r["s"]
    return (scanner_meta(ca_n) or {}).get("token") or (ca_n[:8] if ca_n else "?")
def clip_row(ca):
    return [{"text": "✂️10%", "callback_data": f"cl:10:{ca}"}, {"text": "✂️25%", "callback_data": f"cl:25:{ca}"},
            {"text": "✂️50%", "callback_data": f"cl:50:{ca}"}, {"text": "💰Initial", "callback_data": f"cl:init:{ca}"}]
def house_badge(c, ca):
    try:
        import clips as _CL; m = _CL.house(c, ca)
        if not m: return ""
        return (" 🏠 HOUSE MONEY" if m["initial_out"] else "") + (f" · ✂️{m['clips']} clips ${m['clip_realized']:,.0f}" if m["clips"] else "")
    except Exception: return ""
def alert_kb(ca):
    mt = "🔔 Unmute" if is_muted(ca) else "🔕 Mute token"
    return {"inline_keyboard": [
        [{"text": "Buy $50", "callback_data": f"b:50:{ca}"}, {"text": "Buy $100", "callback_data": f"b:100:{ca}"},
         {"text": "Buy $250", "callback_data": f"b:250:{ca}"}, {"text": "Custom $", "callback_data": f"c:{ca}"}],
        clip_row(ca), [{"text": "Sell All", "callback_data": f"s:all:{ca}"}, {"text": "🤖 Auto-clip", "callback_data": f"ac:{ca}"}],
        [{"text": "📊 Positions", "callback_data": "p"}, {"text": mt, "callback_data": f"m:{ca}"}]]}
def positions_kb(rows):
    kb = []
    for r in rows[:12]:
        kb.append([{"text": f"{r['symbol'][:8]} ✂️25%", "callback_data": f"cl:25:{r['ca']}"}, {"text": "💰Initial", "callback_data": f"cl:init:{r['ca']}"},
                   {"text": "Sell all", "callback_data": f"s:all:{r['ca']}"}])
    kb.append([{"text": "🔄 Refresh", "callback_data": "p"}])
    return {"inline_keyboard": kb}
def position_line(c, ca):
    p = c.execute("select * from positions where ca=?", (ca,)).fetchone()
    if not p: return f"📊 <b>Your position:</b> none · cash ${cash(c):,.2f}"
    q = quote(ca, p["network"]); px = q["price"] if q else None
    if px is None: return f"📊 <b>Your position:</b> {p['qty']:,.4f} {esc(p['symbol'])} · cost ${p['cost_usd']:,.2f} (price n/a)"
    v = p["qty"] * px; u = v - p["cost_usd"]
    return (f"📊 <b>Your position:</b> {p['qty']:,.4f} {esc(p['symbol'])} · cost ${p['cost_usd']:,.2f} · "
            f"value ${v:,.2f} · uPnL {u:+,.2f} ({u/p['cost_usd']*100:+.1f}%)")
def positions_view(c):
    rows = mtm(c); snapshot(c, rows)
    if not rows: return "No open positions.", rows
    return "<b>Open positions</b>\n" + "\n".join(
        f"• {esc(r['symbol'])} ({r['network']}) <code>{r['ca']}</code>\n   cost ${r['cost_usd']:,.2f} · value {('$%s' % format(r['value'], ',.2f')) if r['value'] is not None else 'n/a'} · "
        f"uPnL {('%+.2f (%+.1f%%)' % (r['unrealized'], r['unrealized']/r['cost_usd']*100)) if r['unrealized'] is not None and r['cost_usd'] else 'n/a'} · tag {esc(r['entry_tag'] or '-')}{house_badge(c, r['ca'])}" for r in rows), rows
def add_pending(c, chat_id, payload):
    cur = c.execute("insert into pending(chat_id,payload,created,status) values(?,?,?,'open')", (chat_id, json.dumps(payload), time.time())); c.commit()
    return cur.lastrowid
def take_pending(c, pid, chat_id, ttl=900):
    r = c.execute("select * from pending where id=? and chat_id=?", (pid, chat_id)).fetchone()
    if not r: return None, "not found"
    if r["status"] != "open": return None, f"already {r['status']}"
    if time.time() - r["created"] > ttl: c.execute("update pending set status='expired' where id=?", (pid,)); c.commit(); return None, "expired"
    return json.loads(r["payload"]), None
def close_pending(c, pid, status): c.execute("update pending set status=? where id=?", (status, pid)); c.commit()

# ---------- idempotency for forwarded (AI-routine) trades ----------
def recent_trade(ca, side, minutes=10, c=None):
    """Most recent same-CA same-side paper trade within `minutes`, as a dict, else None.
    The free-form routine MUST call this before executing any trade it was forwarded (Telegram can deliver a message to
    both the local parser and the routine, or the user may repeat themselves while the routine is slow).
    CLI: python3 telegram/core.py recent-trade <ca> <buy|sell> [minutes]  -> prints JSON or null (exit 0)."""
    own = c is None; c = c or db()
    try:
        cut = (datetime.now(MYT) - timedelta(minutes=minutes)).isoformat(timespec="seconds")
        rows = c.execute("select id, ts, side, ca, symbol, usd_notional, source from trades where side=? and ts>=? order by id desc limit 50",
                        (side, cut)).fetchall()
        r = next((x for x in rows if _ca_eq(x["ca"], ca)), None)
        return dict(r) if r else None
    finally:
        if own: c.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 4 and sys.argv[1] == "recent-trade":
        print(json.dumps(recent_trade(sys.argv[2], sys.argv[3], float(sys.argv[4]) if len(sys.argv) > 4 else 10)))
    elif len(sys.argv) >= 3 and sys.argv[1] == "cmd":     # run a paper command, e.g. core.py cmd "/buy <CA> 50 base" (PAPER only)
        _c = db(); print(re.sub(r"<[^>]+>", "", handle(_c, sys.argv[2]) or "")); _c.close()
    elif len(sys.argv) >= 3 and sys.argv[1] == "say":     # send a message to the owner chat: core.py say "<html text>" [reply_to_message_id]
        _o = owner()
        if not _o: sys.exit("no Telegram owner registered (send /start to the bot or set TELEGRAM_CHAT_ID)")
        r = send(_o["chat_id"], sys.argv[2], reply_to=int(sys.argv[3]) if len(sys.argv) > 3 else None); print("sent" if r.get("ok") else "failed: " + redact(r.get("description", "")))
