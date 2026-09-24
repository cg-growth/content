"""Market components of the per-coin Fear & Greed index. Each returns 0–100 (higher = greedier) or None."""
import math
import statistics

WEIGHTS = {"momentum": 0.20, "volatility": 0.15, "volume": 0.15, "range": 0.10}


def clip(x, lo=-1.0, hi=1.0):
    return max(lo, min(hi, x))


def momentum(prices: list[float]):
    """Price vs 30d and 90d moving averages. ±15% from MA30 / ±30% from MA90 saturate."""
    if len(prices) < 30:
        return None
    p = prices[-1]
    ma30 = statistics.fmean(prices[-30:])
    ma90 = statistics.fmean(prices[-90:])
    d30 = (p / ma30 - 1) / 0.15 if ma30 else 0
    d90 = (p / ma90 - 1) / 0.30 if ma90 else 0
    return round(50 + 50 * clip((clip(d30) + clip(d90)) / 2), 1)


def _log_returns(xs):
    return [math.log(b / a) for a, b in zip(xs, xs[1:]) if a > 0 and b > 0]


def volatility(prices: list[float]):
    """7d realised vol vs 90d average; higher recent vol → fear. Ratio 2× → 0, ≤0× → 100, 1× → 50."""
    r = _log_returns(prices[-91:])
    if len(r) < 20:
        return None
    rv7 = statistics.pstdev(r[-7:])
    rv90 = statistics.pstdev(r)
    if not rv90:
        return 50.0
    return round(50 - 50 * clip(rv7 / rv90 - 1), 1)


def volume(volumes: list[float], volume_24h: float | None, change_24h_pct: float | None):
    """24h volume vs 30d average, signed by 24h direction. 2× average on a +5% day → 100; on a −5% day → 0."""
    if not volume_24h or change_24h_pct is None or len(volumes) < 10:
        return None
    avg = statistics.fmean(volumes[-30:])
    if not avg:
        return None
    heat = clip(volume_24h / avg - 1, 0, 1)
    direction = clip(change_24h_pct / 5)
    return round(50 + 50 * heat * direction + 10 * direction * (1 - heat), 1)


def range_position(prices: list[float]):
    xs = prices[-90:]
    if len(xs) < 10:
        return None
    lo, hi = min(xs), max(xs)
    if hi == lo:
        return 50.0
    return round((xs[-1] - lo) / (hi - lo) * 100, 1)


def components(prices, volumes, volume_24h, change_24h_pct) -> dict:
    return {
        "momentum": momentum(prices),
        "volatility": volatility(prices),
        "volume": volume(volumes, volume_24h, change_24h_pct),
        "range": range_position(prices),
    }


def weighted(values: dict, weights: dict):
    """Weighted mean over components that are not None; weights re-normalised."""
    pairs = [(values[k], w) for k, w in weights.items() if values.get(k) is not None]
    tot = sum(w for _, w in pairs)
    if not tot:
        return None
    return round(sum(v * w for v, w in pairs) / tot, 1)


def backfill(prices: list[float], volumes: list[float], times_ms: list[int], days: int = 90) -> list[dict]:
    """Market-only index for each of the last `days` days, using only data available up to that day."""
    out = []
    n = len(prices)
    for i in range(max(30, n - days), n):
        p, v = prices[: i + 1], volumes[: i + 1]
        chg = (p[-1] / p[-2] - 1) * 100 if len(p) > 1 and p[-2] else None
        comps = components(p, v[:-1], v[-1], chg)
        val = weighted(comps, WEIGHTS)
        if val is not None:
            out.append({"t": times_ms[i], "market": val})
    return out
