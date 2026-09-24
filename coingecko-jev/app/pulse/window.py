"""Rolling per-pool state: 1s candles built from trades, trade tape, wallet stats, and derived features."""
import math
import statistics
from collections import deque


class PoolWindow:
    def __init__(self, pool_id: str):
        self.pool_id = pool_id
        self.candles: dict[int, list] = {}  # sec -> [o, h, l, c, v, buy_usd, sell_usd, n]
        self.trades: deque = deque(maxlen=2000)  # (t_ms, side, usd, price)
        self.baseline_1m: list = []  # [(sec, o, h, l, c, v)] oldest first
        self.wallet_stats: dict = {}
        self.median_trade_usd: float | None = None
        self.liquidity_usd: float | None = None
        self.fdv_usd: float | None = None
        self.last_trade_ms = 0
        self.wallet_flow: dict | None = None

    # ---- seeding ----
    def seed_seconds(self, ohlcv_list):
        for ts, o, h, l, c, v in ohlcv_list:
            self.candles.setdefault(int(ts), [o, h, l, c, v, 0.0, 0.0, 0])

    def seed_minutes(self, ohlcv_list):
        self.baseline_1m = sorted((int(r[0]), *r[1:]) for r in ohlcv_list)

    def seed_trades(self, rest_trades):
        """REST trades (newest first) -> tape + wallet stats."""
        usd, wallets = [], {}
        for t in rest_trades:
            v = float(t.get("volume_in_usd") or 0)
            usd.append(v)
            w = t.get("tx_from_address")
            if w:
                wallets[w] = wallets.get(w, 0.0) + v
        self.wallet_stats = wallet_stats(wallets, len(rest_trades))
        if usd:
            self.median_trade_usd = statistics.median(usd)
        if not self.trades:
            for t in reversed(rest_trades[:200]):
                side = "b" if t.get("kind") == "buy" else "s"
                price = float(t.get("price_to_in_usd") if side == "b" else t.get("price_from_in_usd") or 0)
                ts = t.get("block_timestamp")
                if ts:
                    from datetime import datetime

                    ms = int(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp() * 1000)
                    self.trades.append((ms, side, float(t.get("volume_in_usd") or 0), price))

    # ---- live ----
    def add_trade(self, t_ms: int, side: str, usd: float, price: float):
        if not price:
            return None
        self.trades.append((t_ms, side, usd, price))
        self.last_trade_ms = max(self.last_trade_ms, t_ms)
        sec = t_ms // 1000
        c = self.candles.get(sec)
        if c is None:
            c = self.candles[sec] = [price, price, price, price, 0.0, 0.0, 0.0, 0]
        c[1], c[2], c[3] = max(c[1], price), min(c[2], price), price
        c[4] += usd
        c[5 if side == "b" else 6] += usd
        c[7] += 1
        if len(self.candles) > 4000:
            for k in sorted(self.candles)[:1000]:
                del self.candles[k]
        return sec, c

    # ---- features ----
    def closes(self, now_sec: int, seconds: int) -> list[float]:
        """Forward-filled 1s closes for the last `seconds` seconds (oldest first)."""
        keys = [k for k in self.candles if k <= now_sec]
        if not keys:
            return []
        start = now_sec - seconds + 1
        prior = [k for k in keys if k < start]
        last = self.candles[max(prior)][3] if prior else None
        out = []
        for s in range(start, now_sec + 1):
            c = self.candles.get(s)
            if c:
                last = c[3]
            out.append(last)
        first = next((x for x in out if x is not None), None)
        return [x if x is not None else first for x in out] if first is not None else []

    def features(self, now_ms: int) -> dict:
        now_sec = now_ms // 1000
        c300 = self.closes(now_sec, 300)
        return {
            "returns_pct": {
                "10s": pct_change(c300, 10),
                "30s": pct_change(c300, 30),
                "60s": pct_change(c300, 60),
                "5m": pct_change(c300, 300),
            },
            "volatility_60s_vs_4h_baseline": vol_ratio(c300[-61:], self.baseline_1m),
            "flow_10s": flow(self.trades, now_ms, 10_000),
            "flow_60s": flow(self.trades, now_ms, 60_000),
            "largest_trade_60s_vs_median": largest_vs_median(self.trades, now_ms, self.median_trade_usd),
            "trade_rate_acceleration": rate_accel(self.trades, now_ms),
            "distance_from_5m_high_pct": dist_from(c300, max),
            "distance_from_5m_low_pct": dist_from(c300, min),
            "wallets_last_300_trades": self.wallet_stats or None,
            "liquidity_usd": round(self.liquidity_usd) if self.liquidity_usd else None,
        }


def pct_change(closes: list, n: int):
    if len(closes) < 2:
        return None
    base = closes[-min(n + 1, len(closes))]
    if not base:
        return None
    return round((closes[-1] / base - 1) * 100, 3)


def _log_returns(xs):
    return [math.log(b / a) for a, b in zip(xs, xs[1:]) if a and b and a > 0 and b > 0]


def vol_ratio(closes_1s: list, baseline_1m: list):
    """Realised vol of 1s returns over the window, scaled to per-minute, vs stdev of 1m returns over the baseline."""
    r1 = _log_returns([c for c in closes_1s if c])
    rb = _log_returns([row[4] for row in baseline_1m if row[4]])
    if len(r1) < 10 or len(rb) < 10:
        return None
    v1 = statistics.pstdev(r1) * math.sqrt(60)
    vb = statistics.pstdev(rb)
    if not vb:
        return None
    return round(v1 / vb, 2)


def flow(trades, now_ms: int, window_ms: int) -> dict:
    lo = now_ms - window_ms
    b = s = bu = su = 0
    for t, side, usd, _ in reversed(trades):
        if t < lo:
            break
        if t > now_ms:
            continue
        if side == "b":
            b, bu = b + 1, bu + usd
        else:
            s, su = s + 1, su + usd
    tot = bu + su
    return {"buys": b, "sells": s, "buy_usd": round(bu), "sell_usd": round(su), "buy_share": round(bu / tot, 3) if tot else None}


def largest_vs_median(trades, now_ms: int, median: float | None):
    lo = now_ms - 60_000
    big = max((usd for t, _, usd, _ in trades if lo <= t <= now_ms), default=None)
    if big is None or not median:
        return None
    return round(big / median, 1)


def rate_accel(trades, now_ms: int):
    last10 = sum(1 for t, *_ in trades if now_ms - 10_000 <= t <= now_ms) / 10
    prev50 = sum(1 for t, *_ in trades if now_ms - 60_000 <= t < now_ms - 10_000) / 50
    if not prev50:
        return None if not last10 else 9.99
    return round(last10 / prev50, 2)


def dist_from(closes, fn):
    xs = [c for c in closes if c]
    if not xs:
        return None
    ref = fn(xs)
    return round((xs[-1] / ref - 1) * 100, 3) if ref else None


def wallet_stats(volume_by_wallet: dict, n_trades: int) -> dict:
    if not volume_by_wallet:
        return {}
    tot = sum(volume_by_wallet.values()) or 1
    top = sorted(volume_by_wallet.values(), reverse=True)
    return {
        "trades": n_trades,
        "unique_wallets": len(volume_by_wallet),
        "top_wallet_volume_share_pct": round(top[0] / tot * 100, 1),
        "top5_wallets_volume_share_pct": round(sum(top[:5]) / tot * 100, 1),
    }


def normalized_closes(closes: list, n: int = 60) -> list:
    xs = closes[-n:]
    if not xs or not xs[0]:
        return []
    return [round((x / xs[0] - 1) * 100, 2) for x in xs]
