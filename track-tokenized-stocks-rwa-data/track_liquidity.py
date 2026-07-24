import requests
from config import HEADERS, ONCHAIN_URL

def build_network_map():
    # e.g. "ethereum" maps to "eth", "arbitrum-one" maps to "arbitrum"
    network_map = {}
    for page in range(1, 4):
        response = requests.get(f"{ONCHAIN_URL}/networks", headers=HEADERS, params={"page": page})
        response.raise_for_status()
        for net in response.json()["data"]:
            platform = net["attributes"].get("coingecko_asset_platform_id")
            if platform:
                network_map[platform] = net["id"]
    return network_map

# SDK equivalent: client.onchain.networks.get(page=1)

def get_pools_for_token(network_id, token_address):
    # ranked by a combination of liquidity and 24-hour volume
    url = f"{ONCHAIN_URL}/networks/{network_id}/tokens/{token_address}/pools"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()["data"]

# SDK equivalent: client.onchain.networks.tokens.pools.get(token_address, network=network_id)

def get_liquidity_across_chains(detail_platforms, network_map):
    rows = []
    for asset_platform, details in detail_platforms.items():
        network_id = network_map.get(asset_platform)
        if not network_id:
            continue
        for pool in get_pools_for_token(network_id, details["contract_address"]):
            rows.append({
                "network": network_id,
                "pool": pool["attributes"]["name"],
                "pool_address": pool["attributes"]["address"],
                # GeckoTerminal returns these as strings, cast to float and round for display
                "liquidity_usd": round(float(pool["attributes"]["reserve_in_usd"]), 2),
                "volume_24h": round(float(pool["attributes"]["volume_usd"]["h24"]), 2),
            })
    return rows

if __name__ == "__main__":
    # detail_platforms comes from get_contract_addresses() in the discovery step
    tesla_platforms = {
        "solana": {"contract_address": "XsDoVfqeBukxuZHWhdvWHBhgEHjGNst4MLodqsJHzoB"},
        "ethereum": {"contract_address": "0x8ad3c73f833d3f9a523ab01476625f269aeb7cf0"},
    }
    rows = get_liquidity_across_chains(tesla_platforms, build_network_map())

    print(f"{'NETWORK':<8}{'POOL':<18}{'POOL_ADDRESS':<16}{'LIQUIDITY_USD':>14}{'VOLUME_24H':>12}")
    print("-" * 68)
    for r in rows:
        # Truncate the address for a readable print; rows still holds the full value for reuse
        addr = r["pool_address"]
        short_addr = f"{addr[:6]}...{addr[-4:]}"
        print(f"{r['network']:<8}{r['pool']:<18}{short_addr:<16}{r['liquidity_usd']:>14,.2f}{r['volume_24h']:>12,.2f}")
