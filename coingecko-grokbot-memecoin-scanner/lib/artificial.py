"""Artificial-chart check for engineered price action, aimed at new pools.

Candles: Pool OHLCV `/onchain/networks/{net}/pools/{pool}/ohlcv/second?aggregate=1`
and `aggregate=15` while the pool is younger than `new_pool_max_min`, otherwise
`/ohlcv/minute`. A 4xx (or any failed read) on `second` falls back to minute
candles. Duplicate timestamps are merged before scoring: first open, max high,
min low, last close, summed volume.

Clear scores become a Discard. Borderline scores are a penalty only. Missing
candles stay unknown and do not discard. Thresholds live in risk.json
`artificial_chart` and default conservative so ordinary noise is left alone.
"""
import statistics

DEFAULTS = {
    "enabled": True,
    "new_pool_max_min": 30,
    "min_candles": 8,
    "min_steps": 6,
    "step_cv_max": 0.12,
    "mild_step_cv_max": 0.28,
    "max_pullback_share": 0.08,
    "mild_pullback_share": 0.20,
    "flat_eps": 0.003,
    "min_drift": 0.12,
    "mild_drift": 0.08,
    "interval_cv_max": 0.20,
    "body_match_share": 0.75,
    "body_tol": 0.15,
    "wick_body_max": 0.20,
    "clear_score": 75,
    "borderline_score": 55,
    "borderline_penalty": 8,
    "clock_interval_cv": 0.15,
    "clock_min_gaps": 8,
    "clock_size_cv": 0.12,
    "clock_max_unique_ratio": 0.40,
    "vol_unique_ratio": 0.25,
    "vol_vs_liq": 1.5,
    "few_buyers": 3,
    "few_buyers_vs_liq": 2.0,
}


def cfg(over=None):
    out = dict(DEFAULTS)
    for k, v in (over or {}).items():
        if str(k).startswith("_") or v is None: continue
        out[k] = v
    return out


def _num(x):
    try: return float(x)
    except (TypeError, ValueError): return None


def merge_ohlcv(rows):
    """Merge duplicate timestamps. API order within a timestamp is kept.

    First open, max high, min low, last close, summed volume. One candle per
    timestamp, then sorted by time. -> (candles, n_duplicates_folded)
    candles are [t, o, h, l, c, v].
    """
    groups = {}
    order = []
    folded = 0
    for row in rows or []:
        if not row or len(row) < 5: continue
        t_raw = row[0]
        t_key = int(t_raw) if _num(t_raw) is not None and float(t_raw) == int(float(t_raw)) else t_raw
        o, h, l, c = (_num(row[1]), _num(row[2]), _num(row[3]), _num(row[4]))
        if None in (o, h, l, c): continue
        v = _num(row[5]) if len(row) > 5 else 0.0
        if v is None: v = 0.0
        g = groups.get(t_key)
        if g is None:
            groups[t_key] = {"t": _num(t_raw) if _num(t_raw) is not None else t_raw, "o": o, "h": h, "l": l, "c": c, "v": v}
            order.append(t_key)
        else:
            folded += 1
            g["h"] = max(g["h"], h)
            g["l"] = min(g["l"], l)
            g["c"] = c
            g["v"] = (g["v"] or 0) + v
    candles = [[groups[t]["t"], groups[t]["o"], groups[t]["h"], groups[t]["l"], groups[t]["c"], groups[t]["v"]] for t in order]
    candles.sort(key=lambda r: (r[0] is None, r[0]))
    return candles, folded


def _cv(xs):
    if len(xs) < 3: return None
    mu = statistics.fmean(xs)
    if mu == 0: return None
    return statistics.pstdev(xs) / abs(mu)


def _returns(candles):
    out = []
    for i in range(1, len(candles)):
        prev, cur = candles[i - 1][4], candles[i][4]
        if prev and cur and prev > 0:
            out.append((cur - prev) / prev)
    return out


def _interval_cv(candles):
    ts = [c[0] for c in candles if isinstance(c[0], (int, float))]
    gaps = [ts[i + 1] - ts[i] for i in range(len(ts) - 1) if ts[i + 1] > ts[i]]
    if len(gaps) < 4: return None
    return _cv(gaps)


