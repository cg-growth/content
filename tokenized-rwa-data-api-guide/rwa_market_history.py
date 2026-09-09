import requests
from config import BASE_URL, HEADERS

def get_market_chart(rwa_id, days=30):
    url = f"{BASE_URL}/rwas/{rwa_id}/market_chart"
    params = {"days": days}
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    chart = get_market_chart("openai-pre-ipo", days=30)
    print(f"\n{len(chart['tokenized_prices'])} price points over the last 30 days")
    print("First point:", chart["tokenized_prices"][0])
    print("Last point:", chart["tokenized_prices"][-1])
