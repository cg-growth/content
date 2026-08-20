"""Poll the CoinGecko REST API for crypto prices at a sensible interval."""

import os
import time
from datetime import datetime, timezone

import requests

API_KEY = os.environ.get("COINGECKO_API_KEY", "")
BASE_URL = "https://api.coingecko.com/api/v3"
HEADERS = {"x-cg-demo-api-key": API_KEY} if API_KEY else {}

COINS = ["bitcoin", "ethereum", "solana"]  # up to 515 ids in one call
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", 60))  # Demo cache 60s; paid 20s


def fetch_prices(coin_ids):
    """Fetch current prices for several coins in a single request."""
    response = requests.get(
        f"{BASE_URL}/simple/price",
        headers=HEADERS,
        params={
            "ids": ",".join(coin_ids),
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_last_updated_at": "true",
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()

    # Official CoinGecko Python SDK equivalent:
    #   pip install coingecko-sdk
    #
    #   from coingecko_sdk import Coingecko
    #   client = Coingecko(demo_api_key=API_KEY, environment="demo")
    #   response = client.simple.price.get(
    #       ids=",".join(coin_ids),
    #       vs_currencies="usd",
    #       include_24hr_change=True,
    #       include_last_updated_at=True,
    #   )


def poll_forever(coin_ids, interval=POLL_INTERVAL):
    """Print a timestamped price line for each coin on every poll."""
    while True:
        prices = fetch_prices(coin_ids)
        polled_at = datetime.now(timezone.utc).strftime("%H:%M:%S")

        for coin_id in coin_ids:
            data = prices.get(coin_id)
            if not data:
                print(f"[{polled_at}] {coin_id:<10} no data returned")
                continue

            price = data.get("usd")
            change = data.get("usd_24h_change")
            updated_at = data.get("last_updated_at")
            age = int(time.time()) - updated_at if updated_at else None

            print(
                f"[{polled_at}] {coin_id:<10} ${price:>12,.2f}  "
                f"{change:+6.2f}% 24h   data age: {age}s"
            )

        print("-" * 68)
        time.sleep(interval)


if __name__ == "__main__":
    poll_forever(COINS)
