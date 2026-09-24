import asyncio

from ..cg_rest import CGRest
from ..util import age_hours, f

WINDOWS = ("m5", "h1", "h6", "h24")


def base_token_address(pool: dict) -> str:
    return pool["relationships"]["base_token"]["data"]["id"].split("_", 1)[1]


def build_row(pool: dict, included: dict) -> dict:
    a = pool["attributes"]
    tok_id = pool["relationships"]["base_token"]["data"]["id"]
    tok = included.get(tok_id, {}).get("attributes", {})
    tx = a.get("transactions") or {}
    pc = a.get("price_change_percentage") or {}
    vol = a.get("volume_usd") or {}
    h24 = tx.get("h24") or {}
    return {
        "id": a["address"],
        "pool_name": a.get("name"),
        "token": {
            "address": tok.get("address") or base_token_address(pool),
            "name": tok.get("name"),
            "symbol": tok.get("symbol"),
            "image_url": tok.get("image_url") if tok.get("image_url") not in (None, "missing.png") else None,
        },
        "price_usd": f(a.get("base_token_price_usd")),
        "change": {w: f(pc.get(w)) for w in WINDOWS},
        "volume": {w: f(vol.get(w)) for w in WINDOWS},
        "txns": {w: tx.get(w) or {} for w in ("m5", "m15", "m30", "h1", "h6", "h24")},
        "buys_h24": h24.get("buys"),
        "sells_h24": h24.get("sells"),
        "makers_h24": (h24.get("buyers") or 0) + (h24.get("sellers") or 0),
        "reserve_usd": f(a.get("reserve_in_usd")),
        "fdv_usd": f(a.get("fdv_usd")),
        "mcap_usd": f(a.get("market_cap_usd")),
        "age_h": age_hours(a.get("pool_created_at")),
        "locked_liquidity_pct": f(a.get("locked_liquidity_percentage")),
    }


async def load_feed(cg: CGRest, chain: str, window: str, n: int) -> list[dict]:
    pools, included = await cg.trending_pools(chain, window, n)
    return [build_row(p, included) for p in pools]


async def load_rows_for_labelling(cg: CGRest, chain: str, pool_ids: list[str]) -> list[dict]:
    pools, included = await cg.pools_multi(chain, pool_ids)
    order = {pid: i for i, pid in enumerate(pool_ids)}
    rows = [build_row(p, included) for p in pools]
    rows.sort(key=lambda r: order.get(r["id"], 1e9))
    return rows


async def attach_info(cg: CGRest, chain: str, rows: list[dict]):
    async def one(r):
        try:
            r["info"] = await cg.token_info(chain, r["token"]["address"])
        except Exception as e:
            r["info"] = None
            r["info_error"] = str(e)[:120]

    addrs = list(dict.fromkeys(r["token"]["address"] for r in rows))

    async def multi():
        try:
            return await cg.tokens_multi(chain, addrs)
        except Exception:
            return {}

    toks, *_ = await asyncio.gather(multi(), *(one(r) for r in rows))
    for r in rows:
        t = toks.get(r["token"]["address"].lower()) or {}
        r["token_level"] = {
            "total_liquidity_usd": f(t.get("total_reserve_in_usd")),
            "market_cap_usd": f(t.get("market_cap_usd")),
            "listed_on_coingecko": bool(t.get("coingecko_coin_id")) if t else None,
        }
