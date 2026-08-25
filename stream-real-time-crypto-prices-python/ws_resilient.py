import asyncio
import json
import os
import random
import time
from datetime import datetime, timezone

import websockets

API_KEY = os.environ.get("COINGECKO_API_KEY", "")
STREAM_URL = f"wss://stream.coingecko.com/v1?x_cg_pro_api_key={API_KEY}"

COINS = ["bitcoin", "ethereum", "solana"]
CHANNEL = json.dumps({"channel": "CGSimplePrice"})

BASE_DELAY = 1  # seconds
MAX_DELAY = 60  # cap, so backoff never grows unbounded
STABLE_AFTER = 30  # a connection lasting this long counts as healthy


def log(message):
    stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{stamp}] {message}")


async def subscribe(socket):
    """Re-establish the subscription. A new connection has none."""
    await socket.send(json.dumps({"command": "subscribe", "identifier": CHANNEL}))
    await socket.send(
        json.dumps(
            {
                "command": "message",
                "identifier": CHANNEL,
                "data": json.dumps(
                    {
                        "coin_id": COINS,
                        "vs_currencies": ["usd"],
                        "action": "set_tokens",
                    }
                ),
            }
        )
    )


async def consume(socket):
    """Print updates until the server stops sending them."""
    async for raw_message in socket:
        message = json.loads(raw_message)

        if message.get("type") == "ping":
            continue  # informational heartbeat; safe to ignore
        if message.get("c") == "C1":
            price = message.get("p")
            price_text = f"${price:,.2f}" if price is not None else "no price"
            log(f"{message.get('i', 'unknown'):<10} {price_text}")
        elif message.get("message"):
            log(f"server: {message['message']}")


async def stream_with_reconnect():
    attempt = 0

    while True:
        connected_at = time.monotonic()

        try:
            # websockets answers the server's pings automatically, so there is
            # no heartbeat code to write here.
            async with websockets.connect(STREAM_URL) as socket:
                log("connected")
                await subscribe(socket)
                await consume(socket)

            # Reaching here means the server closed the connection cleanly.
            # That is not an exception, so it must be handled explicitly -
            # otherwise the loop reconnects instantly and spins.
            reason = "closed by server"

        except (websockets.exceptions.WebSocketException, OSError) as error:
            reason = type(error).__name__

        uptime = time.monotonic() - connected_at

        # Only treat the connection as healthy if it actually stayed up.
        # A socket that closes immediately every time is still failing.
        attempt = 1 if uptime >= STABLE_AFTER else attempt + 1

        delay = min(BASE_DELAY * 2 ** (attempt - 1), MAX_DELAY)
        delay += random.uniform(0, delay * 0.1)  # jitter

        log(f"disconnected after {uptime:.1f}s ({reason}) - retry {attempt} in {delay:.1f}s")
        await asyncio.sleep(delay)


if __name__ == "__main__":
    try:
        asyncio.run(stream_with_reconnect())
    except KeyboardInterrupt:
        log("stopped")
