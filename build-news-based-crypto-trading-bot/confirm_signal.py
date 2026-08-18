from config import MIN_SENTIMENT_SCORE, MIN_CONFIDENCE

MAX_ALREADY_MOVED_PCT = 8.0

def should_trade(score, confidence, coin):
    """Apply every gate between a scored headline and an order."""
    if score < MIN_SENTIMENT_SCORE or confidence < MIN_CONFIDENCE:
        return False, "below score or confidence threshold"

    change_1h = coin.get("price_change_percentage_1h_in_currency") or 0.0

    # A bullish story on a falling coin means the market knows something
    # the headline does not
    if change_1h < 0:
        return False, f"price disagrees with signal ({change_1h:+.1f}% 1h)"

    if change_1h > MAX_ALREADY_MOVED_PCT:
        return False, f"move already priced in ({change_1h:+.1f}% 1h)"

    return True, "confirmed"

def should_exit(score, confidence, coin):
    """A simple, illustrative exit rule: reverse out of a position on a
    sufficiently bearish, price-confirmed signal. This is not a production
    exit strategy -- see the note below the paper-trading example for what
    a real one needs."""
    change_1h = coin.get("price_change_percentage_1h_in_currency") or 0.0
    return (score <= -MIN_SENTIMENT_SCORE and confidence >= MIN_CONFIDENCE
            and change_1h < 0)

if __name__ == "__main__":
    cases = [
        ("agrees, not yet moved", 0.68, 0.81, {"price_change_percentage_1h_in_currency": 1.2}),
        ("price disagrees",       0.68, 0.81, {"price_change_percentage_1h_in_currency": -0.6}),
        ("already priced in",     0.68, 0.81, {"price_change_percentage_1h_in_currency": 9.4}),
        ("low confidence",        0.41, 0.30, {"price_change_percentage_1h_in_currency": 0.5}),
    ]
    for label, score, confidence, coin in cases:
        ok, reason = should_trade(score, confidence, coin)
        print(f"{'TRADE' if ok else 'SKIP ':<6} {label:<24} {reason}")

    exit_cases = [
        ("bearish, price confirms", -0.71, 0.79, {"price_change_percentage_1h_in_currency": -1.4}),
        ("bearish, not yet moved",  -0.71, 0.79, {"price_change_percentage_1h_in_currency": 0.3}),
    ]
    for label, score, confidence, coin in exit_cases:
        exit_now = should_exit(score, confidence, coin)
        change_1h = coin["price_change_percentage_1h_in_currency"]
        print(f"{'EXIT' if exit_now else 'HOLD':<6} {label:<24} score {score:+.2f}, {change_1h:+.1f}% 1h")
