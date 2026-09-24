"""News + Coin Insights weighting, final index and buckets."""
from datetime import datetime, timezone

from .market import WEIGHTS as MARKET_WEIGHTS

BASE_WEIGHTS = {**MARKET_WEIGHTS, "holistic": 0.10}
# The 30% sentiment share: Coin Insights (curated) outweigh raw news when available.
SENTIMENT_WEIGHTS = {
    (True, True): {"insights": 0.20, "news": 0.10},
    (True, False): {"insights": 0.30},
    (False, True): {"news": 0.30},
    (False, False): {},
}
WEIGHTS = {**BASE_WEIGHTS, "insights": 0.20, "news": 0.10}

RELEVANCE_MIN = 0.5
HALF_LIFE_H = 24
THIN_NEWS_MIN = 3
THIN_NEWS_WINDOW_H = 96
INSIGHT_HALF_LIFE_H = 48
INSIGHT_WINDOW_H = 7 * 24

BUCKETS = [(24, "Extreme Fear"), (44, "Fear"), (55, "Neutral"), (75, "Greed"), (100, "Extreme Greed")]


def bucket(v):
    if v is None:
        return None
    for hi, name in BUCKETS:
        if v <= hi:
            return name
    return BUCKETS[-1][1]


def age_hours(iso: str, now: datetime | None = None):
    now = now or datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    return max(0.0, (now - dt).total_seconds() / 3600)


def news_mood(headlines: list[dict], now: datetime | None = None):
    """headlines: [{about (0–1), mood (0–100), posted_at}]. Returns (score, relevant_count_in_window)."""
    num = den = 0.0
    recent_relevant = 0
    for h in headlines:
        about, mood = h.get("about"), h.get("mood")
        if about is None or mood is None or about < RELEVANCE_MIN:
            continue
        age = age_hours(h.get("posted_at"), now)
        if age is None:
            continue
        if age <= THIN_NEWS_WINDOW_H:
            recent_relevant += 1
        w = about * 0.5 ** (age / HALF_LIFE_H)
        num += w * mood
        den += w
    return (round(num / den, 1) if den else None), recent_relevant


def insights_mood(insights: list[dict], now: datetime | None = None):
    """insights: [{mood, posted_at}] already filtered to the coin. Only insights within 7 days count."""
    num = den = 0.0
    recent = 0
    for it in insights:
        mood = it.get("mood")
        age = age_hours(it.get("posted_at"), now)
        if mood is None or age is None or age > INSIGHT_WINDOW_H:
            continue
        recent += 1
        w = 0.5 ** (age / INSIGHT_HALF_LIFE_H)
        num += w * mood
        den += w
    return (round(num / den, 1) if den else None), recent


def final_index(comps: dict, thin_news: bool, has_insights: bool = False):
    weights = {**BASE_WEIGHTS, **SENTIMENT_WEIGHTS[(has_insights, not thin_news)]}
    pairs = [(comps[k], w) for k, w in weights.items() if comps.get(k) is not None]
    tot = sum(w for _, w in pairs)
    if not tot:
        return None, {}
    used = {k: round(w / tot, 3) for k, w in weights.items() if comps.get(k) is not None}
    return round(sum(v * w for v, w in pairs) / tot, 1), used