def score_candles(candles, settings=None):
    """Score one merged candle series. Higher means more artificial. None if too few candles."""
    k = cfg(settings)
    candles = candles or []
    if len(candles) < int(k["min_candles"]):
        return {"score": None, "reasons": [], "n": len(candles), "signals": {}}
    rets = _returns(candles)
    if len(rets) < int(k["min_steps"]):
        return {"score": None, "reasons": [], "n": len(candles), "signals": {}}
    eps = float(k["flat_eps"])
    pos = [r for r in rets if r > eps]
    neg = [r for r in rets if r < -eps]
    pullback = len(neg) / len(rets)
    step_cv = _cv(pos) if len(pos) >= int(k["min_steps"]) else None
    drift = 0.0
    if candles[0][1] and candles[-1][4] and candles[0][1] > 0:
        drift = candles[-1][4] / candles[0][1] - 1
    iv = _interval_cv(candles)
    points = 0
    reasons = []
    strong = (step_cv is not None and step_cv <= float(k["step_cv_max"]) and pullback <= float(k["max_pullback_share"])
              and drift >= float(k["min_drift"]) and (iv is None or iv <= float(k["interval_cv_max"])))
    mild = (not strong and step_cv is not None and step_cv <= float(k["mild_step_cv_max"]) and pullback <= float(k["mild_pullback_share"])
            and drift >= float(k["mild_drift"]))
    if strong:
        points += 80
        reasons.append("staircase climb (near-identical steps at fixed intervals, almost no pullbacks)")
    elif mild:
        points += 55
        reasons.append("steady climb with similar steps and few pullbacks")
    elif step_cv is not None and step_cv <= float(k["mild_step_cv_max"]) and drift >= float(k["mild_drift"]) and pullback <= float(k["mild_pullback_share"]):
        points += 25
        reasons.append("very low variance of returns with steady drift")
    # Near-identical bodies and almost no wicks.
    bodies = []
    quiet = 0
    considered = 0
    for o, h, l, c in ((x[1], x[2], x[3], x[4]) for x in candles):
        if not o or o <= 0: continue
        body = abs(c - o) / o
        wick = max(0.0, (h - l) - abs(c - o)) / o
        if body <= eps: continue
        considered += 1
        bodies.append(body)
        if wick <= float(k["wick_body_max"]) * body:
            quiet += 1
    if len(bodies) >= int(k["min_candles"]):
        med = statistics.median(bodies)
        if med > 0:
            close = sum(1 for b in bodies if abs(b - med) / med <= float(k["body_tol"]))
            share = close / len(bodies)
            wick_share = quiet / considered if considered else 0
            if share >= float(k["body_match_share"]) and wick_share >= float(k["body_match_share"]):
                points += 30
                reasons.append("clusters of near-identical candle bodies with no wicks")
    score = min(100, points)
    return {
        "score": score,
        "reasons": reasons,
        "n": len(candles),
        "signals": {
            "step_cv": None if step_cv is None else round(step_cv, 3),
            "pullback_share": round(pullback, 3),
            "drift": round(drift, 3),
            "interval_cv": None if iv is None else round(iv, 3),
        },
    }


def _trade_attrs(trades):
    out = []
    for row in trades or []:
        a = row.get("attributes") if isinstance(row, dict) and isinstance(row.get("attributes"), dict) else row
        if not isinstance(a, dict): continue
        if a.get("is_anomalous") is True or a.get("is_anomaly") is True: continue
        out.append(a)
    return out


def score_trades(trades, liquidity=None, settings=None):
    """Clock-like rhythm and volume-without-buyers. Points to add, and reasons."""
    k = cfg(settings)
    rows = _trade_attrs(trades)
    reasons = []
    points = 0
    if len(rows) < int(k["min_candles"]):
        return points, reasons
    import human_pattern as HP
    sizes = [x for x in (HP._usd(a) for a in rows) if x > 0]
    stamps = sorted(t for t in (HP._ts(a) for a in rows) if t is not None)
    gaps = [stamps[i + 1] - stamps[i] for i in range(len(stamps) - 1) if stamps[i + 1] > stamps[i]]
    gap_cv = _cv(gaps) if len(gaps) >= int(k["clock_min_gaps"]) else None
    size_cv = _cv(sizes)
    buys = [a for a in rows if (a.get("kind") or "").lower() == "buy"] or rows
    addrs = [a.get("tx_from_address") for a in buys if a.get("tx_from_address")]
    uniq = len(set(addrs))
    ratio = uniq / max(len(buys), 1)
    if (gap_cv is not None and gap_cv <= float(k["clock_interval_cv"]) and size_cv is not None
            and size_cv <= float(k["clock_size_cv"]) and ratio <= float(k["clock_max_unique_ratio"])):
        points += 20
        reasons.append("clock-like trade rhythm (regular intervals, similar sizes, few wallets)")
    vol = sum(sizes)
    liq = _num(liquidity)
    if liq and liq > 0 and vol > 0:
        thin = ratio <= float(k["vol_unique_ratio"]) and vol / liq >= float(k["vol_vs_liq"])
        few = uniq <= int(k["few_buyers"]) and vol / liq >= float(k["few_buyers_vs_liq"]) and len(rows) >= int(k["min_candles"])
        if thin or few:
            points += 30
            reasons.append("volume without buyers (high volume vs few unique buyers or vs liquidity)")
    return points, reasons


