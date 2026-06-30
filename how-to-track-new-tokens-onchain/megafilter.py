from datetime import datetime
from cg_client import get, index_included

def fetch_megafilter():
    """Return new pools across every chain, pre-filtered server-side."""
    payload = get("/onchain/pools/megafilter", params={
        "include": "base_token,network",
        "pool_created_hour_max": 0.1,      # pools created in the last 6 minutes
        "reserve_in_usd_min": 1_000,       # liquidity floor
        "h24_volume_usd_min": 100,         # activity floor
        "checks": "no_honeypot",
        "sort": "pool_created_at_desc",
    })
    included = index_included(payload)
    results = []
    for pool in payload["data"]:
        attrs = pool["attributes"]
        rels = pool["relationships"]
        base = included[rels["base_token"]["data"]["id"]]["attributes"]
        net = included[rels["network"]["data"]["id"]]["attributes"]
        vol = attrs.get("volume_usd") or {}
        chg = attrs.get("price_change_percentage") or {}
        results.append({
            "network": net["name"],
            "symbol": base.get("symbol"),
            "pool_address": attrs.get("address"),
            "price_usd": float(attrs.get("base_token_price_usd") or 0),
            "fdv_usd": float(attrs.get("fdv_usd") or 0),
            "market_cap_usd": float(attrs.get("market_cap_usd") or 0),
            "reserve_usd": float(attrs.get("reserve_in_usd") or 0),
            "volume_5m_usd": float(vol.get("m5") or 0),
            "price_change_5m_pct": float(chg.get("m5") or 0),
            "created_at": attrs["pool_created_at"],
        })
    return results

if __name__ == "__main__":
    pools = fetch_megafilter()

    print("=" * 78)
    print("  NEW POOLS (Megafilter)")
    print("=" * 78)
    print(f"  Generated: {datetime.utcnow().isoformat()}Z")
    print(f"  Window:    past 6 minutes (0.1 hours)")
    print(f"  Filters:   reserve >= $1,000  |  24h volume >= $100  |  no_honeypot")
    print(f"  Matches:   {len(pools)} pools across 250+ chains")
    print("=" * 78)
    print()

    for p in pools:
        mcap = f"${p['market_cap_usd']:,.2f}" if p['market_cap_usd'] else "n/a"
        print(f"  {p['symbol']} ({p['network']})")
        print(f"    Pool       : {p['pool_address']}")
        print(f"    Price      : ${p['price_usd']:,.8f}")
        print(f"    FDV        : ${p['fdv_usd']:,.2f}")
        print(f"    Market Cap : {mcap}")
        print(f"    Reserve    : ${p['reserve_usd']:,.2f}")
        print(f"    5m Volume  : ${p['volume_5m_usd']:,.2f}")
        print(f"    5m Change  : {p['price_change_5m_pct']:+.2f}%")
        print(f"    Created    : {p['created_at']}")
        print()
