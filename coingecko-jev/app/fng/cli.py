"""Dry-run: python -m app.fng.cli 100"""
import asyncio
import sys
from collections import Counter

from ..cg_rest import CGRest
from ..jev import Jev
from .run import FngService


async def main(n=100):
    cg, jev = CGRest(), Jev()
    svc = FngService(cg, jev)
    rows = []
    async for ev, p in svc.run(n):
        if ev == "start":
            print(f"universe: {p['total']} coins (first: {', '.join(c['symbol'] for c in p['coins'][:12])} …)")
        elif ev == "row":
            rows.append(p)
            if "error" in p:
                print("ERROR", p["coin"]["id"], p["error"])
        elif ev == "done":
            done = p
    rows = [r for r in rows if "error" not in r]
    rows.sort(key=lambda r: r["index"])
    print(f"\n{'coin':8} {'F&G':>5} {'bucket':14} {'mkt':>5} {'news':>5} {'hol':>5} rel96h/rel  top headline")
    for r in rows[:25]:
        th = r["top_headline"]["title"][:60] if r["top_headline"] else ""
        print(f"{r['coin']['symbol'][:8]:8} {r['fng'] or 0:5.1f} {r['bucket'] or '-':14} {r['market_score'] or 0:5.1f} "
              f"{r['news_score'] if r['news_score'] is not None else float('nan'):5.1f} {r['components']['holistic']:5.1f} "
              f"{r['relevant_headlines']:>3}/{r['relevant_total']:<3}{' thin' if r['thin_news'] else '     '}  {th}")
    print("\nbuckets:", dict(Counter(r["bucket"] for r in rows)))
    print(f"thin news: {sum(r['thin_news'] for r in rows)} · divergence ≥30: "
          f"{sum(1 for r in rows if r['news_score'] is not None and r['market_score'] is not None and abs(r['news_score'] - r['market_score']) >= 30)}")
    print(f"DONE {done['elapsed_ms']} ms · Jev calls {done['calls']} · tokens {done['input_tokens']} · ${done['cost_usd']:.4f} · p50 {done['p50_ms']} ms · CG calls {done['cg_calls']}")
    await jev.close()
    await cg.close()


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 100))
