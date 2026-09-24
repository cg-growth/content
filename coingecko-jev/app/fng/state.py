from ..util import rnd


def build_state(coin: dict, comps: dict, headlines: list[dict], insights: list[dict] | None = None) -> dict:
    ath_pct = coin.get("ath_change_percentage")
    state = {
        "coin": f"{coin.get('name')} ({(coin.get('symbol') or '').upper()})",
        "market": {
            "price_usd": coin.get("current_price"),
            "change_pct": {
                "24h": rnd(coin.get("price_change_percentage_24h_in_currency")),
                "7d": rnd(coin.get("price_change_percentage_7d_in_currency")),
                "30d": rnd(coin.get("price_change_percentage_30d_in_currency")),
            },
            "pct_from_all_time_high": rnd(ath_pct, 1),
            "market_cap_rank": coin.get("market_cap_rank"),
            "fear_greed_components_0_to_100": {k: v for k, v in comps.items() if v is not None},
        },
        "headlines": {f"h{i}": f"[{h['source']}, {h['posted_at']}] {h['title']}" for i, h in enumerate(headlines)},
    }
    if insights:
        state["coingecko_coin_insights"] = {
            f"i{i}": f"[{it['posted_at']}] {it['title']}: {it['description']}" for i, it in enumerate(insights)
        }
    return state
