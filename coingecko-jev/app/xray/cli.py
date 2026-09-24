"""Dry-run: python -m app.xray.cli base [token_address]"""
import asyncio
import sys
from collections import Counter

from ..cg_rest import CGRest
from ..jev import Jev
from .profiler import WalletProfiler
from .service import XrayService


async def main(chain="base", token=None):
    cg, jev = CGRest(), Jev()
    svc = XrayService(cg, jev, WalletProfiler(cg, jev))
    if not token:
        pools, _ = await cg.trending_pools(chain, "1h", 5)
        token = pools[0]["relationships"]["base_token"]["data"]["id"].split("_", 1)[1]
    personas = Counter()
    async for ev, p in svc.run(chain, token):
        if ev == "start":
            t = p["token"]
            print(f"{t['symbol']} ({t['name']}) on {t['chain_label']} · {p['total']} wallets · pool {t['pool_name']}")
        elif ev == "wallet":
            if "error" in p:
                print("  ERROR", p["address"][:10], p["error"])
                continue
            personas[p["persona_label"]] += 1
            t = p["token"]
            if p.get("scored"):
                print(f"  {p['short']:14} {p['source']:15} {p['persona_label']:18} skill {p['skill']:5.1f} insider {p['insider']:.2f} copy {p['copyable']:.2f} "
                      f"{p['stance']:12} sup {t.get('supply_share_pct') or 0:6.2f}% pnl {((t.get('realized_pnl_usd') or 0) + (t.get('unrealized_pnl_usd') or 0)):>12,.0f} "
                      f"life {p['lifetime'].get('lifetime_realized_pnl_usd') or 0:>14,.0f} win {p['lifetime'].get('win_rate_tokens')} tpd {p['recent_activity'].get('recent_trades_per_day')} {p.get('label') or ''}")
            else:
                print(f"  {p['short']:14} {p['source']:15} {p['persona_label']:18} sup {t.get('supply_share_pct') or 0:6.2f}% {p.get('label') or ''}")
        elif ev == "verdict":
            print("\nAGGREGATE", {k: v for k, v in p["aggregate"].items() if k != "composition"})
            print("VERDICT", p["verdict"])
        elif ev == "done":
            print(f"DONE {p['elapsed_ms']} ms · Jev calls {p['calls']} · ${p['cost_usd']:.4f} · CG calls {p['cg_calls']}")
    print("personas:", dict(personas))
    await jev.close()
    await cg.close()


if __name__ == "__main__":
    a = sys.argv[1:]
    asyncio.run(main(a[0] if a else "base", a[1] if len(a) > 1 else None))
