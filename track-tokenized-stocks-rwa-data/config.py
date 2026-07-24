import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("COINGECKO_API_KEY", "")
# Switch to "pro" in your .env when you upgrade to a paid plan
PLAN = os.getenv("COINGECKO_PLAN", "demo").lower()

# Demo and paid plans use different base URLs and header names
if PLAN == "pro":
    BASE_URL = "https://pro-api.coingecko.com/api/v3"
    HEADERS = {"x-cg-pro-api-key": API_KEY}
else:
    BASE_URL = "https://api.coingecko.com/api/v3"
    HEADERS = {"x-cg-demo-api-key": API_KEY}

# Onchain (GeckoTerminal) endpoints live under the /onchain path on the same host
ONCHAIN_URL = f"{BASE_URL}/onchain"
