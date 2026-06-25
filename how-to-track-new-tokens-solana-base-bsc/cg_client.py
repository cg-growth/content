import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("COINGECKO_API_KEY")
MODE = os.getenv("CG_API_MODE", "demo")

# Demo and Pro use different base URLs and header names. Pick one and stick to it.
if MODE == "pro":
    BASE_URL = "https://pro-api.coingecko.com/api/v3"
    HEADERS = {"x-cg-pro-api-key": API_KEY}
else:
    BASE_URL = "https://api.coingecko.com/api/v3"
    HEADERS = {"x-cg-demo-api-key": API_KEY}


def get(path, params=None):
    """Call any onchain endpoint on the CoinGecko API."""
    response = requests.get(f"{BASE_URL}{path}", headers=HEADERS, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def index_included(payload):
    """Index sideloaded entities (tokens, networks, dexes) by ID."""
    return {item["id"]: item for item in payload.get("included", [])}
