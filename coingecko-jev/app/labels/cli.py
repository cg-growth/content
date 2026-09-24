"""Dry-run: python -m app.labels.cli solana 50"""
import asyncio
import sys
from collections import Counter

from ..cg_rest import CGRest
from ..jev import Jev
from .feed import load_feed
from .run import run_labels


async def main(chain="solana", n=50, window="1h"):
    cg, jev = CGRest(), Jev()
    feed = await load_feed(cg, chain, window, n)
    chip_counts = Counter()
    print(f"{'token':14} {'mom':9} {'risk':>5}  chips")
    async for ev, p in run_labels(cg, jev, chain, [r["id"] for r in feed]):
        if ev == "start":
            print(f"prep {p['prep_ms']} ms for {p['total']} tokens")
        elif ev == "row":
            if "error" in p:
                print("ERROR", p["id"][:10], p["error"])
                continue
            chip_counts.update(c["label"] for c in p["chips"])
            m = p["momentum"]
            sym = (p["row"]["token"]["symbol"] or "?")[:13]
            print(f"{sym:14} {str(m['value']):9} {p['risk']:5.1f}  {', '.join(c['label'] + ('?' if c['low_conf'] else '') for c in p['chips'])}")
        elif ev == "done":
            print(f"\nDONE {p['elapsed_ms']} ms · Jev calls {p['calls']} · tokens {p['input_tokens']} · ${p['cost_usd']:.4f} · p50 {p['p50_ms']} ms · CG calls {p['cg_calls']}")
    print("chip counts:", dict(chip_counts))
    await jev.close()
    await cg.close()


if __name__ == "__main__":
    a = sys.argv[1:]
    asyncio.run(main(a[0] if a else "solana", int(a[1]) if len(a) > 1 else 50))
