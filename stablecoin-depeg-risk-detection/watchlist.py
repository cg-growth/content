import requests

url = "https://api.coingecko.com/api/v3/coins/markets"
params = {"vs_currency": "usd", "category": "stablecoins",
          "order": "market_cap_desc", "per_page": 250, "page": 1}

# Returns a list of coin IDs the rest of this guide will consume
watchlist = [c["id"] for c in requests.get(url, params=params, timeout=10).json()]

print(f"Stablecoin watchlist ({len(watchlist)} coins, ordered by market cap)")
print("-" * 250)
for i, coin_id in enumerate(watchlist, 1):
    print(f"  {i:>2}. {coin_id}")
