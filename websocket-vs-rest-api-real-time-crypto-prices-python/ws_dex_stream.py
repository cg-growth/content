"""Stream real-time onchain DEX token prices from the CoinGecko WebSocket API."""

import asyncio
import json
import os
from datetime import datetime, timezone

import websockets

API_KEY = os.environ.get("COINGECKO_API_KEY", "")
STREAM_URL = f"wss://stream.coingecko.com/v1?x_cg_pro_api_key={API_KEY}"

NETWORK = "eth"
TOKEN_ADDRESSES = {
    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": "WETH",
    "0x6982508145454ce325ddbe47a25d4ec3d2311933": "PEPE",
    "0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce": "SHIB",
    "0x514910771af9ca656af840dff83e8264ecf986ca": "LINK",
}

CHANNEL = json.dumps({"channel": "OnchainSimpleTokenPrice"})


def format_update(payload):
    """Turn an abbreviated payload into a readable line."""
    address = payload.get("ta", "unknown")
    symbol = TOKEN_ADDRESSES.get(address, address)
    price = payload.get("p")
    change = payload.get("pp")
    received_at = datetime.now(timezone.utc).strftime("%H:%M:%S")

    # Any field can be null when data is unavailable.
    price_text = f"${price:>12,.6f}" if price is not None else f"{'no price':>13}"
    change_text = f"{change:+6.2f}%" if change is not None else "     -"

    return f"[{received_at}] {symbol:<10} {price_text}  {change_text} 24h"


async def stream_dex_prices():
    async with websockets.connect(STREAM_URL) as socket:
        # 1. The server greets us before we subscribe to anything.
        print(await socket.recv())
        print(await socket.recv())

        # 2. Subscribe to the channel.
        await socket.send(json.dumps({"command": "subscribe", "identifier": CHANNEL}))
        print(await socket.recv())

        # 3. Tell the channel which tokens to stream.
        await socket.send(
            json.dumps(
                {
                    "command": "message",
                    "identifier": CHANNEL,
                    "data": json.dumps(
                        {
                            "network_id:token_addresses": [
                                f"{NETWORK}:{address}" for address in TOKEN_ADDRESSES
                            ],
                            "action": "set_tokens",
                        }
                    ),
                }
            )
        )

        # 4. Read updates as the server pushes them.
        async for raw_message in socket:
            message = json.loads(raw_message)

            if message.get("type") == "ping":
                continue  # informational heartbeat; safe to ignore
            if message.get("c") == "C1":
                print(format_update(message))
            elif "message" in message:
                print(f"[server] {message['message']}")


if __name__ == "__main__":
    asyncio.run(stream_dex_prices())
