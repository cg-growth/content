"""Tick / tape sanitation shared by BOTH books (valuation, risk triggers, fills).
Rules (thresholds in TH, overridable via risk.json "tick_sanity"):
  * Same pool only: reference prints are G1 ticks whose pa == the position's pool and G2 trades of that pool.
  * Dust: trades with usd < dust_usd ($1) are ignored for price.
  * Reference = median of the last ref_n (40) clean prints within ref_window_s (300s), in log space; spread = MAD*1.4826.
  * Band: |ln(p/median)| <= max(ln(1+min_band), k_mad*MAD) and never beyond ln(max_band) without confirmation.
  * Big move (outside band) is accepted only if >= confirm_n (2) independent non-dust prints (distinct tx) in the last
    confirm_s (45s) are within confirm_tol (15%) of it. Otherwise the tick is REJECTED and the reference median is used.
  * Trade print vs reserve cross-check: a trade whose implied size (usd / pu) disagrees with token amount by > 50% is a
    units/decimals artifact and is dropped.
  * Rejections are logged (rate-limited) and counted in ticks.db (own WAL file; no market.db/paper.db lock contention).
Fills use mid = sanitized price and constant-product execution against the pool's quote reserve (liq/2): out = y*V/(y+V);
output can never exceed the reserve (clips.fill / core.cp_exit)."""
import math, time, sqlite3, os, json, statistics as S, threading
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
BASE = _ROOT
TH = {"dust_usd": 1.0, "ref_n": 40, "ref_window_s": 300, "min_band": 0.35, "max_band": 3.0, "k_mad": 6.0,
      "confirm_n": 2, "stale_ref_s": 60, "confirm_s": 45, "confirm_tol": 0.15, "min_refs": 3}
def th():
    try: return {**TH, **(json.load(open(f"{BASE}/risk.json")).get("tick_sanity") or {})}
    except Exception: return TH
_L = threading.Lock(); _CNT = {}; _LAST_LOG = {}
def _tdb():
    c = sqlite3.connect(f"{BASE}/ticks.db", timeout=5); c.execute("pragma journal_mode=wal"); c.execute("pragma busy_timeout=5000")
    c.execute("create table if not exists rejects(ts real, ca text, pool text, raw real, ref real, dev real, src text, reason text)")
    c.execute("create table if not exists counts(day text, src text, accepted integer default 0, rejected integer default 0, primary key(day, src))")
    return c
def _count(src, ok, ca=None, pool=None, raw=None, ref=None, dev=None, reason=None):
    day = time.strftime("%Y-%m-%d")
    try:
        c = _tdb()
        c.execute("insert or ignore into counts(day,src) values(?,?)", (day, src))
        c.execute(f"update counts set {'accepted' if ok else 'rejected'}={'accepted' if ok else 'rejected'}+1 where day=? and src=?", (day, src))
        if not ok: c.execute("insert into rejects values(?,?,?,?,?,?,?,?)", (time.time(), ca, pool, raw, ref, dev, src, reason))
        c.commit(); c.close()
    except Exception: pass
    if not ok:
        k = (ca, reason)
        with _L:
            if time.time() - _LAST_LOG.get(k, 0) > 60:
                _LAST_LOG[k] = time.time(); print(time.strftime("%Y-%m-%dT%H:%M:%S"), "[ticks] REJECT", src, (ca or "")[:10], f"raw={raw:.6g}" if raw else "", f"ref={ref:.6g}" if ref else "", reason, flush=True)
def _mdb():
    m = sqlite3.connect(f"file:{BASE}/market.db?mode=ro", uri=True, timeout=3); m.execute("pragma busy_timeout=3000"); return m
