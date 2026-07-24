import pandas as pd
import requests
from config import BASE_URL, HEADERS

def get_historical_price(coin_id, days="30"):
    url = f"{BASE_URL}/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": days}
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()

# SDK equivalent: client.coins.market_chart.get("tesla-xstock", vs_currency="usd", days="30")

if __name__ == "__main__":
    data = get_historical_price("tesla-xstock", days="30")
    df = pd.DataFrame(data["prices"], columns=["timestamp", "price"])
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")

    print(f"{'DATE':<18}{'PRICE':>10}")
    print("-" * 28)
    for _, row in df[["date", "price"]].tail().iterrows():
        print(f"{row['date'].strftime('%Y-%m-%d %H:%M'):<18}{row['price']:>10,.2f}")
