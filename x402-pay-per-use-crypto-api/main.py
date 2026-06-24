"""
CoinGecko X402 API Test Script (Production)
===========================================

Production-ready script for interacting with CoinGecko's X402 endpoints.
Includes a minimal fallback for services that return V2 payment requirements
in the JSON body instead of the PAYMENT-REQUIRED header.
"""

import asyncio
import json
import os
import sys
from typing import Optional
from urllib.parse import urlencode

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Try to import x402 packages
try:
    from x402 import x402Client
    from x402.http import x402HTTPClient
    from x402.http.clients import x402HttpxClient
    from x402.schemas import PaymentRequired
except ImportError as e:
    print("=" * 60)
    print("ERROR: Missing required x402 packages!")
    print("=" * 60)
    print(f"\nImport error: {e}")
    print("\nPlease install the required packages:")
    print("  pip install -r requirements.txt")
    print("=" * 60)
    sys.exit(1)

# Try to import EVM packages
EVM_AVAILABLE = False
EVM_IMPORT_ERROR = None
try:
    from eth_account import Account
    from x402.mechanisms.evm import EthAccountSigner
    from x402.mechanisms.evm.exact.register import register_exact_evm_client
    EVM_AVAILABLE = True
except ImportError as e:
    EVM_IMPORT_ERROR = str(e)

# Try to import Solana packages
SOLANA_AVAILABLE = False
SOLANA_IMPORT_ERROR = None
try:
    from x402.mechanisms.svm import KeypairSigner
    from x402.mechanisms.svm.exact.register import register_exact_svm_client
    SOLANA_AVAILABLE = True
except ImportError as e:
    SOLANA_IMPORT_ERROR = str(e)


# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_URL = "https://pro-api.coingecko.com/api/v3/x402"

