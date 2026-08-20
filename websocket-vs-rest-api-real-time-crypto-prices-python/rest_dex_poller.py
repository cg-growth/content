import os
import time
from datetime import datetime, timezone

import requests

API_KEY = os.environ.get("COINGECKO_API_KEY", "")
BASE_URL = "https://api.coingecko.com/api/v3"
HEADERS = {"x-cg-demo-api-key": API_KEY} if API_KEY else {}

NETWORK = "eth"
TOKEN_ADDRESSES = ["0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"]  # WETH
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", 30))


def fetch_token_prices(network, token_addresses):
    """Fetch current onchain token prices for one or more contract addresses."""
    response = requests.get(
        f"{BASE_URL}/onchain/simple/networks/{network}/token_price/{','.join(token_addresses)}",
        headers=HEADERS,
        params={"include_24hr_price_change": "true"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()

    # Official CoinGecko Python SDK equivalent:
    #   client.onchain.simple.networks.token_price.get_addresses(
    #       ",".join(token_addresses), network=network, include_24hr_price_change=True
    #   )


def poll_forever(network, token_addresses, interval=POLL_INTERVAL):
    """Print a timestamped price line for each token on every poll."""
    while True:
        payload = fetch_token_prices(network, token_addresses)
        attrs = payload["data"]["attributes"]
        polled_at = datetime.now(timezone.utc).strftime("%H:%M:%S")

        for address in token_addresses:
            price = attrs["token_prices"].get(address)
            change = attrs["h24_price_change_percentage"].get(address)
            if price is None:
                print(f"[{polled_at}] {address:<44} no data returned")
                continue

            print(
                f"[{polled_at}] {address:<44} ${float(price):>12,.2f}  "
                f"{float(change):+6.2f}% 24h"
            )

        print("-" * 90)
        time.sleep(interval)


if __name__ == "__main__":
    poll_forever(NETWORK, TOKEN_ADDRESSES)
