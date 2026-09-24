import re

from ..cg_rest import CGRest

EXCLUDE_IDS = {
    "wrapped-bitcoin", "weth", "staked-ether", "wrapped-steth", "wrapped-eeth", "coinbase-wrapped-btc", "rocket-pool-eth",
    "binance-staked-sol", "jito-staked-sol", "msol", "mantle-staked-ether", "kelp-dao-restaked-eth", "renzo-restaked-eth",
    "ether-fi-staked-eth", "wbnb", "wrapped-solana", "binance-bridged-usdt-bnb-smart-chain", "bridged-usdc-polygon-pos-bridge",
    "lombard-staked-btc", "solv-btc", "coinbase-wrapped-staked-eth", "wrapped-beacon-eth", "susds", "usds", "savings-dai",
    "ethena-staked-usde", "binance-peg-weth", "arbitrum-bridged-weth-arbitrum-one", "wrapped-avax", "wrapped-tron",
    # tokenized funds / RWA credit / non-USD stables: price tracks NAV or FX, not market sentiment
    "figure-heloc", "hashnote-usyc", "blackrock-usd-institutional-digital-liquidity-fund", "ondo-us-dollar-yield",
    "spiko-amundi-overnight-swap-fund-eur", "eutbl", "superstate-short-duration-us-government-securities-fund-ustb",
    "janus-henderson-anemoy-aaa-clo-fund", "ylds", "a7a5", "ousg", "usdtb",
}
EXCLUDE_NAME = re.compile(r"\b(wrapped|staked|restaked|bridged|liquid staking|peg)\b", re.I)


def is_flat_price(c: dict) -> bool:
    """Tokenized treasuries / yield-bearing dollar assets that aren't tagged as stablecoins: price barely moves."""
    d30 = c.get("price_change_percentage_30d_in_currency")
    d24 = c.get("price_change_percentage_24h_in_currency")
    return d30 is not None and d24 is not None and abs(d30) < 1.0 and abs(d24) < 0.3


async def load_universe(cg: CGRest, n: int, include_stables: bool, category: str | None = None, ids: list[str] | None = None) -> list[dict]:
    if ids:
        return (await cg.coins_markets(len(ids), ids=ids))[:n]
    if category:
        return (await cg.coins_markets(n, category=category))[:n]
    coins = await cg.coins_markets(250)
    if include_stables:
        return coins[:n]
    try:
        stable_ids = {c["id"] for c in await cg.coins_markets(250, category="stablecoins")}
    except Exception:
        stable_ids = set()
    out = []
    for c in coins:
        if c["id"] in stable_ids or c["id"] in EXCLUDE_IDS or EXCLUDE_NAME.search(c.get("name") or ""):
            continue
        if is_flat_price(c):
            continue
        out.append(c)
        if len(out) >= n:
            break
    return out
