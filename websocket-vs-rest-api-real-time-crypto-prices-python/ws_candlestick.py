import asyncio
import json
import os
from collections import deque
from datetime import datetime, timezone

import websockets

API_KEY = os.environ.get("COINGECKO_API_KEY", "")  # a Basic-plan (paid) key
STREAM_URL = f"wss://stream.coingecko.com/v1?x_cg_pro_api_key={API_KEY}"

NETWORK = "eth"
POOL_ADDRESS = "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"  # WETH/USDC
INTERVAL = "1m"
CHANNEL = json.dumps({"channel": "OnchainOHLCV"})

MAX_CANDLES = 60
candles = deque(maxlen=MAX_CANDLES)  # ring buffer feeding the chart


def render(candle):
    """Print one candle as a colored line; swap this for a real chart library."""
    color = "up" if candle["c"] >= candle["o"] else "down"
    candle_time = datetime.fromtimestamp(candle["t"], tz=timezone.utc).strftime("%H:%M:%S")
    print(
        f"[{color}] {candle_time} O:{candle['o']:.4f} H:{candle['h']:.4f} "
        f"L:{candle['l']:.4f} C:{candle['c']:.4f} V:{candle['v']:.2f}"
    )


async def stream_candles():
    async with websockets.connect(STREAM_URL) as socket:
        # 1. The server greets us before we subscribe to anything.
        print(await socket.recv())
        print(await socket.recv())

        # 2. Subscribe to the channel.
        await socket.send(json.dumps({"command": "subscribe", "identifier": CHANNEL}))
        print(await socket.recv())

        # 3. Tell the channel which pool to stream.
        await socket.send(
            json.dumps(
                {
                    "command": "message",
                    "identifier": CHANNEL,
                    "data": json.dumps(
                        {
                            "network_id:pool_addresses": [f"{NETWORK}:{POOL_ADDRESS}"],
                            "interval": INTERVAL,
                            "token": "base",
                            "action": "set_pools",
                        }
                    ),
                }
            )
        )

        # 4. Read candle updates as the server pushes them.
        async for raw_message in socket:
            message = json.loads(raw_message)

            if message.get("ch") != "G3":
                continue
            # Replace the in-progress candle, or start a new one when the timestamp changes.
            if candles and candles[-1]["t"] == message["t"]:
                candles[-1] = message
            else:
                candles.append(message)
            render(message)


if __name__ == "__main__":
    asyncio.run(stream_candles())
