"""Compact per-token state for Jev. Derived ratios are pre-computed so Jev judges instead of doing arithmetic."""
from ..config import CHAINS
from ..util import f, ratio, rnd


def _authority(v, chain: str):
    if chain != "solana":
        return "n/a on EVM"
    if v in ("yes", "no"):
        return "renounced" if v == "no" else "active"
    return "unknown"


def _honeypot(v):
    if v is True:
        return "yes"
    if v is False:
        return "no"
    return "unknown"


def build_state(row: dict, chain: str) -> dict:
    tx = row.get("txns") or {}
    info = row.get("info") or {}

    def trades_per_wallet(w, side):
        t = tx.get(w) or {}
        return ratio(t.get(side + "s"), t.get(side + "ers"))

    def buy_sell(w):
        t = tx.get(w) or {}
        return ratio(t.get("buys"), t.get("sells"))

    activity = {}
    for w in ("m5", "h1", "h6", "h24"):
        t = tx.get(w) or {}
        activity[w] = {
            "buys": t.get("buys"),
            "sells": t.get("sells"),
            "buyers": t.get("buyers"),
            "sellers": t.get("sellers"),
            "buys_per_buyer": trades_per_wallet(w, "buy"),
            "sells_per_seller": trades_per_wallet(w, "sell"),
            "buy_sell_ratio": buy_sell(w),
        }

    holders = info.get("holders") or {}
    dist = holders.get("distribution_percentage") or {}
    tiers = CHAINS.get(chain, {}).get("holder_tiers", [])
    gsd = info.get("gt_score_details") or {}

    vol24 = row.get("volume", {}).get("h24")
    state = {
        "token": f"{row['token'].get('symbol')} ({row.get('pool_name')})",
        "chain": CHAINS.get(chain, {}).get("label", chain),
        "pool_age_hours": row.get("age_h"),
        "price_change_pct": {k: rnd(v) for k, v in (row.get("change") or {}).items()},
        "volume_usd": {k: rnd(v, 0) for k, v in (row.get("volume") or {}).items()},
        "liquidity_usd": rnd(row.get("reserve_usd"), 0),
        "fdv_usd": rnd(row.get("fdv_usd"), 0),
        "volume_24h_to_liquidity": ratio(vol24, row.get("reserve_usd")),
        "liquidity_to_fdv": ratio(row.get("reserve_usd"), row.get("fdv_usd"), 4),
        "token_total_liquidity_all_pools_usd": rnd((row.get("token_level") or {}).get("total_liquidity_usd"), 0),
        "token_market_cap_usd": rnd((row.get("token_level") or {}).get("market_cap_usd"), 0),
        "listed_on_coingecko": (row.get("token_level") or {}).get("listed_on_coingecko"),
        "locked_liquidity_pct": row.get("locked_liquidity_pct"),
        "trading_activity": activity,
        "gt_score": rnd(f(info.get("gt_score")), 1),
        "gt_score_components": {k: rnd(f(v), 1) for k, v in gsd.items()} or None,
        "holders_count": holders.get("count"),
        "holder_concentration_pct": {t: rnd(f(dist.get(t)), 1) for t in tiers} if dist else None,
        "mint_authority": _authority(info.get("mint_authority"), chain),
        "freeze_authority": _authority(info.get("freeze_authority"), chain),
        "honeypot": _honeypot(info.get("is_honeypot")),
    }
    lp = row.get("launchpad_details") or info.get("launchpad_details")
    if lp:
        state["launchpad"] = lp
    if not info:
        state["note"] = "token security/holder info unavailable"
    return state
