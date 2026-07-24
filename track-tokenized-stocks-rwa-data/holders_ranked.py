import requests
from config import HEADERS, ONCHAIN_URL

def get_top_holders(network_id, token_address, limit=10):
    url = f"{ONCHAIN_URL}/networks/{network_id}/tokens/{token_address}/top_holders"
    response = requests.get(url, headers=HEADERS, params={"holders": limit})
    response.raise_for_status()
    return response.json()["data"]["attributes"]["holders"]

# SDK equivalent: client.onchain.networks.tokens.top_holders.get(token_address, network=network_id, holders="10")

def get_holders_chart(network_id, token_address, days="30"):
    url = f"{ONCHAIN_URL}/networks/{network_id}/tokens/{token_address}/holders_chart"
    response = requests.get(url, headers=HEADERS, params={"days": days})
    response.raise_for_status()
    return response.json()["data"]["attributes"]["token_holders_list"]

# SDK equivalent: client.onchain.networks.tokens.holders_chart.get(token_address, network=network_id, days="30")

def get_recent_trades(network_id, token_address, min_volume_usd=0):
    url = f"{ONCHAIN_URL}/networks/{network_id}/tokens/{token_address}/trades"
    params = {"trade_volume_in_usd_greater_than": min_volume_usd}
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()["data"]

# SDK equivalent: client.onchain.networks.tokens.trades.get(token_address, network=network_id)

if __name__ == "__main__":
    # amount, percentage, and value come back as strings; round for display
    print(f"{'RANK':<6}{'ADDRESS':<16}{'AMOUNT':>14}{'PERCENTAGE':>12}{'VALUE_USD':>16}")
    print("-" * 64)
    for h in get_top_holders("solana", "Xsc9qvGR1efVDFGLrVsmkzv3qi45LTBjeUKSPmx9qEh"):
        addr = h["address"]
        short_addr = f"{addr[:6]}...{addr[-4:]}"
        pct = h["percentage"] + "%"
        value = f"${round(float(h['value']), 2):,.2f}"
        print(f"{h['rank']:<6}{short_addr:<16}{round(float(h['amount']), 2):>14,.2f}{pct:>12}{value:>16}")

    chart = get_holders_chart("solana", "Xsc9qvGR1efVDFGLrVsmkzv3qi45LTBjeUKSPmx9qEh", days="30")
    print(f"\n{'TIMESTAMP':<22}{'HOLDER_COUNT':>14}")
    print("-" * 36)
    for timestamp, holder_count in chart[-3:]:
        print(f"{timestamp:<22}{holder_count:>14}")

    print(f"\n{'KIND':<6}{'VOLUME_USD':>12}  {'TIMESTAMP':<22}{'POOL':<16}")
    print("-" * 60)
    for t in get_recent_trades("solana", "Xsc9qvGR1efVDFGLrVsmkzv3qi45LTBjeUKSPmx9qEh", min_volume_usd=1000)[:5]:
        attrs = t["attributes"]
        pool = attrs["pool_address"]
        short_pool = f"{pool[:6]}...{pool[-4:]}"
        print(f"{attrs['kind']:<6}{round(float(attrs['volume_in_usd']), 2):>12,.2f}  {attrs['block_timestamp']:<22}{short_pool:<16}")
