#!/usr/bin/env python3
"""Safe writers for the scanner routines (file lock + atomic replace).
  assess.py record <network> <ca>  < record.json   merge a verdict into state.json["assessed"]["<network>_<ca>"]
       fields used by the dashboard / AI book: token (symbol), name, pool, verdict ("Organic Hype"|"Watch"|"Scout"|"discard"),
       confidence ("low"|"high"), score, human_score, rule (one-line reason), source ("discovery"|"x-first"), x_ca_authors,
       metrics{liq,fdv,age_min,h1_change,buyers_h1}, gt (GeckoTerminal link)
  assess.py log  < text.md                          append a run summary to log.md (dashboard parses it)
  assess.py get <network> <ca>                      print an existing record (or null)"""
import fcntl, json, os, sys, datetime
ROOT = os.environ.get("MEMESCAN_HOME") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT + "/lib"); import addr as A, localtz
ST, LOCK = f"{ROOT}/state.json", f"{ROOT}/state.json.lock"
def now(): return datetime.datetime.now(localtz.LOCAL_TZ).isoformat(timespec="seconds")
def _load():
    try: return json.load(open(ST))
    except Exception: return {"version": 1, "last_run": None, "assessed": {}, "pending": []}
def record(net, ca, rec):
    ca = A.norm(ca, net); key = f"{net}_{ca}"
    with open(LOCK, "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        s = _load(); old = s.setdefault("assessed", {}).get(key) or {}
        s["assessed"][key] = {**old, **rec, "ca": ca, "network": net, "at": rec.get("at") or now()}; s["last_run"] = now()
        json.dump(s, open(ST + ".tmp", "w"), indent=1, ensure_ascii=False); os.replace(ST + ".tmp", ST)
    return key
if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["record"] and len(a) == 3: print("recorded", record(a[1], a[2], json.load(sys.stdin)))
    elif a[:1] == ["log"]: open(f"{ROOT}/log.md", "a").write(f"\n## {now()}\n" + sys.stdin.read().strip() + "\n"); print("logged")
    elif a[:1] == ["get"] and len(a) == 3: print(json.dumps(_load().get("assessed", {}).get(f"{a[1]}_{A.norm(a[2], a[1])}")))
    else: sys.exit(__doc__)
