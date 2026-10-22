#!/usr/bin/env python3
"""Rule-based, bounded policy tuner for the AI paper book.

Runs every 6h from autotrader (safe to run by hand). Each run is recorded in
policy.json `last_tune_check`, so a process restart does not tune again.

A change uses only positions closed since the previous adjustment (`last_tuned`),
counted once per position (partial sells are one round trip). Unknown human
scores are left out. No new eligible closes -> no size change.

Per tier, on that sample:
  n < 5            -> no change
  total PnL > 0 and win rate >= 40%   -> mult *= 1.10 (cap 1.5)
  total PnL < 0                       -> mult *= 0.85 (floor 0.10); if mult hits floor and n>=10 -> tier disabled
Time stop: among those same positions, if >=3 exited on a time stop,
  avg PnL > 0 -> +0.5h (cap 6h), avg PnL < 0 -> -0.5h (floor 1.5h).
Every change is appended to auto/policy_history.jsonl.
"""
import json, os, sqlite3, datetime as D
import os as _os
_ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
B = _ROOT
REAL_HUMAN = ("wallet data", "trade-pattern estimate")

def policy_path():
    return os.environ.get("MEMESCAN_POLICY") or f"{B}/auto/policy.json"

def db_path():
    return os.environ.get("MEMESCAN_AUTO_DB") or f"{B}/auto.db"

def _ts(s):
    if not s: return None
    try: return D.datetime.fromisoformat(s).timestamp()
    except Exception: return None

def round_trips(c):
    """Closed round trips. One row per buy, even when several sells followed it."""
    buys = [dict(r) for r in c.execute("select id, ca, ts, tier from trades where side='buy' and tier is not null order by id")]
    sells = [dict(r) for r in c.execute("select id, ca, ts, realized_pnl, source from trades where side='sell' and qty>0 order by id")]
    try:
        open_cas = {r[0] for r in c.execute("select ca from positions")}
    except Exception:
        open_cas = set()
    human = {}
    try:
        for r in c.execute("select buy_trade_id, human_source from trade_features where buy_trade_id is not null"):
            human[r["buy_trade_id"]] = r["human_source"]
    except Exception:
        human = {}
    by_ca_buys, by_ca_sells = {}, {}
    for b in buys: by_ca_buys.setdefault(b["ca"], []).append(b)
    for s in sells: by_ca_sells.setdefault(s["ca"], []).append(s)
    out = []
    for ca, bs in by_ca_buys.items():
        ss = by_ca_sells.get(ca) or []
        for i, b in enumerate(bs):
            nxt = bs[i + 1]["id"] if i + 1 < len(bs) else None
            mine = [s for s in ss if s["id"] > b["id"] and (nxt is None or s["id"] < nxt)]
            if not mine: continue
            if nxt is None and ca in open_cas: continue
            out.append({
                "buy_id": b["id"], "ca": ca, "tier": b["tier"], "closed_at": mine[-1]["ts"],
                "pnl": sum((s["realized_pnl"] or 0) for s in mine),
                "time_stop": any("time" in (s["source"] or "") for s in mine),
                "human_source": human.get(b["id"]),
            })
    return out

def eligible(trips, pol):
    """New closed positions with a measured human score.

    `tuned_buy_ids` are round trips already used in an adjustment. When
    `last_tuned` is set but that list is empty (older tuner runs), closes at
    or before `last_tuned` are treated as already used so they are not applied again.
    """
    watermark = _ts(pol.get("last_tuned"))
    seen = set(pol.get("tuned_buy_ids") or [])
    legacy = bool(pol.get("last_tuned")) and not seen
    fresh, measured = [], []
    for t in trips:
        if t["buy_id"] in seen: continue
        closed = _ts(t.get("closed_at"))
        if legacy and closed is not None and watermark is not None and closed <= watermark: continue
        fresh.append(t)
        if t.get("human_source") in REAL_HUMAN: measured.append(t)
    return fresh, measured

def apply_rules(pol, sample):
    """Mutate tier mults / time stop from `sample`. Returns the change list (possibly empty)."""
    st = {}
    for t in sample:
        s = st.setdefault(t["tier"], {"n": 0, "w": 0, "pnl": 0.0})
        s["n"] += 1; s["w"] += t["pnl"] > 0; s["pnl"] += t["pnl"]
    changes = []
    for tier, cfg in (pol.get("tiers") or {}).items():
        if not isinstance(cfg, dict) or "mult" not in cfg: continue
        s = st.get(tier)
        if not s or s["n"] < 5: continue
        old = cfg["mult"]
        if s["pnl"] > 0 and s["w"] / s["n"] >= 0.4: cfg["mult"] = round(min(1.5, old * 1.10), 3)
        elif s["pnl"] < 0:
            cfg["mult"] = round(max(0.10, old * 0.85), 3)
            if cfg["mult"] <= 0.10 and s["n"] >= 10: cfg["enabled"] = False
        if cfg["mult"] != old or not cfg.get("enabled", True):
            changes.append({"tier": tier, "old": old, "new": cfg["mult"], "enabled": cfg.get("enabled", True), **s})
    ts = [t["pnl"] for t in sample if t["time_stop"]]
    if len(ts) >= 3 and isinstance((pol.get("risk_overrides") or {}).get("time_stop"), dict):
        h = pol["risk_overrides"]["time_stop"].get("hours")
        if h is not None:
            avg = sum(ts) / len(ts)
            nh = min(6, h + 0.5) if avg > 0 else max(1.5, h - 0.5)
            if nh != h:
                pol["risk_overrides"]["time_stop"]["hours"] = nh
                changes.append({"time_stop_h": [h, nh], "avg": avg, "n": len(ts)})
    return changes, {str(k): v for k, v in st.items()}

def run(pol, trips, now=None):
    """One tuner pass. Always stamps last_tune_check. Adjusts only when >=5 new eligible closes exist."""
    now = now or D.datetime.now().astimezone()
    stamp = now.isoformat(timespec="seconds")
    fresh, sample = eligible(trips, pol)
    pol["last_tune_check"] = stamp
    if len(sample) < 5:
        if not fresh: reason = "no new closed positions"
        elif not sample: reason = "no new closed positions with a measured human score"
        else: reason = "fewer than 5 new closed positions"
        pol["last_stats"] = pol.get("last_stats") or {}
        return {"skipped": reason, "n": len(sample), "changes": [], "stats": pol.get("last_stats") or {}}
    changes, stats = apply_rules(pol, sample)
    pol["last_tuned"] = stamp
    pol["last_stats"] = stats
    ids = list(pol.get("tuned_buy_ids") or [])
    ids.extend(t["buy_id"] for t in sample if t["buy_id"] not in ids)
    pol["tuned_buy_ids"] = ids[-5000:]
    return {"skipped": None, "n": len(sample), "changes": changes, "stats": stats}

def main():
    path = policy_path()
    pol = json.load(open(path))
    c = sqlite3.connect(f"file:{db_path()}?mode=ro", uri=True, timeout=10)
    c.row_factory = sqlite3.Row
    try:
        trips = round_trips(c)
    except Exception:
        trips = []
    c.close()
    result = run(pol, trips)
    json.dump(pol, open(path, "w"), indent=1)
    if result["changes"]:
        hist = os.path.join(os.path.dirname(path), "policy_history.jsonl")
        open(hist, "a").write(json.dumps({"at": pol["last_tuned"], "changes": result["changes"]}) + "\n")
    print(json.dumps({"changes": result["changes"], "skipped": result["skipped"], "n": result["n"], "stats": result["stats"]}))

if __name__ == "__main__":
    main()
