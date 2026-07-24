import requests
from config import BASE_URL, HEADERS

def get_category_ids():
    url = f"{BASE_URL}/coins/categories/list"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

# --- Optional: same request using the CoinGecko Python SDK ---
# Install it with: pip install coingecko-sdk
#
# from coingecko_sdk import Coingecko
#
# client = Coingecko(demo_api_key="YOUR_API_KEY", environment="demo")
# categories = client.coins.categories.get_list()
#
# On a paid plan, use: Coingecko(pro_api_key="YOUR_API_KEY", environment="pro")

def get_tokens_in_category(category_id):
    # per_page accepts up to 250; page through if a category is larger
    url = f"{BASE_URL}/coins/markets"
    params = {"vs_currency": "usd", "category": category_id, "per_page": 250, "page": 1}
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()

# SDK equivalent: client.coins.markets.get(vs_currency="usd", category="xstocks-ecosystem")

def get_contract_addresses(coin_id):
    # tickers, market_data, community_data, and developer_data default to true
    # on this endpoint; disabling them keeps the response small
    url = f"{BASE_URL}/coins/{coin_id}"
    params = {"localization": "false", "tickers": "false", "market_data": "false",
              "community_data": "false", "developer_data": "false"}
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json().get("detail_platforms", {})

# SDK equivalent: client.coins.get_id("tesla-xstock", localization=False, tickers=False, market_data=False)

if __name__ == "__main__":
    # Step 1: find the category ID for the tokenized stocks you want
    categories = get_category_ids()
    for c in categories:
        if "stock" in c["category_id"]:
            print(c["category_id"], "-", c["name"])

    # Step 2: pull every token in that category, then resolve its contract addresses
    tokens = get_tokens_in_category("xstocks-ecosystem")
    rows = [
        {"symbol": t["symbol"].upper(), "coingecko_id": t["id"],
         "asset_platform": platform, "contract_address": details.get("contract_address")}
        for t in tokens[:10]
        for platform, details in get_contract_addresses(t["id"]).items()
    ]

    # Fixed-width print so columns line up regardless of address length
    print(f"{'SYMBOL':<8}{'COINGECKO_ID':<16}{'ASSET_PLATFORM':<16}{'CONTRACT_ADDRESS'}")
    print("-" * 90)
    for r in rows:
        print(f"{r['symbol']:<8}{r['coingecko_id']:<16}{r['asset_platform']:<16}{r['contract_address']}")
