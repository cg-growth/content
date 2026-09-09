import requests
from config import BASE_URL, HEADERS

def get_pre_ipo_stocks():
    url = f"{BASE_URL}/coins/markets"
    params = {
        "vs_currency": "usd",
        "category": "tokenized-pre-ipo-stocks",
        "order": "market_cap_desc",
        "per_page": 20,
        "page": 1,
    }
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()

def get_rwa_by_id(rwa_id):
    url = f"{BASE_URL}/rwas/{rwa_id}"
    params = {"tokens": "true", "tokenized_market_data": "true"}
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    coins = get_pre_ipo_stocks()
    print(f"Tokenized pre-IPO stocks live: {len(coins)}")
    for c in coins:
        print(c["id"], c["symbol"], c["name"], c["market_cap"])

    openai = get_rwa_by_id("openai-pre-ipo")
    print(f"\n{openai['name']} aggregate price: {openai['tokenized_market_data']['current_price']}")
    for t in openai["tokens"]:
        print(" -", t["name"], "issued by", t["issuer_details"]["name"])
