"""
CoinGecko X402 - Token Data Test (Production)
=============================================

This script tests the Token Data endpoint, which retrieves
price, liquidity, and market data of a token.

Example: Get USDT data on Ethereum

Cost: $0.01 USDC per request

Usage:
    python examples/test_token_data.py
"""

import asyncio

from x402.http.clients import x402HttpxClient

from main import build_url, create_x402_client, fetch_json


async def main():
    client, http_helper, network, wallet = create_x402_client()

    print("=" * 60)
    print("🔄 CoinGecko X402 - Token Data Test")
    print("=" * 60)
    print(f"Network: {network}")
    print(f"Wallet: {wallet}")
    print("Token: USDT on Ethereum")
    print("Cost: $0.01 USDC")
    print("=" * 60)

    endpoint = "onchain/networks/eth/tokens/0xdac17f958d2ee523a2206206994597c13d831ec7"
    params = {
        "include": "top_pools",
        "include_composition": "true",
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
