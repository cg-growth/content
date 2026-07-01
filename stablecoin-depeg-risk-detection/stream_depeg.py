import asyncio, json, os, websockets
from datetime import datetime

import requests

CHANNEL = json.dumps({"channel": "CGSimplePrice"})


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def get_watchlist():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": "usd", "category": "stablecoins",
              "order": "market_cap_desc", "per_page": 250, "page": 1}
    return [c["id"] for c in requests.get(url, params=params, timeout=10).json()]


async def stream_prices(api_key, watchlist):
    url = f"wss://stream.coingecko.com/v1?x_cg_pro_api_key={api_key}"
    async with websockets.connect(url) as ws:
        log(f"Connected. Subscribing to {len(watchlist)} stablecoins on CGSimplePrice...")
        await ws.send(json.dumps({"command": "subscribe", "identifier": CHANNEL}))
        await ws.send(json.dumps({
            "command": "message", "identifier": CHANNEL,
            "data": json.dumps({"coin_id": watchlist, "vs_currencies": ["usd"], "action": "set_tokens"}),
        }))
        async for msg in ws:
            u = json.loads(msg)
            # Streaming payloads use compact keys, c=channel_type, i=coin_id, p=price
            if u.get("c") == "C1" and u.get("p"):
                dev = abs(u["p"] - 1.0)
                if dev > 0.005:
                    log(f"  DEPEG  {u['i']:<28} ${u['p']:.4f}  ({dev*100:.2f}% off peg)")


if __name__ == "__main__":
    API_KEY = os.environ["COINGECKO_PRO_API_KEY"]
    asyncio.run(stream_prices(API_KEY, get_watchlist()))
