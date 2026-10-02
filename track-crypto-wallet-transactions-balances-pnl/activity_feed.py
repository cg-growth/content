from wallet_client import get_balances, get_trades, get_transfers, get_pnl

WALLET = "0x9642b23ed1e01df1092b92641051881a322f5d4e"
NETWORK = "eth"
NETWORKS = "eth,base,arbitrum"

def fetch_all_trades(network, address):
    """Page through every trade using the cursor CoinGecko returns."""
    trades = []
    cursor = None
    while True:
        params = {"per_page": 100}
        if cursor:
            params["cursor"] = cursor
        payload = get_trades(network, address, **params)
        trades.extend(payload["data"])
        cursor = payload["meta"]["next_cursor"]
        if not cursor:
            break
    return trades

def fetch_all_transfers(network, address):
    """Page through every transfer using the cursor CoinGecko returns."""
    transfers = []
    cursor = None
    while True:
        params = {"per_page": 100}
        if cursor:
            params["cursor"] = cursor
        payload = get_transfers(network, address, **params)
        transfers.extend(payload["data"])
        cursor = payload["meta"]["next_cursor"]
        if not cursor:
            break
    return transfers

def build_activity_feed(trades, transfers):
    """Merge trades and transfers into one feed, labeled and sorted by time."""
    feed = []

    for trade in trades:
        attrs = trade["attributes"]
        feed.append({
            "type": "trade",
            "timestamp": attrs["block_timestamp"],
            "tx_hash": attrs["tx_hash"],
            "kind": attrs["kind"],
            "volume_usd": attrs["volume_in_usd"],
        })

    for transfer in transfers:
        attrs = transfer["attributes"]
        feed.append({
            "type": "transfer",
            "timestamp": attrs["block_timestamp"],
            "tx_hash": attrs["tx_hash"],
            "direction": attrs["direction"],
            "token": attrs["symbol"],
            "amount": attrs["amount"],
        })

    feed.sort(key=lambda entry: entry["timestamp"], reverse=True)
    return feed

if __name__ == "__main__":
    balances = get_balances(WALLET, NETWORKS)
    portfolio = balances["data"]["attributes"]
    print(f"Portfolio value: ${portfolio['total_value_usd']} across {len(portfolio['networks'])} networks\n")

    trades = fetch_all_trades(NETWORK, WALLET)
    transfers = fetch_all_transfers(NETWORK, WALLET)
    feed = build_activity_feed(trades, transfers)

    for entry in feed[:10]:
        if entry["type"] == "trade":
            print(f"{entry['timestamp']}  TRADE     {entry['kind']:<4}  ${entry['volume_usd']}")
        else:
            print(f"{entry['timestamp']}  TRANSFER  {entry['direction']:<3}   {entry['amount']} {entry['token']}")

    pnl = get_pnl(WALLET, NETWORKS)
    summary = pnl["data"]["attributes"]
    print(f"\nRealized PnL: ${summary['total_realized_pnl_usd']}")
    print(f"Unrealized PnL: ${summary['total_unrealized_pnl_usd']}")
    for network in summary["networks"]:
        print(f"  {network['network']:<10} realized ${network['realized_pnl_usd']}  unrealized ${network['unrealized_pnl_usd']}")
