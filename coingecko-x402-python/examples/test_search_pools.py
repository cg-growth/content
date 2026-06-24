"""
CoinGecko X402 - Search Pools Test (Production)
===============================================

This script tests the Search Pools endpoint, which searches
pools and tokens by contract address, name, or token symbol.

Example: Search for "pump" on Solana

Cost: $0.01 USDC per request

Usage:
    python examples/test_search_pools.py
"""

import asyncio

from x402.http.clients import x402HttpxClient

from main import build_url, create_x402_client, fetch_json


async def main():
    client, http_helper, network, wallet = create_x402_client()

    print("=" * 60)
    print("🔄 CoinGecko X402 - Search Pools Test")
    print("=" * 60)
    print(f"Network: {network}")
    print(f"Wallet: {wallet}")
    print("Search: 'pump' on Solana")
    print("Cost: $0.01 USDC")
    print("=" * 60)

    endpoint = "onchain/search/pools"
    params = {
        "query": "pump",
        "network": "solana",
        "include": "base_token,quote_token,dex",
        "page": "1",
    }
    url = build_url(endpoint, params)

    print(f"\n📡 Request URL:\n{url}\n")

    async with x402HttpxClient(client) as http:
        try:
            data = await fetch_json(client, http, http_helper, url)
            print("✅ SUCCESS!\n")
            print(data)
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