def _band(score, k):
    if score is None: return "unknown"
    if score >= float(k["clear_score"]): return "clear"
    if score >= float(k["borderline_score"]): return "borderline"
    return "ok"


def combine(candle_hit, trade_points, trade_reasons, settings=None):
    k = cfg(settings)
    if not candle_hit or candle_hit.get("score") is None:
        if not trade_points:
            return {"score": None, "band": "unknown", "reasons": [], "n_candles": (candle_hit or {}).get("n") or 0}
        score = min(100, trade_points)
        return {"score": score, "band": _band(score, k), "reasons": trade_reasons, "n_candles": 0}
    score = min(100, int(candle_hit["score"]) + int(trade_points or 0))
    reasons = list(candle_hit.get("reasons") or []) + list(trade_reasons or [])
    return {"score": score, "band": _band(score, k), "reasons": reasons, "n_candles": candle_hit.get("n") or 0, "signals": candle_hit.get("signals") or {}}


def fetch_ohlcv(net, pool, timeframe, aggregate, mc=None):
    """-> (merged_candles, folded, failed). failed is True on a 4xx or any read error."""
    import common as C
    path = f"/networks/{net}/pools/{pool}/ohlcv/{timeframe}"
    try:
        o = C.cg(path, {"aggregate": aggregate, "limit": 300, "currency": "usd"}, mc)
    except Exception:
        return [], 0, True
    if not o:
        return [], 0, True
    rows = ((o.get("data") or {}).get("attributes") or {}).get("ohlcv_list") or []
    candles, folded = merge_ohlcv(rows)
    return candles, folded, False


def assess(net, pool, age_min=None, liquidity=None, trades=None, mc=None, settings=None, fetch=None):
    """Read OHLCV (and use trades when provided) and score engineered price action.

    `fetch(timeframe, aggregate) -> (candles, folded, failed)` overrides HTTP in tests.
    """
    k = cfg(settings)
    if not k.get("enabled", True):
        return {"score": None, "band": "unknown", "reasons": [], "timeframe": None, "n_candles": 0, "merged_duplicates": 0}
    getter = fetch or (lambda tf, ag: fetch_ohlcv(net, pool, tf, ag, mc))
    young = age_min is not None and float(age_min) < float(k["new_pool_max_min"])
    series = []
    folded = 0
    if young:
        for tf, ag, label in (("second", 1, "1s"), ("second", 15, "15s")):
            candles, nfold, failed = getter(tf, ag)
            folded += nfold or 0
            if failed: continue
            series.append((label, candles))
        if not series:
            candles, nfold, failed = getter("minute", 1)
            folded += nfold or 0
            if not failed:
                series.append(("1m", candles))
    else:
        candles, nfold, failed = getter("minute", 1)
        folded += nfold or 0
        if not failed:
            series.append(("1m", candles))
    tp, tr = score_trades(trades, liquidity, k)
    best = None
    for label, candles in series:
        hit = score_candles(candles, k)
        merged = combine(hit, tp, tr, k)
        merged["timeframe"] = label
        merged["merged_duplicates"] = folded
        if best is None or (merged.get("score") or -1) > (best.get("score") or -1):
            best = merged
    if best is None:
        merged = combine(None, tp, tr, k)
        merged.update(timeframe=None, merged_duplicates=folded, n_candles=0)
        return merged
    if best.get("band") == "borderline":
        best["penalty"] = float(k["borderline_penalty"])
    else:
        best["penalty"] = 0
    return best