PLACEHOLDER_PATTERNS = [
    "your_evm_private_key_here",
    "your_solana_private_key_here",
    "your_private_key",
    "placeholder",
    "example",
    "xxx",
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def is_placeholder_key(key: str) -> bool:
    """Check if a private key looks like a placeholder value."""
    if not key:
        return True
    key_lower = key.lower()
    for pattern in PLACEHOLDER_PATTERNS:
        if pattern in key_lower:
            return True
    if "_" in key:
        return True
    if len(key.replace("0x", "")) < 32:
        return True
    return False


def get_network_config() -> tuple:
    """
    Determine which network to use based on available private keys.

    Returns:
        tuple: (network_name, private_key, signer_setup_function)
    """
    evm_key = os.getenv("EVM_PRIVATE_KEY")
    solana_key = os.getenv("SOLANA_PRIVATE_KEY")
    network_preference = os.getenv("NETWORK", "auto").lower()

    if network_preference == "evm" or network_preference == "base":
        if not evm_key:
            print("❌ Error: NETWORK=evm specified but EVM_PRIVATE_KEY not found")
            sys.exit(1)
        if is_placeholder_key(evm_key):
            print("❌ Error: EVM_PRIVATE_KEY contains a placeholder value")
            print("   Please replace it with your actual private key in .env")
            sys.exit(1)
        if not EVM_AVAILABLE:
            print("❌ Error: EVM packages not available")
            print(f"   Import error: {EVM_IMPORT_ERROR}")
            print("   Fix: pip install \"x402[evm,httpx]>=0.1.0\"")
            sys.exit(1)
        return ("evm", evm_key, setup_evm_client)

    if network_preference == "solana" or network_preference == "svm":
        if not solana_key:
            print("❌ Error: NETWORK=solana specified but SOLANA_PRIVATE_KEY not found")
            sys.exit(1)
        if is_placeholder_key(solana_key):
            print("❌ Error: SOLANA_PRIVATE_KEY contains a placeholder value")
            print("   Please replace it with your actual private key in .env")
            sys.exit(1)
        if not SOLANA_AVAILABLE:
            print("❌ Error: Solana packages not available")
            print(f"   Import error: {SOLANA_IMPORT_ERROR}")
            print("   Fix: pip install 'x402[svm]'")
            sys.exit(1)
        return ("solana", solana_key, setup_solana_client)

    if evm_key and not is_placeholder_key(evm_key) and EVM_AVAILABLE:
        return ("evm", evm_key, setup_evm_client)
    if solana_key and not is_placeholder_key(solana_key) and SOLANA_AVAILABLE:
        return ("solana", solana_key, setup_solana_client)

    print("=" * 60)
    print("ERROR: No valid wallet private key found!")
    print("=" * 60)
    print("Please set one of the following in your .env file:")
    print("  EVM_PRIVATE_KEY=0xYourEVMPrivateKey     (for Base network)")
    print("  SOLANA_PRIVATE_KEY=YourBase58Key        (for Solana network)")
    print("=" * 60)
    sys.exit(1)


def setup_evm_client(client: x402Client, private_key: str) -> str:
    """Set up EVM (Base) network client and return wallet address."""
    if not private_key.startswith("0x"):
        private_key = f"0x{private_key}"
    account = Account.from_key(private_key)
    signer = EthAccountSigner(account)
    register_exact_evm_client(client, signer)
    return account.address


def setup_solana_client(client: x402Client, private_key: str) -> str:
    """Set up Solana network client and return wallet address."""
    signer = KeypairSigner.from_base58(private_key)
    register_exact_svm_client(client, signer)
    return signer.address


def print_response(endpoint_name: str, response_data: dict):
    """Pretty print the API response."""
    print("\n" + "=" * 60)
    print(f"✅ {endpoint_name}")
    print("=" * 60)
    print(json.dumps(response_data, indent=2))
    print("=" * 60 + "\n")


def print_error(endpoint_name: str, error: Exception):
    """Print error information."""
    print("\n" + "=" * 60)
    print(f"❌ {endpoint_name} - FAILED")
    print("=" * 60)
    print(f"Error: {error}")
    print("=" * 60 + "\n")


def build_url(endpoint: str, params: Optional[dict] = None) -> str:
    """Build the full URL with query parameters."""
    url = f"{BASE_URL}/{endpoint}"
    if params:
        query_string = urlencode(params, doseq=True)
        return f"{url}?{query_string}"
    return url


def safe_json(response) -> dict:
    """Safely parse JSON with a clear error message on failure."""
    try:
        return response.json()
    except Exception:
        raise ValueError("Response body is not valid JSON")


def create_x402_client() -> tuple:
    """
    Create and configure the x402 client with appropriate network support.

    Returns:
        tuple: (client, http_helper, network_name, wallet_address)
    """
    network_name, private_key, setup_func = get_network_config()

    client = x402Client()
    wallet_address = setup_func(client, private_key)
    http_helper = x402HTTPClient(client)

    network_display = "Base (EVM)" if network_name == "evm" else "Solana"
    print("✅ X402 client initialized")
    print(f"   Network: {network_display}")
    print(f"   Wallet address: {wallet_address}")

    return client, http_helper, network_name, wallet_address


async def manual_x402_request(
    client: x402Client,
    http_helper: x402HTTPClient,
    url: str,
) -> "httpx.Response":
    """Manual x402 payment flow for body-only V2 402 responses."""
    import httpx

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as raw:
        initial = await raw.get(url)
        await initial.aread()

        if initial.status_code != 402:
            return initial

        try:
            body = initial.json()
        except Exception:
            raise ValueError("402 response body is not valid JSON")

        if not isinstance(body, dict) or body.get("x402Version") != 2:
            raise ValueError("402 response missing x402Version=2 in body")

        payment_required = PaymentRequired.model_validate(body)

        payment_payload = await client.create_payment_payload(
            payment_required,
            resource=payment_required.resource,
            extensions=payment_required.extensions,
        )

        payment_headers = http_helper.encode_payment_signature_header(payment_payload)
        payment_headers["Access-Control-Expose-Headers"] = "PAYMENT-RESPONSE,X-PAYMENT-RESPONSE"

        retry = await raw.get(url, headers=payment_headers)
        await retry.aread()
        return retry


async def fetch_json(
    client: x402Client,
    http: x402HttpxClient,
    http_helper: x402HTTPClient,
    url: str,
) -> dict:
    """Perform a paid request and return JSON with a minimal fallback."""
    try:
        response = await http.get(url)
        await response.aread()

        if response.is_success:
            return safe_json(response)

        raise ValueError(f"Request failed with status {response.status_code}")
    except Exception as error:
        if "Invalid payment required response" in str(error):
            manual_response = await manual_x402_request(client, http_helper, url)
            if manual_response.is_success:
                return safe_json(manual_response)
            raise ValueError(f"Manual payment retry failed with status {manual_response.status_code}")
        raise


# =============================================================================
# API ENDPOINT TESTS
# =============================================================================

async def test_simple_token_price(
    client: x402Client,
    http: x402HttpxClient,
    http_helper: x402HTTPClient,
) -> dict:
    endpoint = "onchain/simple/networks/eth/token_price/0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
    params = {
        "include_market_cap": "true",
        "include_24hr_vol": "true",
        "include_24hr_price_change": "true",
    }

    url = build_url(endpoint, params)
    print("\n🔄 Testing: Simple Token Price")
    print(f"   URL: {url}")

    return await fetch_json(client, http, http_helper, url)


async def test_search_pools(
    client: x402Client,
    http: x402HttpxClient,
    http_helper: x402HTTPClient,
) -> dict:
    endpoint = "onchain/search/pools"
    params = {
        "query": "pump",
        "network": "solana",
        "include": "base_token,quote_token,dex",
        "page": "1",
    }

    url = build_url(endpoint, params)
    print("\n🔄 Testing: Search Pools")
    print(f"   URL: {url}")

    return await fetch_json(client, http, http_helper, url)


async def test_trending_pools(
    client: x402Client,
    http: x402HttpxClient,
    http_helper: x402HTTPClient,
) -> dict:
    endpoint = "onchain/networks/base/trending_pools"
    params = {
        "page": "1",
        "duration": "5m",
        "include": "base_token,quote_token,dex",
    }

    url = build_url(endpoint, params)
    print("\n🔄 Testing: Trending Pools")
    print(f"   URL: {url}")

    return await fetch_json(client, http, http_helper, url)


async def test_token_data(
    client: x402Client,
    http: x402HttpxClient,
    http_helper: x402HTTPClient,
) -> dict:
    endpoint = "onchain/networks/eth/tokens/0xdac17f958d2ee523a2206206994597c13d831ec7"
    params = {
        "include": "top_pools",
        "include_composition": "true",
    }

    url = build_url(endpoint, params)
    print("\n🔄 Testing: Token Data")
    print(f"   URL: {url}")

    return await fetch_json(client, http, http_helper, url)


async def test_simple_price(
    client: x402Client,
    http: x402HttpxClient,
    http_helper: x402HTTPClient,
) -> dict:
    endpoint = "simple/price"
    params = {
        "vs_currencies": "usd",
        "ids": "bitcoin,ethereum,solana",
        "include_market_cap": "true",
        "include_24hr_vol": "true",
        "include_24hr_change": "true",
        "include_last_updated_at": "true",
        "precision": "full",
    }

    url = build_url(endpoint, params)
    print("\n🔄 Testing: Simple Price")
    print(f"   URL: {url}")

    return await fetch_json(client, http, http_helper, url)


# =============================================================================
# MAIN EXECUTION
# =============================================================================

async def run_single_test(test_name: str):
    client, http_helper, network_name, wallet_address = create_x402_client()

    test_map = {
        "token_price": test_simple_token_price,
        "search_pools": test_search_pools,
        "trending_pools": test_trending_pools,
        "token_data": test_token_data,
        "simple_price": test_simple_price,
    }

    if test_name not in test_map:
        print(f"Unknown test: {test_name}")
        print(f"Available tests: {', '.join(test_map.keys())}")
        return

    async with x402HttpxClient(client) as http:
        try:
            result = await test_map[test_name](client, http, http_helper)
            print_response(test_name, result)
        except Exception as e:
            print_error(test_name, e)


async def run_all_tests():
    client, http_helper, network_name, wallet_address = create_x402_client()

    network_display = "Base (EVM)" if network_name == "evm" else "Solana"

    print("\n" + "=" * 60)
    print("🚀 CoinGecko X402 API Test Suite")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Network: {network_display}")
    print("Payment: $0.01 USDC per request")
    print("=" * 60)

    tests = [
        ("Simple Token Price (WETH on ETH)", test_simple_token_price),
        ("Search Pools (Solana)", test_search_pools),
        ("Trending Pools (Base)", test_trending_pools),
        ("Token Data (USDT on ETH)", test_token_data),
        ("Simple Price (BTC, ETH, SOL)", test_simple_price),
    ]

    results = {"passed": 0, "failed": 0}

    async with x402HttpxClient(client) as http:
        for name, test_func in tests:
            try:
                result = await test_func(client, http, http_helper)
                print_response(name, result)
                results["passed"] += 1
            except Exception as e:
                print_error(name, e)
                results["failed"] += 1

    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"   ✅ Passed: {results['passed']}")
    print(f"   ❌ Failed: {results['failed']}")
    print(f"   💰 Estimated cost: ${results['passed'] * 0.01:.2f} USDC")
    print("=" * 60)


def parse_args() -> Optional[str]:
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        if test_name in {"--help", "-h"}:
            print("Usage: python main.py [test_name]")
            print("\nAvailable tests:")
            print("  token_price    - Get WETH price on Ethereum")
            print("  search_pools   - Search pools on Solana")
            print("  trending_pools - Get trending pools on Base")
            print("  token_data     - Get USDT data on Ethereum")
            print("  simple_price   - Get BTC, ETH, SOL prices")
            print("\nRun without arguments to execute all tests.")
            return None
        return test_name
    return None


def main():
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║           CoinGecko X402 API Test Script                      ║
║                                                               ║
║   Test CoinGecko's X402-enabled endpoints with automatic      ║
║   crypto payments via the x402 protocol.                      ║
║                                                               ║
║   Supported Networks:                                         ║
║   • Base (EVM) - set EVM_PRIVATE_KEY                          ║
║   • Solana     - set SOLANA_PRIVATE_KEY                       ║
║                                                               ║
║   ⚠️  Each API call costs $0.01 USDC                          ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """)

    test_name = parse_args()
    if test_name:
        asyncio.run(run_single_test(test_name))
    else:
        asyncio.run(run_all_tests())


if __name__ == "__main__":
    main()
