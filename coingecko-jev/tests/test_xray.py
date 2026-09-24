from app.xray.features import activity_features, is_protocol_holder, pnl_features, token_features
from app.xray.profiler import copy_worthy
from app.xray.service import aggregate


def test_pnl_features():
    attrs = {
        "total_tokens": 4, "total_realized_pnl_usd": "1000", "total_unrealized_pnl_usd": "50",
        "token_stats": [
            {"realized_pnl_usd": "900", "total_buy_count": 2, "total_sell_count": 2, "total_buy_usd": "100", "total_sell_usd": "1000"},
            {"realized_pnl_usd": "150", "total_buy_count": 1, "total_sell_count": 1, "total_buy_usd": "50", "total_sell_usd": "200"},
            {"realized_pnl_usd": "-50", "total_buy_count": 1, "total_sell_count": 1, "total_buy_usd": "100", "total_sell_usd": "50"},
            {"realized_pnl_usd": "0", "total_buy_count": 1, "total_sell_count": 0, "total_buy_usd": "0", "total_sell_usd": "0"},
        ],
    }
    f = pnl_features(attrs)
    assert f["win_rate_tokens"] == round(2 / 3, 3)
    assert f["profit_concentration_top_token"] == round(900 / 1050, 3)
    assert f["total_buys"] == 5 and f["total_sells"] == 4
    assert pnl_features(None) == {"available": False}


def test_activity_features_bot_cadence():
    trades = [{"block_timestamp": f"2026-09-23T12:00:{s:02d}Z", "pool_address": "p1" if (s // 2) % 2 else "p2", "kind": "buy" if s % 3 else "sell"} for s in range(0, 60, 2)]
    a = activity_features(trades, now=1790000000)
    assert a["recent_trades"] == 30
    assert a["median_seconds_between_trades"] == 2
    assert a["distinct_pools_recent"] == 2
    assert activity_features([])["recent_trades"] == 0


def test_token_features_entry_timing_and_flow():
    row = {"_source": "trader", "average_buy_price_usd": "0.5", "total_buy_usd": "1000", "total_sell_usd": "300", "percentage": "1.5"}
    ctx = {"price_usd": "1.0", "pool_created_at": "2026-09-23T10:00:00Z"}
    trades = [
        {"block_timestamp": "2026-09-23T10:03:00Z", "kind": "buy", "volume_in_usd": "700"},
        {"block_timestamp": "2026-09-23T11:00:00Z", "kind": "sell", "volume_in_usd": "300"},
    ]
    now = 1790161200  # 2026-09-23T11:00:00Z + a bit
    t = token_features(row, trades, ctx, now=now)
    assert t["first_trade_minutes_after_pool_launch"] == 3
    assert t["price_vs_avg_buy_multiple"] == 2.0
    assert t["supply_share_pct"] == 1.5


def test_protocol_holder_detection():
    assert is_protocol_holder({"_source": "holder", "label": "Gnosis Safe Proxy", "total_buy_count": None, "average_buy_price_usd": None})
    assert not is_protocol_holder({"_source": "holder", "label": None, "total_buy_count": None, "average_buy_price_usd": None})
    assert not is_protocol_holder({"_source": "trader", "label": "x", "total_buy_count": None, "average_buy_price_usd": None})


def test_copy_worthy_rule():
    a = {"skill": {"value": 80}, "insider": {"value": 0.2}}
    g = {"recent_activity": {"days_since_last_trade": 3}}
    assert copy_worthy("proven_trader", a, g)
    assert not copy_worthy("market_maker_bot", a, g)
    assert not copy_worthy("proven_trader", {**a, "skill": {"value": 60}}, g)
    assert not copy_worthy("proven_trader", a, {"recent_activity": {"days_since_last_trade": None}})


def test_aggregate():
    w = lambda persona, **k: {"persona": persona, "scored": persona != "protocol", "skill": k.get("skill", 0), "insider": k.get("insider", 0),
                              "copy_worthy": k.get("cw", False), "token": {"bought_usd": k.get("b", 0), "sold_usd": k.get("s", 0),
                              "supply_share_pct": k.get("sup", 0), "net_flow_24h_usd": k.get("net", 0)}}
    agg = aggregate([
        w("market_maker_bot", b=800, s=800),
        w("proven_trader", skill=80, b=200, s=0, net=150, cw=True),
        w("insider_like", insider=0.9, sup=12, s=200),
        w("protocol", sup=40),
    ])
    assert agg["smart_wallets"] == 1 and agg["smart_net_flow_24h_usd"] == 150
    assert agg["insider_like_supply_pct"] == 12
    assert agg["bot_volume_share"] == round(1600 / 2000, 3)
    assert agg["copyable_wallets"] == 1
    assert agg["composition"]["protocol"]["supply_pct"] == 40
