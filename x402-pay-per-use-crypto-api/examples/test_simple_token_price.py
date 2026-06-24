"""
CoinGecko X402 - Simple Token Price Test (Production)
=====================================================

This script tests the Simple Token Price endpoint, which retrieves
price and market data based on token contract addresses.

Example: Get WETH price on Ethereum

Cost: $0.01 USDC per request

Usage:
    python examples/test_simple_token_price.py
"""

import asyncio

from x402.http.clients import x402HttpxClient

from main import build_url, create_x402_client, fetch_json


async def main():
    client, http_helper, network, wallet = create_x402_client()

    print("=" * 60)
    print("🔄 CoinGecko X402 - Simple Token Price Test")
    print("=" * 60)
    print(f"Network: {network}")
    print(f"Wallet: {wallet}")
    print("Token: WETH on Ethereum")
    print("Cost: $0.01 USDC")
    print("=" * 60)

    endpoint = "onchain/simple/networks/eth/token_price/0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
    params = {
        "include_market_cap": "true",
        "include_24hr_vol": "true",
        "include_24hr_price_change": "true",
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
