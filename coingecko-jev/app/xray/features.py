"""Pure feature extraction for a wallet: multi-chain lifetime, portfolio, recent activity, and behaviour on one token."""
import statistics
from datetime import datetime, timezone

from ..util import f, rnd

STABLES = {"USDC", "USDT", "DAI", "USDG", "USDS", "USDE", "PYUSD", "FDUSD", "TUSD", "USD1", "USDC.E", "USDBC", "LUSD", "FRAX", "GHO", "RLUSD", "USDT0"}


def _ts(iso):
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
    except (AttributeError, ValueError):
        return None


def pnl_features(attrs: dict | None) -> dict:
    """From GET /onchain/wallets/{address}/pnl (all wallet networks in one call)."""
    if not attrs:
        return {"available": False}
    stats = attrs.get("token_stats") or []
    realized = [f(s.get("realized_pnl_usd"), 0.0) for s in stats]
    sold = [f(s.get("realized_pnl_usd"), 0.0) for s in stats if (s.get("total_sell_count") or 0) > 0]
    wins = [r for r in sold if r > 0]
    pos = [r for r in realized if r > 0]
    buys = sum(s.get("total_buy_count") or 0 for s in stats)
    sells = sum(s.get("total_sell_count") or 0 for s in stats)
    vol = sum(f(s.get("total_buy_usd"), 0) + f(s.get("total_sell_usd"), 0) for s in stats)
    nets = [n for n in (attrs.get("networks") or []) if (n.get("tokens") or 0) > 0]
    return {
        "available": True,
        "tokens_traded": attrs.get("total_tokens"),
        "tokens_in_sample": len(stats),
        "sample_note": "per-token stats cover the most-traded tokens by buy volume" if (attrs.get("total_tokens") or 0) > len(stats) else "all tokens",
        "lifetime_realized_pnl_usd": rnd(f(attrs.get("total_realized_pnl_usd")), 0),
        "lifetime_unrealized_pnl_usd": rnd(f(attrs.get("total_unrealized_pnl_usd")), 0),
        "win_rate_tokens": rnd(len(wins) / len(sold), 3) if sold else None,
        "profit_concentration_top_token": rnd(max(pos) / sum(pos), 3) if pos else None,
        "median_realized_per_token_usd": rnd(statistics.median(sold), 0) if sold else None,
        "total_buys": buys,
        "total_sells": sells,
        "avg_trade_usd": rnd(vol / (buys + sells), 0) if buys + sells else None,
        "active_networks": [n.get("network") for n in nets],
        "pnl_by_network": {n.get("network"): {"realized": rnd(f(n.get("realized_pnl_usd")), 0), "tokens": n.get("tokens")} for n in nets},
    }


def top_traded_tokens(attrs: dict | None, n: int = 12) -> list[dict]:
    """Token names matter: Jev judges memecoin vs blue-chip focus from them."""
    stats = (attrs or {}).get("token_stats") or []
    ranked = sorted(stats, key=lambda s: -(f(s.get("total_buy_usd"), 0) + f(s.get("total_sell_usd"), 0)))[:n]
    return [
        {"symbol": s.get("symbol"), "name": s.get("name"), "network": s.get("network"),
         "realized_usd": rnd(f(s.get("realized_pnl_usd")), 0), "volume_usd": rnd(f(s.get("total_buy_usd"), 0) + f(s.get("total_sell_usd"), 0), 0),
         "buys": s.get("total_buy_count"), "sells": s.get("total_sell_count")}
        for s in ranked
    ]


def portfolio_features(bal: dict | None) -> dict:
    """From GET /onchain/wallets/{address}/balances (all wallet networks)."""
    if not bal:
        return {"available": False}
    items = bal.get("balances") or []
    total = f(bal.get("total_value_usd"), 0.0) or sum(f(i.get("value_usd"), 0) for i in items)
    vals = sorted((f(i.get("value_usd"), 0) for i in items), reverse=True)
    stable = sum(f(i.get("value_usd"), 0) for i in items if (i.get("symbol") or "").upper() in STABLES)
    native = sum(f(i.get("value_usd"), 0) for i in items if i.get("token_type") == "native")
    return {
        "available": True,
        "portfolio_value_usd": rnd(total, 0),
        "holdings": bal.get("total_holdings") or len(items),
        "networks_with_balance": [n.get("network") for n in (bal.get("networks") or []) if f(n.get("value_usd"), 0) > 1],
        "top_holding_share": rnd(vals[0] / total, 3) if total and vals else None,
        "stablecoin_share": rnd(stable / total, 3) if total else None,
        "native_share": rnd(native / total, 3) if total else None,
        "top_holdings": [{"symbol": i.get("symbol"), "network": i.get("network"), "value_usd": rnd(f(i.get("value_usd")), 0)} for i in items[:8]],
    }


