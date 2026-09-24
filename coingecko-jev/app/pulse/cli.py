"""Live check: python -m app.pulse.cli [chain] [seconds]"""
import asyncio
import sys
import time

from ..cg_rest import CGRest
from ..jev import Jev
from .hub import PulseHub


class Printer:
    def __init__(self):
        self.scores, self.trades, self.markers, self.t0 = [], 0, [], time.time()

    def send(self, ev, d):
        if ev == "trade":
            self.trades += 1
        elif ev == "score":
            self.scores.append((time.time(), d))
            print(f"{time.time() - self.t0:5.1f}s pump {d['pump']:5.1f} (raw {d['pump_raw']:5.1f}) dump {d['dump']:5.1f} (raw {d['dump_raw']:5.1f}) "
                  f"phase {d['phase']:12} exh {d['exhaustion']:.2f} · {d['latency_ms']} ms")
        elif ev == "marker":
            self.markers.append(d)
            print(f"   MARKER {d['side']} {d['value']}")
        elif ev in ("stopped", "jev_error", "error"):
            print("  ", ev, d)


async def main(chain="solana", seconds=60):
    cg, jev = CGRest(), Jev()
    pools, _ = await cg.trending_pools(chain, "5m", 30)
    pools.sort(key=lambda p: -(p["attributes"]["transactions"]["m5"]["buys"] + p["attributes"]["transactions"]["m5"]["sells"]))
    focus = pools[0]["attributes"]["address"]
    print("focus pool:", pools[0]["attributes"]["name"])
    hub = PulseHub(cg, jev)
    pr = Printer()
    hub.clients.add(pr)
    await hub.start_session(chain, focus, [])
    t_start = time.time()
    await asyncio.sleep(seconds)
    await hub.stop_session("cli done")
    starts = [d["t"] / 1000 for _, d in pr.scores]
    gaps = [b - a for a, b in zip(starts, starts[1:])]
    print(f"\n{len(starts)} scores in {time.time() - t_start:.0f}s · trades {pr.trades} · markers {len(pr.markers)}")
    if gaps:
        print(f"min gap between Jev call starts {min(gaps):.2f}s (must be ≥ 1.0) · mean {sum(gaps) / len(gaps):.2f}s")
        print(f"overlapping calls: {sum(1 for (_, a), (_, b) in zip(pr.scores, pr.scores[1:]) if b['t'] < a['t'] + a['latency_ms'])}")
    await jev.close()
    await cg.close()


if __name__ == "__main__":
    a = sys.argv[1:]
    asyncio.run(main(a[0] if a else "solana", int(a[1]) if len(a) > 1 else 60))
