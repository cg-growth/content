"""M0 live smoke test: python -m app.smoke  (run via ./with-keys.sh)."""
import asyncio
import time
from collections import Counter

from typesafe_sdk import Noul

from .cg_rest import CGRest
from .cg_ws import CGStream
from .jev import Jev


async def main():
    cg = CGRest()
    for net in ("solana", "robinhood"):
        pools, _ = await cg.trending_pools(net, "1h", 50)
        multi, _ = await cg.pools_multi(net, [p["attributes"]["address"] for p in pools])
        tok = pools[0]["relationships"]["base_token"]["data"]["id"].split("_", 1)[1]
        info = await cg.token_info(net, tok)
        print(f"[{net}] trending={len(pools)} pools_multi={len(multi)}/{len(pools)} info.gt_score={info.get('gt_score')}")
    news = await cg.news("bitcoin")
    print(f"[news] bitcoin items={len(news)}")

    pools, _ = await cg.trending_pools("solana", "5m", 20)
    busiest = max(pools, key=lambda p: p["attributes"]["transactions"]["m5"]["buys"] + p["attributes"]["transactions"]["m5"]["sells"])
    pid = "solana:" + busiest["attributes"]["address"]
    print(f"[ws] busiest pool {busiest['attributes']['name']} ({pid})")

    counts, first = Counter(), {}
    t0 = time.monotonic()

    def on_event(ch, m):
        counts[ch] += 1
        first.setdefault(ch, round(time.monotonic() - t0, 2))

    s = CGStream(on_event)
    await s.set_pools([pid], [pid])
    s.start()
    await asyncio.sleep(60)
    await s.stop()
    print(f"[ws] 60s: G2={counts['G2']} ({counts['G2']/60:.2f}/s) G3={counts['G3']} ({counts['G3']/60:.2f}/s) first_seen={first} status_ok={bool(counts)}")

    jev = Jev()
    r, ms, toks = await jev.ask("Bitcoin is up 3% today on ETF inflows.", {"q": Noul(instructions="Is sentiment positive?")})
    print(f"[jev] noul={r.nouls['q'].noul:.2f} latency={ms}ms tokens={toks}")
    await jev.close()
    await cg.close()


if __name__ == "__main__":
    asyncio.run(main())
