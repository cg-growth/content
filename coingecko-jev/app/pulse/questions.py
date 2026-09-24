from typesafe_sdk import Choice, Noul, Score

PUMP = ["none", "building", "strong", "euphoric"]
DUMP = ["none", "building", "strong", "capitulating"]
PHASES = ["accumulation", "breakout", "distribution", "capitulation", "ranging"]

QUESTIONS = {
    "pump": Score(
        instructions=(
            "Strength of an ongoing or imminent pump right now, from the last seconds-to-minutes of trading: "
            "short-horizon returns, buy share of flow, accelerating trade rate, oversized buys, price pressing its 5m high."
        ),
        criteria=PUMP,
    ),
    "dump": Score(
        instructions=(
            "Strength of an ongoing or imminent dump or exit right now: falling short-horizon returns, sell share of flow, "
            "oversized sells, price breaking toward its 5m low, a few wallets dominating volume."
        ),
        criteria=DUMP,
    ),
    "phase": Choice(
        instructions="Which market phase best describes the last few minutes?",
        criteria={
            "accumulation": "quiet steady buying, price holding",
            "breakout": "price breaking up on rising activity",
            "distribution": "heavy selling into strength, price stalling near highs",
            "capitulation": "sharp fall on heavy selling",
            "ranging": "no clear direction",
        },
    ),
    "exhaustion": Noul(instructions="Is the current move losing steam and likely to reverse soon?"),
}

CRITERIA_SIZES = {"pump": len(PUMP), "dump": len(DUMP)}
