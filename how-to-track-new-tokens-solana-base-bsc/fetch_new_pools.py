import sys
from cg_client import get, index_included

def fetch_new_pools(network=None, pages=2):
    """Return newest pools. Without a network, fetches across all chains.
    With a network ID, scopes to that chain."""
    if network:
        path = f"/onchain/networks/{network}/new_pools"
        include = "base_token"
    else:
        path = "/onchain/networks/new_pools"
        include = "base_token,network"

    results = []
    for page in range(1, pages + 1):
        payload = get(path, params={"include": include, "page": page})
        included = index_included(payload)
        for pool in payload["data"]:
            attrs = pool["attributes"]
            base_id = pool["relationships"]["base_token"]["data"]["id"]
            base = included[base_id]["attributes"]
            row = {
                "symbol": base.get("symbol"),
                "address": base["address"],
                "reserve_usd": float(attrs.get("reserve_in_usd") or 0),
                "volume_24h": float(attrs.get("volume_usd", {}).get("h24") or 0),
            }
            if network:
                row["network"] = network
                row["network_id"] = network
            else:
                net_id = pool["relationships"]["network"]["data"]["id"]
                row["network"] = included[net_id]["attributes"]["name"]
                row["network_id"] = net_id
            results.append(row)
    return results

if __name__ == "__main__":
    network = sys.argv[1] if len(sys.argv) > 1 else None
    pools = fetch_new_pools(network)[:10]

    header = f"{'NETWORK':<14} {'SYMBOL':<12} {'RESERVE':>14}  {'24H VOLUME':>14}"
    print()
    print(header)
    print("-" * len(header))
    for p in pools:
        print(f"{p['network'][:13]:<14} {(p['symbol'] or '?')[:11]:<12} "
              f"${p['reserve_usd']:>13,.0f}  ${p['volume_24h']:>13,.0f}")
    print()
