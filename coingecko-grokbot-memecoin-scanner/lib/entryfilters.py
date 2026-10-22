"""Entry filters shared by the AI book (autotrader) and human Scout criteria.
 impersonation(name, symbol) -> matched term | None   (auto/impersonation.json, fuzzy)
 ca_buzz(ca)                 -> {"authors": n_non_shill_authors_posting_exact_CA, "posts": n, "src": [...]}
 fragile(age_min, live_liq)  -> reason | None        (pool < 10 min old or live liquidity < $10k)
 profile(net, pool)          -> winner-profile dict (sustained non-dust volume, steady multi-minute climb) with score 0..1
Data for exact-CA buzz: xfirst runs/queue (posts that contain the CA) + routine verdicts in state.json (field x_ca_authors)."""
import json, re, os, glob, time, math, sqlite3, difflib, unicodedata
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
BASE = _ROOT
SHILL = [r"\b\d+(\.\d+)?x\b.*(call|secured|profit)", r"profit secured", r"called (it )?early", r"\bvip\b", r"\bgem\b.*\b(100|1000)x\b", r"don'?t miss", r"next 100x",
         r"join (my|our) (tg|telegram|channel)", r"\bpump(ing)? soon\b", r"airdrop", r"guaranteed"]
def _n(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9& ]", "", s).strip()
def impersonation(name, symbol):
    try: L = json.load(open(f"{BASE}/auto/impersonation.json"))
    except Exception: return None
    exact = set(L.get("exact_only") or [])
    words = set(re.split(r"\s+", _n(name)) + re.split(r"\s+", _n(symbol))) - {""}
    blob = (_n(name) + " " + _n(symbol)).replace(" ", "")
    for t in L.get("terms") or []:
        tn = _n(t).replace(" ", "")
        if not tn: continue
        if t in exact:
            if tn in words: return t
            continue
        if tn in words or (len(tn) >= 5 and tn in blob): return t
        for w in words:   # fuzzy: NASDANQ ~ NASDAQ, TESLAA ~ TESLA, M1CROSOFT ~ MICROSOFT
            if len(w) >= 4 and len(tn) >= 4 and difflib.SequenceMatcher(None, w, tn).ratio() >= 0.83: return t
    return None
def _shill(text): return any(re.search(p, text or "", re.I) for p in SHILL)
_BZ = {"t": 0, "m": {}}
def _buzz_index():
    if time.time() - _BZ["t"] < 60: return _BZ["m"]
    m = {}; cut = time.time() - 12 * 3600
    files = sorted(glob.glob(f"{BASE}/xfirst/runs/*/candidates.json"), key=os.path.getmtime)[-40:]
    for fp in files:
        if os.path.getmtime(fp) < cut: continue
        try: d = json.load(open(fp))
        except Exception: continue
        for c in d.get("candidates") or []:
            ca = c.get("ca") or ""; k = ca if not ca.startswith("0x") else ca.lower(); e = m.setdefault(k, {"authors": set(), "posts": 0, "src": set()})
            for p in c.get("x_posts") or []:
                if ca.lower() in (p.get("text") or "").lower():
                    e["posts"] += 1
                    if not _shill(p.get("text")): e["authors"].add(p.get("user")); e["src"].add("x-first")
    try:
        st = json.load(open(f"{BASE}/state.json"))
        for v in (st.get("assessed") or {}).values():
            ca = v.get("ca") or ""; n = v.get("x_ca_authors")
            if ca and isinstance(n, (int, float)) and n > 0:
                k = ca if not ca.startswith("0x") else ca.lower(); e = m.setdefault(k, {"authors": set(), "posts": 0, "src": set()})
                e["authors"] |= {f"routine#{i}" for i in range(int(n))}; e["src"].add("routine")
    except Exception: pass
    _BZ.update(t=time.time(), m=m); return m
def ca_buzz(ca):
    e = _buzz_index().get(ca if not ca.startswith("0x") else ca.lower())
    return {"authors": len(e["authors"]), "posts": e["posts"], "src": sorted(e["src"])} if e else {"authors": 0, "posts": 0, "src": []}
