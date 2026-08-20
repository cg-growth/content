import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("COINGECKO_API_KEY", "")
PLAN = os.getenv("COINGECKO_PLAN", "demo")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

if PLAN in ("analyst", "pro"):
    BASE_URL = "https://pro-api.coingecko.com/api/v3"
    HEADERS = {"x-cg-pro-api-key": API_KEY}
else:
    BASE_URL = "https://api.coingecko.com/api/v3"
    HEADERS = {"x-cg-demo-api-key": API_KEY}

# Fix these before testing so you are not tuning against results
# you have already seen.
MIN_SENTIMENT_SCORE = 0.35
MIN_CONFIDENCE = 0.60

# Universe filters.
MIN_MARKET_CAP_USD = 100_000_000
MIN_VOLUME_USD = 5_000_000

STARTING_CASH_USD = 10_000.0
POSITION_PCT = 0.05          # 5% of equity per trade
COOLDOWN_HOURS = 6           # per coin, prevents stacking one news cycle
FEE_PCT = 0.001              # 0.1% per side
SLIPPAGE_PCT = 0.002         # 0.2% assumed adverse fill