def activity_features(trades: list[dict], now: float | None = None) -> dict:
    """From the latest ~100 wallet trades on a network."""
    now = now or datetime.now(timezone.utc).timestamp()
    ts = sorted(t for t in (_ts(x.get("block_timestamp")) for x in trades) if t)
    if not ts:
        return {"recent_trades": 0, "days_since_last_trade": None}
    gaps = [b - a for a, b in zip(ts, ts[1:])]
    span_days = max((ts[-1] - ts[0]) / 86400, 1 / 24)
    pools = {x.get("pool_address") for x in trades}
    buys = sum(1 for x in trades if x.get("kind") == "buy")
    vol = sum(f(x.get("volume_in_usd"), 0) for x in trades)
    return {
        "recent_trades": len(ts),
        "recent_trades_per_day": rnd(len(ts) / span_days, 1),
        "median_seconds_between_trades": rnd(statistics.median(gaps), 0) if gaps else None,
        "distinct_pools_recent": len(pools),
        "recent_buy_share": rnd(buys / len(trades), 2),
        "recent_avg_trade_usd": rnd(vol / len(trades), 0),
        "days_since_last_trade": rnd((now - ts[-1]) / 86400, 1),
    }


def funding_features(transfers: list[dict], token_holders: set[str], mint_like: set[str]) -> dict:
    """How a holder that never bought got its tokens (inbound transfers of this token)."""
    inbound = [t for t in transfers if t.get("direction") == "in"]
    if not inbound:
        return {"inbound_transfers": 0}
    inbound.sort(key=lambda t: _ts(t.get("block_timestamp")) or 0)
    first = inbound[0]
    src = (first.get("from_address") or "").lower()
    return {
        "inbound_transfers": len(inbound),
        "first_received_from": "mint / zero address" if src in mint_like else "another top holder" if src in token_holders else "other wallet",
        "first_received_at": first.get("block_timestamp"),
    }


def token_features(row: dict, token_trades: list[dict], ctx: dict, now: float | None = None) -> dict:
    """Behaviour on THIS token. `row` is the top-trader/holder entry; ctx has price_usd, pool_created_at."""
    now = now or datetime.now(timezone.utc).timestamp()
    avg_buy = f(row.get("average_buy_price_usd"))
    price = f(ctx.get("price_usd"))
    trade_ts = sorted(t for t in (_ts(x.get("block_timestamp")) for x in token_trades) if t)
    created = _ts(ctx.get("pool_created_at"))
    first_min = rnd((trade_ts[0] - created) / 60, 0) if trade_ts and created and trade_ts[0] - created < 30 * 86400 else None
    net_24h = sum(
        (f(x.get("volume_in_usd"), 0) if x.get("kind") == "buy" else -f(x.get("volume_in_usd"), 0))
        for x in token_trades
        if (_ts(x.get("block_timestamp")) or 0) >= now - 86400
    )
    return {
        "role": row.get("_source"),
        "supply_share_pct": rnd(f(row.get("percentage")), 3),
        "position_value_usd": rnd(f(row.get("value")), 0),
        "realized_pnl_usd": rnd(f(row.get("realized_pnl_usd")), 0),
        "unrealized_pnl_usd": rnd(f(row.get("unrealized_pnl_usd")), 0),
        "buy_count": row.get("total_buy_count"),
        "sell_count": row.get("total_sell_count"),
        "bought_usd": rnd(f(row.get("total_buy_usd")), 0),
        "sold_usd": rnd(f(row.get("total_sell_usd")), 0),
        "price_vs_avg_buy_multiple": rnd(price / avg_buy, 2) if price and avg_buy else None,
        "first_trade_minutes_after_pool_launch": first_min,
        "trades_in_token_recent": len(trade_ts),
        "net_flow_24h_usd": rnd(net_24h, 0),
        "never_bought_this_token": not row.get("total_buy_count") and not trade_ts,
        "api_label": row.get("label") or row.get("name"),
        "api_label_type": row.get("type"),
    }


def is_protocol_holder(row: dict) -> bool:
    """Holders that never traded (escrows, pools, treasuries, burn) carry a label and no PnL fields."""
    no_trades = row.get("total_buy_count") is None and row.get("average_buy_price_usd") is None
    return "holder" in (row.get("_source") or "") and no_trades and bool(row.get("label"))


def likely_bot_row(row: dict) -> bool:
    """Cheap pre-filter for candidate lists: thousands of trades in a single token."""
    return (row.get("total_buy_count") or 0) + (row.get("total_sell_count") or 0) > 1500
