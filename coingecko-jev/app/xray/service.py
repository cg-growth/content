import asyncio
import time

from .. import config
from ..cg_rest import CGRest
from ..jev import Jev, Usage, answers_to_dict
from ..util import f
from .profiler import WalletProfiler
from .questions import PERSONA_LABEL, TOKEN_QUESTIONS, TOKEN_SIZES, VERDICT_LABEL

SMART = {"proven_trader", "accumulator"}


def _by(ws: list[dict], kind: str) -> dict:
    out: dict = {}
    for w in ws:
        t = w.get("token") or {}
        v = (t.get("supply_share_pct") or 0) if kind == "supply" else (t.get("bought_usd") or 0) + (t.get("sold_usd") or 0)
        out[w.get("persona", "?")] = round(out.get(w.get("persona", "?"), 0) + v, 2)
    return out


class WalletDataUnavailable(Exception):
    pass


def aggregate(wallets: list[dict]) -> dict:
    comp: dict[str, dict] = {}
    tot_vol = tot_supply = 0.0
    smart_net = insider_supply = bot_vol = treasury_supply = 0.0
    smart_n = copy_n = 0
    for w in wallets:
        t = w.get("token") or {}
        vol = (t.get("bought_usd") or 0) + (t.get("sold_usd") or 0)
        sup = t.get("supply_share_pct") or 0
        p = w.get("persona", "new_wallet")
        c = comp.setdefault(p, {"label": PERSONA_LABEL.get(p, p), "wallets": 0, "supply_pct": 0.0, "volume_usd": 0.0})
        c["wallets"] += 1
        c["supply_pct"] += sup
        c["volume_usd"] += vol
        tot_vol += vol
        tot_supply += sup
        if not w.get("scored"):
            continue
        if p in SMART and (w.get("skill") or 0) >= 60:
            smart_n += 1
            smart_net += t.get("net_flow_24h_usd") or 0
        if p == "insider_like":
            insider_supply += sup
        if p == "treasury_allocation":
            treasury_supply += sup
        if p == "market_maker_bot":
            bot_vol += vol
        if w.get("copy_worthy"):
            copy_n += 1
    for c in comp.values():
        c["supply_pct"] = round(c["supply_pct"], 2)
        c["volume_share"] = round(c["volume_usd"] / tot_vol, 3) if tot_vol else 0
        c["volume_usd"] = round(c["volume_usd"])
    return {
        "wallets": len(wallets),
        "composition": comp,
        "smart_wallets": smart_n,
        "smart_net_flow_24h_usd": round(smart_net),
        "insider_like_supply_pct": round(insider_supply, 2),
        "treasury_allocation_supply_pct": round(treasury_supply, 2),
        "bot_volume_share": round(bot_vol / tot_vol, 3) if tot_vol else 0,
        "copyable_wallets": copy_n,
        "supply_covered_pct": round(tot_supply, 2),
    }


