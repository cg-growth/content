"""Shared helpers. Secrets come ONLY from env and are never printed/logged/written."""
import threading, json, os, sqlite3, time, urllib.request, urllib.parse, urllib.error, datetime, sys
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
BASE = _ROOT
sys.path.insert(0, BASE + "/lib")
sys.path.insert(0, BASE + "/telegram"); sys.path.insert(0, BASE)
MARKET = f"{BASE}/market.db"; PAPER = os.environ.get("PAPER_DB", f"{BASE}/paper.db")
from localtz import LOCAL_TZ as MYT, TZ_LABEL  # MYT kept as the internal name for the local zone
_CL = threading.RLock()
PRO = "https://pro-api.coingecko.com/api/v3/onchain"
def now_iso(): return datetime.datetime.now(MYT).isoformat(timespec="seconds")
def today(): return datetime.datetime.now(MYT).strftime("%Y-%m-%d")
def redact(s):
    s = str(s)
    for k in ("COINGECKO_PRO_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_FORWARD_KEY", "TELEGRAM_FORWARD_URL"):
        v = os.environ.get(k)
        if v: s = s.replace(v, "<redacted>")
    return s
def logger(name):
    def log(*a): print(now_iso(), f"[{name}]", *[redact(x) for x in a], flush=True)
    return log
def risk_cfg(): return json.load(open(f"{BASE}/risk.json"))
MSCHEMA = """
create table if not exists ohlcv(net text, pool text, iv text, t integer, o real, h real, l real, c real, v real, src text, primary key(net,pool,iv,t));
create table if not exists trades(net text, pool text, tx text, ty text, usd real, pu real, amt real, t integer, frm text, src text, primary key(tx,ty,usd));
create table if not exists prices(net text, ta text, p real, r real, tr real, m real, v real, pa text, t integer);
create index if not exists prices_i on prices(ta, t);
create index if not exists trades_i on trades(pool, t);
create table if not exists credits(day text, kind text, n real, primary key(day,kind));
create table if not exists kv(k text primary key, v text, at text);
"""
def mdb():
    c = sqlite3.connect(MARKET, timeout=30, check_same_thread=False); c.row_factory = sqlite3.Row
    c.execute("pragma busy_timeout=30000"); c.execute("pragma journal_mode=wal"); c.executescript(MSCHEMA); return c
def credit(c, kind, n):
    c.execute("insert into credits values(?,?,?) on conflict(day,kind) do update set n=n+excluded.n", (today(), kind, n))
def kv_set(c, k, v): c.execute("insert or replace into kv values(?,?,?)", (k, json.dumps(v), now_iso()))
def kv_get(c, k, d=None):
    r = c.execute("select v from kv where k=?", (k,)).fetchone(); return json.loads(r[0]) if r else d
def cg(path, params=None, mc=None, timeout=25):
    """Pro REST GET (1 credit/call). Key from env header only."""
    url = PRO + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"accept": "application/json", "x-cg-pro-api-key": os.environ["COINGECKO_PRO_API_KEY"]})
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r: out = json.load(r); break
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(2 + 2 * i); continue
            if e.code in (404, 400, 422): out = None; break
            if i == 2: raise RuntimeError(f"HTTP {e.code} {path}")
            time.sleep(1)
        except Exception as e:
            if i == 2: raise RuntimeError(redact(f"{type(e).__name__} {path}"))
            time.sleep(1)
    if mc is not None:
        with _CL: credit(mc, "rest", 1); mc.commit()
    return out
def pdb():
    import core; return core.db()
PSCHEMA = """
create table if not exists risk_plans(ca text primary key, network text, pool text, entry_px real, opened_at text,
  sl_pct real, sl_px real, be_moved integer default 0, tp json, trail_active integer default 0, peak_px real,
  auto integer default 1, time_stop_asked integer default 0, notes text, updated_at text);
create table if not exists risk_events(id integer primary key autoincrement, ts text, ca text, kind text, detail text, action text);
create table if not exists risk_prompts(id integer primary key autoincrement, ca text, kind text, sell_pct real, reason text, created real, status text);
create table if not exists decisions(id integer primary key autoincrement, ts text, ca text, network text, pool text, action text, usd real, rec_usd real, tag text, confidence text, score real, source text);
create table if not exists outcomes(ca text, network text, pool text, symbol text, alerted_at text, alert_px real, tag text, confidence text,
  score real, decision text, px_1h real, px_6h real, px_24h real, ret_1h real, ret_6h real, ret_24h real, max_px real, primary key(ca, alerted_at));
create table if not exists watchlist(ca text primary key, network text, pool text, symbol text, tag text, added_at text, expires real);
"""
def pinit(c): c.executescript(PSCHEMA); return c
def tracked():
    """-> positions [(net,pool,ca)], watch [(net,pool,ca)] from paper.db."""
    c = pinit(pdb())
    pos = [(r["network"], r["pool"], r["ca"]) for r in c.execute("select network,pool,ca from positions")]
    c.execute("delete from watchlist where expires < ?", (time.time(),)); c.commit()
    w = [(r["network"], r["pool"], r["ca"]) for r in c.execute("select network,pool,ca from watchlist")]
    c.close()
    try:   # also stream the AI book's positions (read-only)
        a = sqlite3.connect(f"file:{BASE}/auto.db?mode=ro", uri=True, timeout=5)
        pos += [tuple(r) for r in a.execute("select network,pool,ca from positions") if tuple(r) not in pos]; a.close()
    except Exception: pass
    pset = {p[2] for p in pos}
    return pos, [x for x in w if x[2] not in pset]
def last_price(mc, ca, max_age=45):
    """freshest of G1 price / 1s close / trade price; -> (price, src, age_s) or None"""
    t = time.time(); best = None
    r = mc.execute("select p,t from prices where ta=? order by t desc limit 1", (ca,)).fetchone()
    if r and r["p"]: best = (r["p"], "G1", t - r["t"])
    for q, src in (("select c p, t+1 t from ohlcv o join (select pa from prices where ta=? order by t desc limit 1) x on o.pool=x.pa where iv='1s' order by t desc limit 1", "G3"),):
        r = mc.execute(q, (ca,)).fetchone()
        if r and (best is None or t - r["t"] < best[2]): best = (r["p"], src, t - r["t"])
    return best if best and best[2] <= max_age else None

def backfill(mc, net, pool, which=("1m", "15s")):
    """REST candles into market.db: 1m (minute/1), 15s (second/15), 1s (second/1). Returns {iv: n}."""
    spec = {"1m": ("minute", 1), "15s": ("second", 15), "1s": ("second", 1)}; out = {}
    for iv in which:
        tf, ag = spec[iv]
        o = cg(f"/networks/{net}/pools/{pool}/ohlcv/{tf}", {"aggregate": ag, "limit": 300, "currency": "usd"}, mc)
        rows = ((o or {}).get("data") or {}).get("attributes", {}).get("ohlcv_list") or []
        for t, op, h, l, cl, v in rows:
            mc.execute("insert or replace into ohlcv values(?,?,?,?,?,?,?,?,?,'rest')", (net, pool, iv, t, op, h, l, cl, v))
        out[iv] = len(rows)
    mc.commit(); return out
