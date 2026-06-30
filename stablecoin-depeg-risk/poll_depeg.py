import requests, time
from datetime import datetime

PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"
THRESHOLD, INTERVAL = 0.005, 30  # 0.5% deviation, poll every 30 seconds


def get_watchlist():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": "usd", "category": "stablecoins",
              "order": "market_cap_desc", "per_page": 250, "page": 1}
    return [c["id"] for c in requests.get(url, params=params, timeout=10).json()]


def check_depeg(watchlist):
    params = {"ids": ",".join(watchlist), "vs_currencies": "usd",
              "include_24hr_change": "true", "include_last_updated_at": "true"}
    data = requests.get(PRICE_URL, params=params, timeout=10).json()

    breaches = []
    for coin, p in data.items():
        if p.get("usd") is None:
            continue
        dev = abs(p["usd"] - 1.0)
        if dev > THRESHOLD:
            breaches.append((coin, p["usd"], dev))

    ts = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{ts}] Checked {len(data)} stablecoins, {len(breaches)} off peg")
    for coin, price, dev in sorted(breaches, key=lambda x: -x[2]):
        print(f"  DEPEG  {coin:<30} ${price:.4f}  ({dev*100:.2f}% off peg)")


if __name__ == "__main__":
    watchlist = get_watchlist()
    while True:
        check_depeg(watchlist)
        time.sleep(INTERVAL)
