import asyncio
import time

from ..cg_rest import CGRest
from ..jev import Jev, Usage, answers_to_dict
from . import history, market
from .index import WEIGHTS, bucket, final_index, insights_mood, news_mood
from .questions import build_questions, criteria_sizes
from .state import build_state
from .universe import load_universe

HISTORY_DAYS = 180


def coin_public(c: dict) -> dict:
    return {
        "id": c["id"], "symbol": (c.get("symbol") or "").upper(), "name": c.get("name"), "image": c.get("image"),
        "rank": c.get("market_cap_rank"), "price": c.get("current_price"),
        "change": {"24h": c.get("price_change_percentage_24h_in_currency"), "7d": c.get("price_change_percentage_7d_in_currency"),
                   "30d": c.get("price_change_percentage_30d_in_currency")},
        "market_cap": c.get("market_cap"), "volume": c.get("total_volume"),
        "sparkline_7d": [round(x, 8) for x in ((c.get("sparkline_in_7d") or {}).get("price") or [])[::2]],
    }


class FngService:
    def __init__(self, cg: CGRest, jev: Jev, concurrency: int = 8):
        self.cg, self.jev = cg, jev
        self._sem = asyncio.Semaphore(concurrency)

    async def score_coin(self, idx: int, c: dict, usage: Usage) -> dict:
        async with self._sem:
            return await self._score_coin(idx, c, usage)

    async def _score_coin(self, idx: int, c: dict, usage: Usage) -> dict:
        cid = c["id"]
        comps, backfill = {}, []
        try:
            mc = await self.cg.market_chart(cid, HISTORY_DAYS)
            prices = [p for _, p in mc.get("prices", [])]
            times = [t for t, _ in mc.get("prices", [])]
            vols = [v for _, v in mc.get("total_volumes", [])]
            comps = market.components(prices, vols[:-1], c.get("total_volume"), c.get("price_change_percentage_24h_in_currency"))
            backfill = market.backfill(prices, vols, times, 90)
        except Exception as e:
            comps = {k: None for k in market.WEIGHTS}
            comps["_error"] = str(e)[:80]
        try:
            items = await self.cg.news(cid)
        except Exception:
            items = []
        heads = [
            {"title": it.get("title"), "url": it.get("url"), "source": it.get("source_name"), "posted_at": it.get("posted_at")}
            for it in (items or [])[:20]
            if it.get("title")
        ]
        try:
            raw_ins = await self.cg.insights(cid)
        except Exception:
            raw_ins = []
        insights = [
            {"title": it.get("title"), "description": it.get("description"), "posted_at": it.get("posted_at")}
            for it in (raw_ins or [])
            if it.get("title") and cid in (it.get("related_coin_ids") or [cid])
        ][:5]
        clean = {k: v for k, v in comps.items() if not k.startswith("_")}
        state = build_state(c, clean, heads, insights)
        name = c.get("name") or cid
        r, ms, toks = await self.jev.ask(state, build_questions(name, len(heads), len(insights)), usage)
        a = answers_to_dict(r, criteria_sizes(len(heads), len(insights)))
        for i, h in enumerate(heads):
            h["about"] = a.get(f"h{i}_about", {}).get("value")
            h["mood"] = a.get(f"h{i}_mood", {}).get("value")
            h["relevant"] = h["about"] is not None and h["about"] >= 0.5
        for i, it in enumerate(insights):
            it["mood"] = a.get(f"i{i}_mood", {}).get("value")
        news_score, relevant = news_mood(heads)
        insights_score, recent_insights = insights_mood(insights)
        thin = relevant < 3
        has_insights = insights_score is not None
        holistic = a["overall"]["value"]
        all_comps = {**clean, "insights": insights_score, "news": news_score, "holistic": holistic}
        index, used = final_index(all_comps, thin, has_insights)
        top = next((h for h in heads if h["relevant"]), None)
        return {
            "index": idx,
            "coin": coin_public(c),
            "fng": index,
            "bucket": bucket(index),
            "components": all_comps,
            "weights_used": used,
            "market_score": market.weighted(clean, market.WEIGHTS),
            "news_score": news_score,
            "insights_score": insights_score,
            "insights": insights,
            "recent_insights": recent_insights,
            "holistic_confidence": a["overall"]["confidence"],
            "relevant_headlines": relevant,
            "relevant_total": sum(1 for h in heads if h["relevant"]),
            "thin_news": thin,
            "top_headline": top,
            "headlines": heads,
            "history": history.history(cid),
            "backfill": backfill,
            "latency_ms": ms,
            "input_tokens": toks,
        }

    async def run(self, n: int = 100, include_stables: bool = False, category: str | None = None, ids: list[str] | None = None, scope: dict | None = None):
        t0 = time.perf_counter()
        cg0 = self.cg.calls
        usage = Usage()
        coins = await load_universe(self.cg, n, include_stables, category, ids)
        yield "start", {"total": len(coins), "weights": WEIGHTS, "coins": [coin_public(c) for c in coins], "scope": scope or {"kind": "top", "n": n}}
        q: asyncio.Queue = asyncio.Queue()

        async def one(i, c):
            try:
                await q.put(await self.score_coin(i, c, usage))
            except Exception as e:
                await q.put({"index": i, "coin": coin_public(c), "error": f"{type(e).__name__}: {str(e)[:160]}"})

        tasks = [asyncio.create_task(one(i, c)) for i, c in enumerate(coins)]
        rows = []
        for k in range(len(coins)):
            row = await q.get()
            rows.append(row)
            yield "row", row
            yield "progress", {"done": k + 1, "total": len(coins), "elapsed_ms": round((time.perf_counter() - t0) * 1000), **usage.snapshot()}
        await asyncio.gather(*tasks)
        ok = [r for r in rows if "error" not in r and r.get("fng") is not None]
        if ok:
            history.save(ok)
        yield "done", {"elapsed_ms": round((time.perf_counter() - t0) * 1000), "cg_calls": self.cg.calls - cg0, **usage.snapshot()}