def prints(ca, pool, now=None, m=None, window=None):
    """-> list of (t, price, usd, tx, kind) clean-candidate prints for this pool (dust & unit-mismatch removed)."""
    k = th(); now = now or time.time(); own = m is None; m = m or _mdb(); out = []
    if window: k = {**k, "ref_window_s": window}
    try:
        q = "select t, p, pa from prices where ta=? and t>? and t<=? and p>0 order by t desc limit ?"
        for t, p, pa in m.execute(q, (ca, now - k["ref_window_s"], now + 5, k["ref_n"])):
            if pool and pa and pa.lower() != pool.lower(): continue
            out.append((t, p, None, None, "G1"))
        if pool:
            for t, usd, pu, amt, tx in m.execute("select t, usd, pu, amt, tx from trades where pool=? and t>? and t<=? and pu>0 order by t desc limit ?",
                                                (pool, now - k["ref_window_s"], now + 5, k["ref_n"])):
                if (usd or 0) < k["dust_usd"]: continue
                if amt and usd and abs(math.log((usd / pu) / amt)) > math.log(1.5): continue   # units/decimals mismatch
                out.append((t, pu, usd, tx, "G2"))
            if len(out) < k["min_refs"]:   # fresh position / no stream yet: OHLCV closes of the same pool (15s/1m, up to 15 min)
                for t, cl in m.execute("select t, c from ohlcv where pool=? and iv in ('15s','1m') and t>? and t<=? and c>0 order by t desc limit 20",
                                       (pool, now - 900, now + 5)):
                    out.append((t, cl, None, None, "G3"))
    finally:
        if own: m.close()
    return out
def sane(ca, pool, px, src="?", now=None, m=None, confirm_with=None):
    """Return (price, info). price is px if it passes, else the reference median (or None when nothing trustworthy)."""
    if not px or px <= 0 or not math.isfinite(px): return None, {"ok": False, "reason": "no price"}
    k = th(); now = now or time.time()
    try: P = prints(ca, pool, now, m)
    except Exception as e: return px, {"ok": True, "reason": f"no refs ({e})"}
    refs = [p for (_, p, *_r) in P]
    if len(refs) < k["min_refs"]:   # quiet pool: fall back to older history (6h) of the same pool as the reference
        try: P = prints(ca, pool, now, m, window=6 * 3600); refs = [p for (_, p, *_r) in P]
        except Exception: pass
    if len(refs) < k["min_refs"]:
        return px, {"ok": True, "reason": "few refs", "n": len(refs)}
    lr = [math.log(x) for x in refs]; med = S.median(lr); mad = S.median([abs(x - med) for x in lr]) * 1.4826
    thr = min(max(math.log(1 + k["min_band"]), k["k_mad"] * mad), math.log(k["max_band"]))
    dev = math.log(px) - med; ref = math.exp(med)
    if abs(dev) <= thr:
        _count(src, True); return px, {"ok": True, "ref": ref, "dev": dev, "thr": thr, "n": len(refs)}
    # big move: needs >= confirm_n independent non-dust prints near px in the last confirm_s
    rec = [(tx or f"g1:{t}", p) for (t, p, usd, tx, kind) in P if now - t <= k["confirm_s"] and abs(math.log(p / px)) <= math.log(1 + k["confirm_tol"])
           and (kind == "G2")]
    if confirm_with: rec += [(f"x{i}", p) for i, p in enumerate(confirm_with) if p and abs(math.log(p / px)) <= math.log(1 + k["confirm_tol"])]
    if len({r[0] for r in rec}) >= k["confirm_n"]:
        _count(src, True); return px, {"ok": True, "ref": ref, "dev": dev, "thr": thr, "confirmed": len(rec), "n": len(refs)}
    newest = max((t for (t, *_r) in P), default=0)
    if dev < 0 and now - newest > k.get("stale_ref_s", 60):   # price fell and no fresh prints contradict it: accept (never hold value up on stale refs)
        _count(src, True); return px, {"ok": True, "ref": ref, "dev": dev, "thr": thr, "n": len(refs), "reason": "down-move, stale refs"}
    _count(src, False, ca, pool, px, ref, dev, f"dev {math.exp(dev):.3g}x vs median of {len(refs)} prints (band ±{(math.exp(thr)-1)*100:.0f}%), unconfirmed")
    # winsorized fallback: median of clean recent prints
    return ref, {"ok": False, "ref": ref, "dev": dev, "thr": thr, "n": len(refs), "reason": "rejected"}
def stats(day=None):
    c = _tdb(); r = c.execute("select src, accepted, rejected from counts where day=?", (day or time.strftime("%Y-%m-%d"),)).fetchall(); c.close(); return r
