from typesafe_sdk import Noul, Score

MOOD = ["extreme fear", "fear", "neutral", "greed", "extreme greed"]


def build_questions(coin_name: str, n_headlines: int, n_insights: int = 0) -> dict:
    q = {}
    for i in range(n_headlines):
        q[f"h{i}_about"] = Noul(instructions=f"Is headline h{i} primarily about {coin_name}?")
        q[f"h{i}_mood"] = Score(instructions=f"What sentiment does headline h{i} express toward {coin_name}?", criteria=MOOD)
    for i in range(n_insights):
        q[f"i{i}_mood"] = Score(
            instructions=f"What sentiment does CoinGecko coin insight i{i} (title and summary) express toward {coin_name}?",
            criteria=MOOD,
        )
    q["overall"] = Score(
        instructions=f"Given {coin_name}'s market data, CoinGecko coin insights and news, where is market sentiment on the fear–greed scale right now?",
        criteria=MOOD,
    )
    return q


def criteria_sizes(n_headlines: int, n_insights: int = 0) -> dict:
    sizes = {f"h{i}_mood": len(MOOD) for i in range(n_headlines)}
    sizes.update({f"i{i}_mood": len(MOOD) for i in range(n_insights)})
    sizes["overall"] = len(MOOD)
    return sizes
