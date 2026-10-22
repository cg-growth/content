#!/usr/bin/env python3
"""Create every local database + runtime file with an empty schema. Idempotent, needs no API keys, makes no network calls."""
import json, os, subprocess, sys
ROOT = os.environ.get("MEMESCAN_HOME") or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["MEMESCAN_HOME"] = ROOT
for d in ("logs", "research", "cards", "xfirst/inbox", "xfirst/runs"): os.makedirs(os.path.join(ROOT, d), exist_ok=True)
def jinit(rel, obj):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p): json.dump(obj, open(p, "w"), indent=1); print("created", rel)
jinit("state.json", {"version": 1, "last_run": None, "assessed": {}, "pending": []})
jinit("xfirst/queue.json", [])
jinit("pending_research.json", {"updated_at": None, "items": []})
STEPS = {
 "paper.db (human book)": "import core, common as C, clips as CL; c = core.db(); C.pinit(c); CL.init(c); c.close()",
 "auto.db (AI book)":     "import autotrader; autotrader.adb().close()",
 "market.db":             "import common as C; C.mdb().close()",
 "wallets.db":            "import walletdb; walletdb.conn().close()",
 "ticks.db":              "import ticks; ticks._tdb().close()",
 "scout.db":              "import scout; scout._db().close()",
 "fwdq.db":               "import fwdq; fwdq._c().close()",
}
path = os.pathsep.join([ROOT, f"{ROOT}/lib", f"{ROOT}/telegram", f"{ROOT}/auto"])
env = {**os.environ, "PYTHONPATH": path + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else "")}
ok = True
for name, code in STEPS.items():
    e = dict(env)
    if name.startswith("paper"): e["PAPER_DB"] = f"{ROOT}/paper.db"
    r = subprocess.run([sys.executable, "-c", code], env=e, capture_output=True, text=True, cwd=ROOT)
    if r.returncode: ok = False; print(f"FAILED {name}: {(r.stderr.strip().splitlines() or ['?'])[-1]}", file=sys.stderr)
    else: print("ok", name)
sys.exit(0 if ok else 1)
