from datetime import datetime, timedelta, timezone

from app.fng import market
from app.fng.index import bucket, final_index, insights_mood, news_mood


def series(start, step, n):
    return [start * (1 + step) ** i for i in range(n)]


def test_momentum_rising_falling_flat():
    assert market.momentum(series(100, 0.01, 120)) > 80
    assert market.momentum(series(100, -0.01, 120)) < 20
    assert market.momentum([100.0] * 120) == 50
    assert market.momentum([100.0] * 10) is None


def test_volatility_recent_spike_is_fear():
    calm = [100 * (1 + (0.005 if i % 2 else -0.005)) for i in range(84)]
    spiky = calm + [100 * (1 + (0.08 if i % 2 else -0.08)) for i in range(7)]
    assert market.volatility(spiky) < 20
    assert 40 <= market.volatility(calm) <= 60


def test_volume_signed_by_direction():
    vols = [1e6] * 30
    assert market.volume(vols, 2e6, 6) == 100
    assert market.volume(vols, 2e6, -6) == 0
    assert market.volume(vols, 1e6, 0) == 50
    assert market.volume(vols, None, 3) is None


def test_range_position():
    assert market.range_position(list(range(1, 91))) == 100
    assert market.range_position(list(range(90, 0, -1))) == 0
    assert market.range_position([5.0] * 90) == 50


def test_weighted_renormalises():
    assert market.weighted({"momentum": 100, "volatility": None, "volume": None, "range": 0}, market.WEIGHTS) == round(100 * 0.2 / 0.3, 1)


def test_news_relevance_and_recency():
    now = datetime(2026, 9, 23, 12, tzinfo=timezone.utc)
    iso = lambda h: (now - timedelta(hours=h)).isoformat()
    hs = [
        {"about": 0.95, "mood": 90, "posted_at": iso(1)},
        {"about": 0.9, "mood": 10, "posted_at": iso(48)},
        {"about": 0.1, "mood": 0, "posted_at": iso(0)},
    ]
    score, n = news_mood(hs, now)
    assert 70 < score < 90
    assert n == 2
    assert news_mood([], now) == (None, 0)


def test_thin_news_reweighting():
    comps = {"momentum": 60, "volatility": 60, "volume": 60, "range": 60, "news": 0, "holistic": 60}
    full, used = final_index(comps, thin_news=False)
    thin, used_thin = final_index(comps, thin_news=True)
    assert full == 42.0
    assert thin == 60.0
    assert "news" not in used_thin and abs(sum(used_thin.values()) - 1) < 0.01


def test_insights_outweigh_news_when_available():
    comps = {"momentum": 50, "volatility": 50, "volume": 50, "range": 50, "holistic": 50, "insights": 100, "news": 0}
    v, used = final_index(comps, thin_news=False, has_insights=True)
    assert used["insights"] == 0.2 and used["news"] == 0.1
    assert v == 50 + 0.2 * 50 - 0.1 * 50
    v_thin, used_thin = final_index(comps, thin_news=True, has_insights=True)
    assert used_thin["insights"] == 0.3 and "news" not in used_thin
    v_none, used_none = final_index({**comps, "insights": None}, thin_news=False, has_insights=False)
    assert used_none["news"] == 0.3 and "insights" not in used_none


def test_insights_mood_recency_and_window():
    now = datetime(2026, 9, 23, 12, tzinfo=timezone.utc)
    iso = lambda h: (now - timedelta(hours=h)).isoformat()
    score, n = insights_mood([{"mood": 90, "posted_at": iso(2)}, {"mood": 10, "posted_at": iso(96)}, {"mood": 0, "posted_at": iso(24 * 10)}], now)
    assert n == 2 and score > 70
    assert insights_mood([{"mood": 50, "posted_at": iso(24 * 8)}], now) == (None, 0)


def test_buckets():
    assert [bucket(v) for v in (0, 24, 25, 50, 56, 80, None)] == ["Extreme Fear", "Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed", None]


def test_backfill_uses_only_past_data():
    p = series(100, 0.01, 180)
    v = [1e6] * 180
    t = list(range(180))
    out = market.backfill(p, v, t, 90)
    assert len(out) == 90 and out[0]["t"] == 90
