from app.pulse.window import (
    PoolWindow,
    flow,
    largest_vs_median,
    normalized_closes,
    pct_change,
    rate_accel,
    vol_ratio,
    wallet_stats,
)


def test_candles_built_from_trades():
    w = PoolWindow("p")
    w.add_trade(10_000, "b", 100, 1.0)
    w.add_trade(10_400, "s", 50, 0.9)
    w.add_trade(10_900, "b", 25, 1.2)
    o, h, l, c, v, bu, su, n = w.candles[10]
    assert (o, h, l, c) == (1.0, 1.2, 0.9, 1.2)
    assert (v, bu, su, n) == (175, 125, 50, 3)
    assert w.add_trade(11_000, "b", 1, 0) is None


def test_closes_forward_fill():
    w = PoolWindow("p")
    w.add_trade(100_000, "b", 1, 1.0)
    w.add_trade(103_000, "b", 1, 2.0)
    assert w.closes(104, 5) == [1.0, 1.0, 1.0, 2.0, 2.0]


def test_pct_change_and_normalize():
    xs = [1.0] * 50 + [1.1] * 10
    assert pct_change(xs, 10) == 10.0
    assert pct_change(xs, 60) == 10.0
    assert pct_change([1.0], 10) is None
    assert normalized_closes([2.0, 2.2, 1.8], 3) == [0.0, 10.0, -10.0]


def test_flow_and_share():
    trades = [(1000, "b", 100, 1), (5000, "s", 300, 1), (9000, "b", 100, 1), (20000, "b", 999, 1)]
    f = flow(trades, 10_000, 10_000)
    assert f == {"buys": 2, "sells": 1, "buy_usd": 200, "sell_usd": 300, "buy_share": 0.4}


def test_largest_vs_median_and_accel():
    trades = [(t, "b", 10, 1) for t in range(0, 50_000, 5_000)] + [(t, "b", 50, 1) for t in range(50_000, 60_000, 500)]
    assert largest_vs_median(trades, 60_000, 10) == 5.0
    assert rate_accel(trades, 60_000) == 10.0
    assert rate_accel([], 60_000) is None


def test_vol_ratio_volatile_vs_flat():
    base = [(i, 1, 1, 1, 1 + (0.01 if i % 2 else 0), 1) for i in range(60)]
    calm = [1.0 + (0.0001 if i % 2 else 0) for i in range(61)]
    wild = [1.0 + (0.02 if i % 2 else 0) for i in range(61)]
    assert vol_ratio(wild, base) > vol_ratio(calm, base)
    assert vol_ratio([1.0] * 5, base) is None


def test_wallet_stats():
    s = wallet_stats({"a": 60, "b": 30, "c": 10}, 5)
    assert s == {"trades": 5, "unique_wallets": 3, "top_wallet_volume_share_pct": 60.0, "top5_wallets_volume_share_pct": 100.0}
