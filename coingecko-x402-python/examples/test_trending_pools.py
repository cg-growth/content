"""
CoinGecko X402 - Trending Pools Test (Production)
=================================================

This script tests the Trending Pools endpoint, which retrieves
latest trending pools & tokens based on a network.

Example: Get trending pools on Base network (last 5 minutes)

Cost: $0.01 USDC per request

Usage:
    python examples/test_trending_pools.py
"""

import asyncio

from x402.http.clients import x402HttpxClient

from main import build_url, create_x402_client, fetch_json


async def main():
    client, http_helper, network, wallet = create_x402_client()

    print("=" * 60)
    print("🔄 CoinGecko X402 - Trending Pools Test")
    print("=" * 60)
    print(f"Network: {network}")
    print(f"Wallet: {wallet}")
    print("Query: Trending pools on Base (5min)")
    print("Cost: $0.01 USDC")
    print("=" * 60)

    endpoint = "onchain/networks/base/trending_pools"
    params = {
        "page": "1",
        "duration": "5m",
        "include": "base_token,quote_token,dex",
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
