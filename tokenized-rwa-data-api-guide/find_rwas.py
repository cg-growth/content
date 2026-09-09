import requests
from config import BASE_URL, HEADERS

def get_rwa_list(asset_type=None):
    url = f"{BASE_URL}/rwas/list"
    params = {}
    if asset_type:
        # asset_type accepts "stock", "commodity", or "etf"
        params["asset_type"] = asset_type
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()

def get_rwa_markets(ids=None, asset_type=None, price_change_percentage="24h,7d"):
    url = f"{BASE_URL}/rwas/markets"
    params = {"price_change_percentage": price_change_percentage}
    if ids:
        params["ids"] = ",".join(ids) if isinstance(ids, list) else ids
    if asset_type:
        params["asset_type"] = asset_type
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    rwas = get_rwa_list()
    print(f"Total RWAs tracked: {len(rwas)}")

    # Screen a mix of tokenized stocks, a leveraged ETF, and a tokenized commodity
    sample = get_rwa_markets(ids=["amazon", "adobe", "2x-bitcoin-strategy-etf", "gold"])
    for m in sample:
        data = m["tokenized_market_data"]
        print(m["id"], m["asset_type"], data["current_price"], data["market_cap"])
