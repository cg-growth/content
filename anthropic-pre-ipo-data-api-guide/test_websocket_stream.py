"""
Test: stream live price updates for Anthropic's tokenized PreStocks token
via CoinGecko's WebSocket API (requires Basic Plan and above).

Requires: pip install websockets
Run: export COINGECKO_PRO_API_KEY=... (sourced from your key file, not typed)
     python3 test_websocket_stream.py
Stop with Ctrl+C.
"""

import asyncio
import json
import os

import websockets

API_KEY = os.environ["COINGECKO_PRO_API_KEY"]
WS_URL = f"wss://stream.coingecko.com/v1?x_cg_pro_api_key={API_KEY}"
TOKEN = "solana:Pren1FvFX6J3E4kXhJuCiAD5aDmGEb7qJRncwA8Lkhw"


async def main():
    async with websockets.connect(WS_URL) as ws:
        # Subscribe to the live price channel
        await ws.send(json.dumps({
            "command": "subscribe",
            "identifier": json.dumps({"channel": "OnchainSimpleTokenPrice"}),
        }))
        print("Subscribe response:", await ws.recv())

        # Tell it which token to watch
        await ws.send(json.dumps({
            "command": "message",
            "identifier": json.dumps({"channel": "OnchainSimpleTokenPrice"}),
            "data": json.dumps({
                "network_id:token_addresses": [TOKEN],
                "action": "set_tokens",
            }),
        }))

        print("Listening for price ticks (Ctrl+C to stop)...\n")
        async for message in ws:
            data = json.loads(message)
            if data.get("c") == "G1":  # skip periodic {"type":"ping",...} keepalives
                print(message)


if __name__ == "__main__":
    asyncio.run(main())
