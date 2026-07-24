import json
import websocket
from config import API_KEY

NETWORK_ID = "solana"
POOL_ADDRESS = "8aDaBQkTrS6HVMjyc6EZebgdiaXhLYGriDWKWWp1NpFF"  # Tesla xStock / USDC
COIN_ID = "tesla-xstock"

def on_open(ws):
    # Subscribe to all three channels, then tell each one what to watch
    for channel in ("CGSimplePrice", "OnchainOHLCV", "OnchainTrade"):
        ws.send(json.dumps({"command": "subscribe", "identifier": json.dumps({"channel": channel})}))

    ws.send(json.dumps({
        "command": "message",
        "identifier": json.dumps({"channel": "CGSimplePrice"}),
        "data": json.dumps({"coin_id": [COIN_ID], "vs_currencies": ["usd"], "action": "set_tokens"}),
    }))
    ws.send(json.dumps({
        "command": "message",
        "identifier": json.dumps({"channel": "OnchainOHLCV"}),
        "data": json.dumps({
            "network_id:pool_addresses": [f"{NETWORK_ID}:{POOL_ADDRESS}"],
            "interval": "1m",
            "token": "base",
            "action": "set_pools",
        }),
    }))
    ws.send(json.dumps({
        "command": "message",
        "identifier": json.dumps({"channel": "OnchainTrade"}),
        "data": json.dumps({
            "network_id:pool_addresses": [f"{NETWORK_ID}:{POOL_ADDRESS}"],
            "action": "set_pools",
        }),
    }))

def on_message(ws, message):
    data = json.loads(message)
    # OnchainTrade payloads carry "ty" (b/s); OnchainOHLCV uses "ch" for channel type
    # (not "c"); CGSimplePrice uses "c":"C1". Checking in this order avoids key collisions.
    if "ty" in data:
        side = "BUY" if data["ty"] == "b" else "SELL"
        print(f"[TRADE] {side} {data['vo']:.2f} USD at ${data['pu']:.2f}  tx={data['tx'][:10]}...")
    elif "ch" in data:
        print(f"[OHLCV] {data['i']} candle  O:{data['o']:.2f} H:{data['h']:.2f} L:{data['l']:.2f} C:{data['c']:.2f}")
    elif data.get("c") == "C1":
        print(f"[PRICE] {data['i']} ${data['p']:.2f}  {data['pp']:+.2f}% 24h")
    else:
        print("Status:", data.get("message", data))

if __name__ == "__main__":
    url = f"wss://stream.coingecko.com/v1?x_cg_pro_api_key={API_KEY}"
    ws = websocket.WebSocketApp(url, on_open=on_open, on_message=on_message)
    ws.run_forever()
