import requests
from config import BASE_URL, HEADERS

def fetch_latest_news(per_page=10, coin_id=None):
    """Fetch the most recent crypto news articles."""
    params = {"per_page": per_page, "page": 1}

    if coin_id:
        params["coin_id"] = coin_id

    response = requests.get(f"{BASE_URL}/news", headers=HEADERS, params=params)
    response.raise_for_status()

    # SDK equivalent: client.news.get(per_page=10)
    # The endpoint returns a bare JSON array, not an object with a data key
    return response.json()

if __name__ == "__main__":
    for article in fetch_latest_news(per_page=5):
        print(f"[{article['posted_at']}] {article['source_name']}")
        print(f"  {article['title']}")
        print(f"  coins: {article['related_coin_ids']}\n")
