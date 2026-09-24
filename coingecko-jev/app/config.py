import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
DATA_DIR = ROOT / "data"
FIXTURES_DIR = ROOT / "fixtures"

CG_PRO_KEY = os.environ.get("COINGECKO_PRO_API_KEY", "")
CG_DEMO_KEY = os.environ.get("COINGECKO_DEMO_API_KEY", "")
CG_API_MODE = os.environ.get("CG_API_MODE", "pro").strip().lower()

if CG_API_MODE == "demo":
    CG_BASE = "https://api.coingecko.com/api/v3"
    CG_KEY = CG_DEMO_KEY
    CG_KEY_HEADER = "x-cg-demo-api-key"
else:
    CG_BASE = "https://pro-api.coingecko.com/api/v3"
    CG_KEY = CG_PRO_KEY
    CG_KEY_HEADER = "x-cg-pro-api-key"

CG_WS_URL = "wss://stream.coingecko.com/v1?x_cg_pro_api_key={key}"

EVM_TIERS = ["top_10", "11_30", "31_50", "rest"]
CHAINS = {
    "solana": {"label": "Solana", "holder_tiers": ["top_10", "11_20", "21_40", "rest"]},
    "base": {"label": "Base", "holder_tiers": EVM_TIERS},
    "bsc": {"label": "BNB Chain", "holder_tiers": EVM_TIERS},
    "eth": {"label": "Ethereum", "holder_tiers": EVM_TIERS},
    "robinhood": {"label": "Robinhood Chain", "holder_tiers": EVM_TIERS},
}

WALLET_CHAINS = {
    "eth": "Ethereum", "base": "Base", "bsc": "BNB Chain", "polygon_pos": "Polygon", "arbitrum": "Arbitrum",
    "optimism": "Optimism", "avax": "Avalanche", "stable": "Stable", "robinhood": "Robinhood Chain",
    "solana": "Solana",
}

# Not every wallet endpoint has the same chain coverage. Configure that per chain here; the UI
# hides a tab rather than guessing or showing broken/empty data for a chain that isn't supported.
WALLET_CHAIN_CAPS = {
    "solana": {"trades": True, "pnl": True, "balances": False, "transfers": False},
}
_DEFAULT_WALLET_CAPS = {"trades": True, "pnl": True, "balances": True, "transfers": True}


def wallet_caps(chain: str) -> dict:
    return WALLET_CHAIN_CAPS.get(chain, _DEFAULT_WALLET_CAPS)


# Base58, no 0/O/I/l (Solana addresses); EVM chains use 0x + 40 hex.
WALLET_ADDR_PATTERNS = {"solana": r"^[1-9A-HJ-NP-Za-km-z]{32,44}$"}
DEFAULT_WALLET_ADDR_PATTERN = r"^0x[0-9a-fA-F]{40}$"

XRAY_CONCURRENCY = 12
XRAY_WALLET_CAP = 60
WALLET_CACHE_TTL_S = 30 * 60
PULSE_WALLET_POLL_S = 30
PULSE_WALLET_MIN_USD = 250
PULSE_WALLET_NEW_PER_CYCLE = 12

HOST = "127.0.0.1"
PORT = int(os.environ.get("JEV_DEMO_PORT", "8787"))

CG_CONCURRENCY = 10
JEV_CONCURRENCY = 20

INFO_TTL_S = 600
TRENDING_TTL_S = 30
MARKET_CHART_TTL_S = 6 * 3600
NEWS_TTL_S = 300
STABLE_TTL_S = 24 * 3600

PULSE_MIN_INTERVAL_MS = int(os.environ.get("PULSE_MIN_INTERVAL_MS", "1000"))
PULSE_WATCH_INTERVAL_MS = 2000
PULSE_MAX_POOLS = 4
PULSE_IDLE_STOP_S = int(os.environ.get("PULSE_IDLE_STOP_S", str(20 * 60)))
PULSE_TRADES_POLL_S = 15
PULSE_LIQ_POLL_S = 60
PULSE_EMA_ALPHA = 0.4

JEV_PRICE_PER_MTOK = 0.042
