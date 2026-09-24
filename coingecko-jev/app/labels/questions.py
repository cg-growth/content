from typesafe_sdk import Choice, Noul, Score

MOMENTUM = ["pumping", "climbing", "flat", "cooling", "dumping"]
LMH = ["low", "medium", "high"]

QUESTIONS = {
    "momentum": Choice(
        instructions="Classify this token's current price momentum using the short (5m, 1h) and longer (6h, 24h) price changes and buy/sell pressure.",
        criteria={
            "pumping": "sharp, accelerating rise right now",
            "climbing": "steady rise",
            "flat": "little net movement",
            "cooling": "was rising, now fading or pulling back",
            "dumping": "sharp fall right now",
        },
    ),
    "demand": Score(
        instructions="How organic is the buying demand? Organic = many distinct buyers, few trades per wallet, buyers growing with price. Artificial = few wallets doing many trades, volume far above liquidity.",
        criteria=["artificial", "mixed", "organic"],
    ),
    "wash_like": Noul(
        instructions="Does the trading activity look wash-traded: many trades per unique wallet and 24h volume far larger than liquidity?"
    ),
    "whale_heavy": Noul(
        instructions="Is the token supply dangerously concentrated in a few wallets (e.g. top 10 holders own well over half)? Holder concentration is the key input; ignore it if unavailable."
    ),
    "rug_risk": Score(
        instructions=(
            "Rug-pull risk for a buyer today. Raise risk for: active mint or freeze authority, honeypot, very young pool, "
            "tiny liquidity across all pools, extreme holder concentration, no liquidity lock on a new token. "
            "Lower risk for established tokens: listed on CoinGecko, months or years old, many holders, deep liquidity across all pools."
        ),
        criteria=LMH,
    ),
    "thin_liq": Noul(
        instructions=(
            "Is the token's liquidity too thin to trade safely: small total liquidity across all pools (tens of thousands of USD), "
            "or 24h volume many times larger than liquidity so single trades move the price sharply? "
            "A large-cap token with millions in liquidity is not thin even if liquidity is small relative to FDV."
        )
    ),
    "fresh": Noul(instructions="Is this a fresh launch still in early price discovery (pool only hours or a few days old)?"),
    "sell_pressure": Score(
        instructions="How strong is sell pressure right now (recent sells vs buys, distinct sellers, falling short-term price)?",
        criteria=LMH,
    ),
}

CRITERIA_SIZES = {"demand": 3, "rug_risk": 3, "sell_pressure": 3}
