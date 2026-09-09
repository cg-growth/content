import requests
from config import BASE_URL, HEADERS

def get_rwa_tickers(rwa_id, order="volume_desc", depth=False):
    url = f"{BASE_URL}/rwas/{rwa_id}/tickers"
    params = {"order": order, "depth": str(depth).lower()}
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    tickers = get_rwa_tickers("openai-pre-ipo", depth=True)
    for t in tickers["tickers"][:5]:
        spread = t["bid_ask_spread_percentage"]
        print(f"{t['market']['name']}: {t['converted_last']['usd']} USD, spread {spread}%, volume {t['converted_volume']['usd']}")
