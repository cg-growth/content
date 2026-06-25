import json
from pathlib import Path
from fetch_new_pools import fetch_new_pools

SEEN_PATH = Path("seen_pools.json")

def send_alert(pool):
    print(f"NEW: {pool['symbol']} on {pool['network']} — ${pool['reserve_usd']:,.0f}")

seen = set(json.loads(SEEN_PATH.read_text())) if SEEN_PATH.exists() else set()

for pool in fetch_new_pools():
    key = f"{pool['network_id']}:{pool['address']}"
    if key in seen:
        continue
    send_alert(pool)
    seen.add(key)

SEEN_PATH.write_text(json.dumps(sorted(seen)))
