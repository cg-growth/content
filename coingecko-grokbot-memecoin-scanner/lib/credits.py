#!/usr/bin/env python3
"""Estimate demo-tier credit use from the repeating discovery calls. Informational only.

The scanner does not change discovery.interval_s. The owner keeps the interval or picks another.

Each onchain REST call counts as 1 credit. Listing calls are what discovery.py issues every cycle.
research_per_cycle is the measured average of follow-up reads on the demo tier (token info, pool trades,
and similar) when four networks are scanned. A run on 22 Oct 2026 at a 60 second interval used
about 17 credits per cycle: 8 listing calls plus 9 research calls.
"""
import sys
import os as _os
_ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
sys.path.insert(0, _ROOT + "/lib")
import cgtier

# Pricing page, demo tier, checked 22 Oct 2026.
DEMO_MONTHLY_CREDITS = 10000
# Listing: one new-pools call per network, plus one trending-pools call per network when Megafilter is off.
LISTING = {"new_pools_per_network": 1, "trending_pools_per_network": 1}
MEGAFILTER_PER_CYCLE = 1
# Measured follow-up credits at 4 networks. Other network counts scale from this.
RESEARCH_AT_NETWORKS = 4
RESEARCH_CREDITS = 9


def cycle_credits(n_networks, megafilter=False):
    n = max(0, int(n_networks))
    if n == 0: return 0.0
    research = RESEARCH_CREDITS * (n / RESEARCH_AT_NETWORKS)
    if megafilter:
        listing = n * LISTING["new_pools_per_network"] + MEGAFILTER_PER_CYCLE
    else:
        listing = n * (LISTING["new_pools_per_network"] + LISTING["trending_pools_per_network"])
    return listing + research


def estimate(interval_s, n_networks, monthly=DEMO_MONTHLY_CREDITS, megafilter=False):
    interval_s = max(1.0, float(interval_s))
    per_cycle = cycle_credits(n_networks, megafilter)
    per_day = per_cycle * (86400.0 / interval_s)
    days = (monthly / per_day) if per_day else None
    return {
        "per_cycle": per_cycle,
        "per_minute": per_cycle * (60.0 / interval_s),
        "per_day": per_day,
        "days": days,
        "hours": None if days is None else days * 24,
        "monthly": monthly,
        "interval_s": interval_s,
        "networks": int(n_networks),
    }


def _span(days):
    if days is None: return "an unknown time"
    if days >= 1: return f"{days:.1f} days"
    return f"{days:.1f} days (about {days * 24:.0f} hours)"


def sentence(interval_s, n_networks, monthly=DEMO_MONTHLY_CREDITS, megafilter=False):
    e = estimate(interval_s, n_networks, monthly, megafilter)
    return (f"At these settings the scanner uses about {e['per_day']:,.0f} credits a day, "
            f"so your {int(e['monthly']):,} monthly {cgtier.PLAN_LABELS['demo']} credits last about {_span(e['days'])}. "
            "You can keep this interval or set a slower one. The scanner does not change it.")


def from_config():
    import common as C
    k = C.risk_cfg().get("discovery") or {}
    interval = k.get("interval_s") or 60
    nets = k.get("networks") or []
    mega = False
    try:
        mega = bool(C.cg_has("megafilter"))
    except Exception:
        mega = False
    return sentence(interval, len(nets), megafilter=mega)


def main(argv=None):
    print(from_config())
    return 0


if __name__ == "__main__":
    sys.exit(main())
