import requests
from config import BASE_URL, HEADERS

WATCHLIST = ["openai-pre-ipo", "spacex-pre-ipo", "gold", "silver"]

def get_watchlist_snapshot(ids):
    url = f"{BASE_URL}/rwas/markets"
    params = {
        "ids": ",".join(ids),
        "price_change_percentage": "24h",
    }
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    snapshot = get_watchlist_snapshot(WATCHLIST)
    # The markets endpoint can only sort by market cap, volume, or id,
    # so sorting by biggest mover has to happen client-side after the fetch
    snapshot.sort(key=lambda x: x["tokenized_market_data"]["price_change_percentage_24h_in_currency"] or 0, reverse=True)
    print(f"{'Asset':<20}{'Price':>12}{'24h %':>10}{'Market Cap':>18}")
    for rwa in snapshot:
        data = rwa["tokenized_market_data"]
        change = data["price_change_percentage_24h_in_currency"] or 0
        print(f"{rwa['id']:<20}{data['current_price']:>12,.2f}{change:>+9.2f}%{data['market_cap']:>18,.0f}")
