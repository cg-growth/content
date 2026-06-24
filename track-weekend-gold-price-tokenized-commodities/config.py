import os
from dotenv import load_dotenv

load_dotenv()

USE_PRO_API = os.getenv("USE_PRO_API", "false").lower() == "true"
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "").strip()

if USE_PRO_API:
    BASE_URL = "https://pro-api.coingecko.com/api/v3"
    API_HEADER_KEY = "x-cg-pro-api-key"
else:
    BASE_URL = "https://api.coingecko.com/api/v3"
    API_HEADER_KEY = "x-cg-demo-api-key"

REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))
USER_AGENT = "coingecko-tokenized-commodities-python/1.0"


def get_headers() -> dict:
    if not COINGECKO_API_KEY:
        raise ValueError("COINGECKO_API_KEY is not set. Copy .env.example to .env and configure it.")

    return {
        "accept": "application/json",
        "user-agent": USER_AGENT,
        API_HEADER_KEY: COINGECKO_API_KEY,
    }


def get_runtime_config() -> dict:
    return {
        "use_pro_api": USE_PRO_API,
        "base_url": BASE_URL,
        "api_header_key": API_HEADER_KEY,
        "request_timeout": REQUEST_TIMEOUT,
        "max_retries": MAX_RETRIES,
    }
