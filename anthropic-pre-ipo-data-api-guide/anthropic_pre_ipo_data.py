"""
Companion script for "How to Get Anthropic Pre-IPO Data With the CoinGecko API"
Requires: Python 3.8+, `pip install requests`, and a CoinGecko API Pro key
with Analyst-tier access for the top_holders/top_traders/holders_chart calls.
"""

import os
import requests

API_KEY = os.environ["COINGECKO_PRO_API_KEY"]
BASE_URL = "https://pro-api.coingecko.com/api/v3"
HEADERS = {"x-cg-pro-api-key": API_KEY}

RWA_ID = "anthropic-pre-ipo"
TOKEN_ADDRESS = "Pren1FvFX6J3E4kXhJuCiAD5aDmGEb7qJRncwA8Lkhw"
NETWORK = "solana"


def resolve_rwa_id():
    resp = requests.get(f"{BASE_URL}/rwas/list", headers=HEADERS)
    resp.raise_for_status()
    # client.rwas.get_list()
    match = next((r for r in resp.json() if r["id"] == RWA_ID), None)
    if not match:
        raise SystemExit(f"{RWA_ID} not found in /rwas/list")
    return match


def get_asset_snapshot():
    params = {"tokens": "true", "tokenized_market_data": "true"}
    resp = requests.get(f"{BASE_URL}/rwas/{RWA_ID}", headers=HEADERS, params=params)
    resp.raise_for_status()
    # client.rwas.get_id(id=RWA_ID, tokens=True, tokenized_market_data=True)
    return resp.json()


def get_issuer_snapshot(issuer_id):
    resp = requests.get(f"{BASE_URL}/rwas/issuers/{issuer_id}", headers=HEADERS)
    resp.raise_for_status()
    # client.rwas.issuers.get_id(issuer_id)
    return resp.json()


def get_live_tickers():
    resp = requests.get(f"{BASE_URL}/rwas/{RWA_ID}/tickers", headers=HEADERS)
    resp.raise_for_status()
    # client.rwas.tickers.get(id=RWA_ID)
    return resp.json()["tickers"]


def get_price_history(days="30"):
    resp = requests.get(
        f"{BASE_URL}/rwas/{RWA_ID}/market_chart", headers=HEADERS, params={"days": days}
    )
    resp.raise_for_status()
    # client.rwas.market_chart.get(id=RWA_ID, days=days)
    return resp.json()


def get_holder_and_trader_activity():
    onchain_base = f"{BASE_URL}/onchain/networks/{NETWORK}/tokens/{TOKEN_ADDRESS}"
    holders = requests.get(f"{onchain_base}/top_holders", headers=HEADERS, params={"holders": "5"})
    holders.raise_for_status()
    # client.onchain.networks.tokens.top_holders.get(address=TOKEN_ADDRESS, network=NETWORK, holders="5")
    traders = requests.get(f"{onchain_base}/top_traders", headers=HEADERS, params={"traders": "5"})
    traders.raise_for_status()
    # client.onchain.networks.tokens.top_traders.get(token_address=TOKEN_ADDRESS, network_id=NETWORK, traders="5")
    chart = requests.get(f"{onchain_base}/holders_chart", headers=HEADERS, params={"days": "30"})
    chart.raise_for_status()
    # client.onchain.networks.tokens.holders_chart.get(token_address=TOKEN_ADDRESS, network=NETWORK, days="30")
    return holders.json(), traders.json(), chart.json()


def main():
    listing = resolve_rwa_id()
    print(f"Resolved: {listing['name']} ({listing['id']}), asset_type={listing['asset_type']}")

    asset = get_asset_snapshot()
    market = asset["tokenized_market_data"]
    token = asset["tokens"][0]
    print(f"Tokenized price: ${market['current_price']:,.2f}")
    print(f"Tokenized market cap: ${market['market_cap']:,.2f}")
    print(f"24h volume: ${market['total_volume']:,.2f}")
    print(f"Issued by: {token['issuer_details']['name']} on {list(token['platforms'].keys())[0]}")

    issuer = get_issuer_snapshot(token["issuer_details"]["id"])
    print(f"\n{issuer['name']} issuer profile:")
    print(f"  Market cap: ${issuer['market_cap']:,.2f}")
    print(f"  24h volume: ${issuer['volume_24h']:,.2f}")
    print(f"  Tokenizes {len(issuer['tokens'])} assets total")

    tickers = get_live_tickers()
    print(f"\n{len(tickers)} live venue tickers:")
    for t in tickers[:5]:
        flags = []
        if t["is_stale"]:
            flags.append("STALE")
        if t["is_anomaly"]:
            flags.append("ANOMALY")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        usd_price = t["converted_last"].get("usd")  # not every venue quotes a USD pair
        price_str = f"${usd_price:,.2f}" if usd_price is not None else "n/a"
        print(f"  {t['market']['name']}: {price_str}{flag_str}")

    history = get_price_history(days="30")
    prices = history["tokenized_prices"]
    print(f"\n{len(prices)} price points over the last 30 days")
    print(f"  First: {prices[0]}")
    print(f"  Last:  {prices[-1]}")

    holders, traders, holders_chart = get_holder_and_trader_activity()
    holder_list = holders["data"]["attributes"]["holders"]
    trader_list = traders["data"]["attributes"]["traders"]
    holder_counts = holders_chart["data"]["attributes"]["token_holders_list"]
    print(f"\nTop holder controls {holder_list[0]['percentage']}% of supply")
    print(f"Top trader realized PnL: ${float(trader_list[0]['realized_pnl_usd']):,.2f}")
    print(f"Holder count: {holder_counts[0][1]} -> {holder_counts[-1][1]} over the window")


if __name__ == "__main__":
    main()
