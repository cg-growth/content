"""
CoinGecko X402 - Simple Price Test (Production)
===============================================

This script tests the Simple Price endpoint, which retrieves
prices and market data for coins listed on CoinGecko.com.

Example: Get BTC, ETH, SOL prices in USD

Cost: $0.01 USDC per request

Usage:
    python examples/test_simple_price.py
"""

import asyncio

from x402.http.clients import x402HttpxClient

from main import build_url, create_x402_client, fetch_json


async def main():
    client, http_helper, network, wallet = create_x402_client()

    print("=" * 60)
    print("🔄 CoinGecko X402 - Simple Price Test")
    print("=" * 60)
    print(f"Network: {network}")
    print(f"Wallet: {wallet}")
    print("Tokens: BTC, ETH, SOL")
    print("Currency: USD")
    print("Cost: $0.01 USDC")
    print("=" * 60)

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