class XrayService:
    def __init__(self, cg: CGRest, jev: Jev, profiler: WalletProfiler):
        self.cg, self.jev, self.profiler = cg, jev, profiler

    async def token_context(self, chain: str, token: str, pool: str | None = None) -> dict:
        d = await self.cg.get(f"/onchain/networks/{chain}/tokens/{token}", {"include": "top_pools"}, ttl=30)
        a = d["data"]["attributes"]
        pools = [i for i in d.get("included", []) if i.get("type") == "pool"]
        p = next((x for x in pools if x["attributes"]["address"].lower() == (pool or "").lower()), pools[0] if pools else None)
        pa = p["attributes"] if p else {}
        info = {}
        try:
            info = await self.cg.token_info(chain, token)
        except Exception:
            pass
        return {
            "holder_addrs": set(),
            "chain": chain, "chain_label": config.WALLET_CHAINS.get(chain, chain), "address": a.get("address"), "name": a.get("name"),
            "symbol": a.get("symbol"), "image_url": a.get("image_url") if a.get("image_url") not in (None, "missing.png") else None,
            "price_usd": f(a.get("price_usd")), "fdv_usd": f(a.get("fdv_usd")), "market_cap_usd": f(a.get("market_cap_usd")),
            "volume_24h_usd": f((a.get("volume_usd") or {}).get("h24")), "liquidity_usd": f(a.get("total_reserve_in_usd")),
            "pool_address": pa.get("address"), "pool_name": pa.get("name"), "pool_created_at": pa.get("pool_created_at"),
            "change_24h": f((pa.get("price_change_percentage") or {}).get("h24")),
            "holders_count": (info.get("holders") or {}).get("count"), "gt_score": f(info.get("gt_score")),
        }

    async def wallet_rows(self, chain: str, token: str) -> list[dict]:
        rows: dict[str, dict] = {}
        traders, holders = [], []
        for sort, n in (("realized_pnl_usd_desc", 30), ("total_buy_usd_desc", 25)):
            try:
                d = await self.cg.get(f"/onchain/networks/{chain}/tokens/{token}/top_traders", {"traders": n, "sort": sort, "include_address_label": "true"}, ttl=60)
                traders += d["data"]["attributes"]["traders"]
            except Exception:
                pass
        try:
            d = await self.cg.get(f"/onchain/networks/{chain}/tokens/{token}/top_holders", {"holders": 40, "include_pnl_details": "true"}, ttl=60)
            holders = d["data"]["attributes"]["holders"]
        except Exception:
            pass
        for h in holders[:30]:
            rows[h["address"].lower()] = {**h, "_source": "holder"}
        for t in traders:
            k = t["address"].lower()
            if k in rows:
                rows[k] = {**t, **{kk: vv for kk, vv in rows[k].items() if vv is not None}, "_source": "holder + trader"}
            elif len(rows) < config.XRAY_WALLET_CAP:
                rows[k] = {**t, "_source": "trader"}
        return list(rows.values())

    async def run(self, chain: str, token: str, pool: str | None = None):
        if chain not in config.WALLET_CHAINS:
            raise WalletDataUnavailable("Couldn't load wallet data for this token.")
        t0 = time.perf_counter()
        cg0 = self.cg.calls
        usage = Usage()
        ctx = await self.token_context(chain, token, pool)
        rows = await self.wallet_rows(chain, token)
        ctx["holder_addrs"] = {r["address"].lower() for r in rows if "holder" in (r.get("_source") or "")}
        if not rows:
            raise WalletDataUnavailable("Couldn't load wallet data for this token.")
        yield "start", {"token": {k: v for k, v in ctx.items() if k != "holder_addrs"}, "total": len(rows)}
        q: asyncio.Queue = asyncio.Queue()

        async def one(i, row):
            try:
                w = await self.profiler.profile(chain, token, row, ctx, usage)
                await q.put({**w, "index": i})
            except Exception as e:
                await q.put({"index": i, "address": row["address"], "error": type(e).__name__})

        tasks = [asyncio.create_task(one(i, r)) for i, r in enumerate(rows)]
        wallets = []
        for k in range(len(rows)):
            w = await q.get()
            if "error" not in w:
                wallets.append(w)
            yield "wallet", w
            yield "progress", {"done": k + 1, "total": len(rows), "elapsed_ms": round((time.perf_counter() - t0) * 1000), **usage.snapshot()}
        await asyncio.gather(*tasks)
        agg = aggregate(wallets)
        top = sorted((w for w in wallets if w.get("scored")), key=lambda w: -((w["token"].get("supply_share_pct") or 0) * 10 + (w["token"].get("bought_usd") or 0) / 1e4))[:12]
        holders = [w for w in wallets if "holder" in (w.get("source") or "")]
        traders_only = [w for w in wallets if (w.get("source") or "") == "trader"]
        state = {
            "token": f"{ctx['symbol']} on {ctx['chain_label']}", "breakdown": agg,
            "note": "Top traders are sampled by realized profit and by buy size, so bots are over-represented among traders on liquid tokens. Judge the token by who HOLDS supply as well as who trades.",
            "holders_by_persona_supply_pct": _by(holders, "supply"), "traders_by_persona_volume_usd": _by(traders_only, "volume"),
            "key_wallets": [{"persona": w["persona"], "skill": w["skill"], "insider": w["insider"], "stance": w["stance"],
                             "supply_pct": w["token"].get("supply_share_pct"), "net_flow_24h_usd": w["token"].get("net_flow_24h_usd")} for w in top],
        }
        verdict = None
        try:
            r, ms, _ = await self.jev.ask(state, TOKEN_QUESTIONS, usage)
            a = answers_to_dict(r, TOKEN_SIZES)
            verdict = {"verdict": a["verdict"]["choice"], "label": VERDICT_LABEL.get(a["verdict"]["choice"]), "confidence": a["verdict"]["confidence"],
                       "quality": a["quality"]["value"], "rug_signal": a["rug_signal"]["value"], "latency_ms": ms}
        except Exception:
            pass
        yield "verdict", {"aggregate": agg, "verdict": verdict}
        yield "done", {"elapsed_ms": round((time.perf_counter() - t0) * 1000), "cg_calls": self.cg.calls - cg0, **usage.snapshot()}
