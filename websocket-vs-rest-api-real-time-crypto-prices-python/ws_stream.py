"""Stream real-time crypto prices from the CoinGecko WebSocket API."""

import asyncio
import json
import os
from datetime import datetime, timezone

import websockets

API_KEY = os.environ.get("COINGECKO_API_KEY", "")
STREAM_URL = f"wss://stream.coingecko.com/v1?x_cg_pro_api_key={API_KEY}"

COINS = ["bitcoin", "ethereum", "solana"]
VS_CURRENCIES = ["usd"]

# The identifier is a JSON string nested inside the JSON message, not an object.
CHANNEL = json.dumps({"channel": "CGSimplePrice"})

# CGSimplePrice payloads use abbreviated keys.
FIELDS = {
    "i": "coin_id",
    "vs": "vs_currency",
    "p": "price",
    "pp": "price_24h_change_percentage",
    "t": "last_updated_at",
}


def format_update(payload):
    """Turn an abbreviated payload into a readable line."""
    coin_id = payload.get("i", "unknown")
    price = payload.get("p")
    change = payload.get("pp")
    received_at = datetime.now(timezone.utc).strftime("%H:%M:%S")

    # Any field can be null when data is unavailable.
    price_text = f"${price:>12,.2f}" if price is not None else f"{'no price':>13}"
    change_text = f"{change:+6.2f}%" if change is not None else "     -"

    return f"[{received_at}] {coin_id:<10} {price_text}  {change_text} 24h"


async def stream_prices():
    async with websockets.connect(STREAM_URL) as socket:
        # 1. The server greets us before we subscribe to anything.
        print(await socket.recv())
        print(await socket.recv())

        # 2. Subscribe to the channel.
        await socket.send(json.dumps({"command": "subscribe", "identifier": CHANNEL}))
        print(await socket.recv())

        # 3. Tell the channel which coins to stream.
        await socket.send(
            json.dumps(
                {
                    "command": "message",
                    "identifier": CHANNEL,
                    "data": json.dumps(
                        {
                            "coin_id": COINS,
                            "vs_currencies": VS_CURRENCIES,
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
    asyncio.run(stream_prices())
