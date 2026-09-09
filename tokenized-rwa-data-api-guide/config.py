import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("COINGECKO_API_KEY")

# Use the Demo base URL if you have a free Demo key.
# Switch to the Pro base URL once you upgrade to a paid plan.
BASE_URL = "https://api.coingecko.com/api/v3"
# BASE_URL = "https://pro-api.coingecko.com/api/v3"

HEADERS = {
    "accept": "application/json",
    "x-cg-demo-api-key": API_KEY,
    # Swap the header above for "x-cg-pro-api-key" if you switch to the Pro base URL.
}
