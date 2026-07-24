import pandas as pd
import requests
from config import HEADERS, ONCHAIN_URL

def get_top_pool_address(network_id, token_address):
    url = f"{ONCHAIN_URL}/networks/{network_id}/tokens/{token_address}/pools"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    pools = response.json()["data"]
    return pools[0]["attributes"]["address"] if pools else None  # sorted by liquidity + 24h volume, so the first is the most liquid

# SDK equivalent: client.onchain.networks.tokens.pools.get(token_address, network=network_id)

def get_pool_ohlcv(network_id, pool_address, timeframe="day", limit=30):
    url = f"{ONCHAIN_URL}/networks/{network_id}/pools/{pool_address}/ohlcv/{timeframe}"
    response = requests.get(url, headers=HEADERS, params={"limit": limit})
    response.raise_for_status()
    return response.json()["data"]["attributes"]["ohlcv_list"]

# SDK equivalent: client.onchain.networks.pools.ohlcv.get_timeframe("day", network=network_id, pool_address=pool_address, limit=limit)

if __name__ == "__main__":
    # Tesla xStock on Solana; resolve its most liquid pool from the token's contract address
    network_id, token_address = "solana", "XsDoVfqeBukxuZHWhdvWHBhgEHjGNst4MLodqsJHzoB"

    pool_address = get_top_pool_address(network_id, token_address)

    candles = get_pool_ohlcv(network_id, pool_address, timeframe="day", limit=30)
    df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["timestamp"], unit="s")

    print(f"{'DATE':<12}{'OPEN':>10}{'HIGH':>10}{'LOW':>10}{'CLOSE':>10}{'VOLUME':>14}")
    print("-" * 66)
    for _, row in df.tail().iterrows():
        print(f"{row['date'].strftime('%Y-%m-%d'):<12}{row['open']:>10,.2f}{row['high']:>10,.2f}{row['low']:>10,.2f}{row['close']:>10,.2f}{row['volume']:>14,.2f}")