def fragile(age_min, live_liq, min_age=10, min_liq=10000):
    if age_min is not None and age_min < min_age: return f"pool age {age_min:.0f}m < {min_age}m"
    if (live_liq or 0) < min_liq: return f"live liq ${live_liq or 0:,.0f} < ${min_liq:,}"
    return None
def profile(net, pool, window_min=15, dust=1.0):
    """Winner profile (MET/TERMINAL/ODDSINU): many non-dust trades, steady climb across several minutes, not one spike."""
    m = sqlite3.connect(f"file:{BASE}/market.db?mode=ro", uri=True, timeout=3); now = time.time()
    try:
        tr = m.execute("select usd from trades where pool=? and t>? and usd>=?", (pool, now - 600, dust)).fetchall()
        bars = m.execute("select t, o, c from ohlcv where pool=? and iv='1m' and t>? order by t", (pool, now - window_min * 60)).fetchall()
        if len(bars) < 4:
            b15 = m.execute("select t, o, c from ohlcv where pool=? and iv='15s' and t>? order by t", (pool, now - window_min * 60)).fetchall()
            bars = [(b15[i][0], b15[i][1], b15[min(i + 3, len(b15) - 1)][2]) for i in range(0, len(b15), 4)] if b15 else bars
        if len(bars) < 4:   # aggregate 1s candles (stream G3) into 1m bars
            agg = {}
            for t, o, c in m.execute("select t, o, c from ohlcv where pool=? and iv='1s' and t>? order by t", (pool, now - window_min * 60)):
                b = agg.setdefault(int(t // 60), [t, o, c]); b[2] = c
            if len(agg) > len(bars): bars = [tuple(v) for _, v in sorted(agg.items())]
        if len(bars) < 4:   # last resort: non-dust trade prices bucketed per minute
            agg = {}
            for t, pu in m.execute("select t, pu from trades where pool=? and t>? and usd>=? and pu>0 order by t", (pool, now - window_min * 60, dust)):
                b = agg.setdefault(int(t // 60), [t, pu, pu]); b[2] = pu
            if len(agg) > len(bars): bars = [tuple(v) for _, v in sorted(agg.items())]
    finally: m.close()
    if len(bars) < 4 or not tr:   # candidate not on the stream yet: REST (CoinGecko onchain) minute OHLCV + recent trades
        try:
            import sys; sys.path.insert(0, f"{BASE}/lib"); import common as C
            if len(bars) < 4:
                d = C.cg(f"/networks/{net}/pools/{pool}/ohlcv/minute", {"aggregate": 1, "limit": window_min}, None) or {}
                ol = (((d.get("data") or {}).get("attributes") or {}).get("ohlcv_list") or [])
                bars = sorted([(r[0], float(r[1]), float(r[4])) for r in ol if r and r[0] > now - window_min * 60])
            if not tr:
                d = C.cg(f"/networks/{net}/pools/{pool}/trades", None, None) or {}
                tr = [(float(x["attributes"]["volume_in_usd"] or 0),) for x in d.get("data") or []
                      if float(x["attributes"]["volume_in_usd"] or 0) >= dust and __import__("datetime").datetime.fromisoformat(x["attributes"]["block_timestamp"].replace("Z", "+00:00")).timestamp() > now - 600]
        except Exception: pass
    n_tr = len(tr); vol = sum(x[0] for x in tr)
    moves = [math.log(c / o) for _, o, c in bars if o and c and o > 0 and c > 0]
    up = sum(1 for x in moves if x > 0); tot = sum(moves); pos = sum(x for x in moves if x > 0)
    spike = (max(moves) / pos) if pos > 0 and moves else 1.0
    green = up / len(moves) if moves else 0
    s_tr = min(1, n_tr / 40); s_vol = min(1, vol / 15000); s_green = green; s_spread = max(0, 1 - spike) if len(moves) >= 4 else 0
    s_dir = 1 if tot > 0 else 0
    score = round(0.25 * s_tr + 0.2 * s_vol + 0.2 * s_green + 0.25 * s_spread + 0.1 * s_dir, 3)
    return {"score": score, "nondust_trades_10m": n_tr, "nondust_vol_10m": round(vol), "bars": len(moves), "green_share": round(green, 2),
            "largest_bar_share_of_gain": round(spike, 2), "net_move_pct": round((math.exp(tot) - 1) * 100, 1) if moves else None}
