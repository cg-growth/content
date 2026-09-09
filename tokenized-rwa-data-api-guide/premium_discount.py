import requests
from config import BASE_URL, HEADERS

def get_implied_spot_price(commodity_code):
    # commodity_code is "xau" for gold or "xag" for silver
    url = f"{BASE_URL}/exchange_rates"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    rates = response.json()["rates"]
    # Both rates are quoted against BTC, so dividing USD by the commodity
    # rate gives you the implied USD spot price for one troy ounce
    return rates["usd"]["value"] / rates[commodity_code]["value"]

def get_tokenized_price(rwa_id):
    url = f"{BASE_URL}/rwas/{rwa_id}"
    params = {"tokenized_market_data": "true"}
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()["tokenized_market_data"]["current_price"]

if __name__ == "__main__":
    for rwa_id, code in [("gold", "xau"), ("silver", "xag")]:
        tokenized = get_tokenized_price(rwa_id)
        spot = get_implied_spot_price(code)
        premium = (tokenized - spot) / spot * 100
        label = "premium" if premium >= 0 else "discount"
        print(f"{rwa_id}: tokenized ${tokenized:,.2f} vs implied spot ${spot:,.2f}, a {abs(premium):.2f}% {label}")
