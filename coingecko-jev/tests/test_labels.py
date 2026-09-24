from app.jev import norm_score
from app.labels.labeler import chips, composite, momentum
from app.labels.state import build_state


def _row(**kw):
    base = {
        "id": "pool1",
        "pool_name": "ABC / SOL",
        "token": {"address": "tok1", "symbol": "ABC"},
        "change": {"m5": 1.234, "h1": 5.0, "h6": None, "h24": 20.0},
        "volume": {"m5": 100.0, "h1": 1000.0, "h6": 5000.0, "h24": 20000.0},
        "txns": {"h1": {"buys": 40, "sells": 10, "buyers": 20, "sellers": 5}},
        "reserve_usd": 10000.0,
        "fdv_usd": 1_000_000.0,
        "age_h": 3.5,
        "locked_liquidity_pct": None,
    }
    base.update(kw)
    return base


def test_state_solana_tiers_and_authorities():
    info = {
        "holders": {"count": 100, "distribution_percentage": {"top_10": "51.3", "11_20": "12.9", "21_40": "12.4", "rest": "23.4"}},
        "mint_authority": "no",
        "freeze_authority": "yes",
        "is_honeypot": "unknown",
        "gt_score": 74.75,
    }
    s = build_state(_row(info=info), "solana")
    assert s["holder_concentration_pct"] == {"top_10": 51.3, "11_20": 12.9, "21_40": 12.4, "rest": 23.4}
    assert s["mint_authority"] == "renounced"
    assert s["freeze_authority"] == "active"
    assert s["honeypot"] == "unknown"
    assert s["trading_activity"]["h1"]["buys_per_buyer"] == 2.0
    assert s["trading_activity"]["h1"]["buy_sell_ratio"] == 4.0
    assert s["volume_24h_to_liquidity"] == 2.0
    assert s["liquidity_to_fdv"] == 0.01


def test_state_evm_tiers_and_nulls():
    info = {"holders": {"distribution_percentage": {"top_10": "69.9", "11_30": "16.4", "31_50": "9.7", "rest": "4.1"}},
            "mint_authority": None, "freeze_authority": None, "is_honeypot": False}
    s = build_state(_row(info=info), "robinhood")
    assert set(s["holder_concentration_pct"]) == {"top_10", "11_30", "31_50", "rest"}
    assert s["mint_authority"] == "n/a on EVM"
    assert s["honeypot"] == "no"


def test_state_missing_info_is_null_not_faked():
    s = build_state(_row(info=None, txns={}), "solana")
    assert s["holder_concentration_pct"] is None
    assert s["gt_score"] is None
    assert s["trading_activity"]["h1"]["buys_per_buyer"] is None
    assert "note" in s


def test_norm_score():
    assert norm_score(0, 3) == 0
    assert norm_score(2, 3) == 100
    assert norm_score(1.56, 3) == 78.0
    assert norm_score(2, 5) == 50
    assert norm_score(9, 3) == 100


def _answers(**v):
    a = {
        "momentum": {"type": "choice", "choice": "pumping", "confidence": 0.3},
        "demand": {"type": "score", "value": 80, "confidence": 0.9},
        "rug_risk": {"type": "score", "value": 70, "confidence": 0.4},
        "sell_pressure": {"type": "score", "value": 10, "confidence": 0.8},
        "wash_like": {"type": "noul", "value": 0.1},
        "whale_heavy": {"type": "noul", "value": 0.7},
        "thin_liq": {"type": "noul", "value": 0.2},
        "fresh": {"type": "noul", "value": 0.9},
    }
    a.update(v)
    return a


def test_chip_mapping_and_low_conf():
    c = {x["id"]: x for x in chips(_answers())}
    assert set(c) == {"organic", "whale", "rug", "fresh"}
    assert c["rug"]["low_conf"] is True
    assert c["organic"]["low_conf"] is False
    assert momentum(_answers())["low_conf"] is True


def test_composite():
    # 0.35*70 + 0.2*20 + 0.15*10 + 0.15*70 + 0.15*20
    assert composite(_answers()) == 43.5
