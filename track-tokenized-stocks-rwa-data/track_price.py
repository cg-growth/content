import requests
from config import BASE_URL, HEADERS

def get_simple_price(coin_ids):
    # Lightweight price lookup for specific tokenized stocks by coin ID
    url = f"{BASE_URL}/simple/price"
    params = {
        "ids": ",".join(coin_ids),
        "vs_currencies": "usd",
        "include_market_cap": "true",
        "include_24hr_vol": "true",
        "include_24hr_change": "true",
    }
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()

# SDK equivalent: client.simple.price.get(ids="tesla-xstock,nvidia-xstock,sp500-xstock", vs_currencies="usd", include_market_cap=True, include_24hr_vol=True, include_24hr_change=True)

if __name__ == "__main__":
    prices = get_simple_price(["tesla-xstock", "nvidia-xstock", "sp500-xstock"])
    for coin_id, data in prices.items():
        print(coin_id, f"${data['usd']:,.2f}", f"{data['usd_24h_change']:+.2f}% 24h",
              f"mcap ${data['usd_market_cap']:,.0f}", f"vol ${data['usd_24h_vol']:,.0f}")
