#!/usr/bin/env python3
"""Rule-based, bounded policy tuner for the AI book (runs every 6h from autotrader; safe to run by hand).
Per tier, using CLOSED round-trips in auto.db (buy tier -> realized PnL of its sells):
  n < 5            -> no change
  total PnL > 0 and win rate >= 40%   -> mult *= 1.10 (cap 1.5)
  total PnL < 0                       -> mult *= 0.85 (floor 0.10); if mult hits floor and n>=10 -> tier disabled
Stop-loss: if >=60% of SL exits recovered (price later >1.2x the SL fill) can't be known offline -> SL untouched.
Time stop: if avg PnL of time-stop exits > 0 -> +0.5h (cap 6h), if < 0 -> -0.5h (floor 1.5h).
Every change is appended to auto/policy_history.jsonl."""
import json, sqlite3, datetime as D
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
B = _ROOT; P = f"{B}/auto/policy.json"
def main():
    pol = json.load(open(P)); c = sqlite3.connect(f"file:{B}/auto.db?mode=ro", uri=True, timeout=10); c.row_factory = sqlite3.Row
    tier_of = {r["ca"]: r["tier"] for r in c.execute("select ca, tier from trades where side='buy' and tier is not null")}
    st = {}
    for r in c.execute("select ca, realized_pnl, source from trades where side='sell' and qty>0"):
        t = tier_of.get(r["ca"]); s = st.setdefault(t, {"n": 0, "w": 0, "pnl": 0.0}); s["n"] += 1; s["w"] += (r["realized_pnl"] or 0) > 0; s["pnl"] += r["realized_pnl"] or 0
    ts = [r[0] or 0 for r in c.execute("select realized_pnl from trades where side='sell' and qty>0 and source like '%time%'")]
    changes = []
    for t, cfg in pol["tiers"].items():
        s = st.get(t)
        if not s or s["n"] < 5: continue
        old = cfg["mult"]
        if s["pnl"] > 0 and s["w"] / s["n"] >= 0.4: cfg["mult"] = round(min(1.5, old * 1.10), 3)
        elif s["pnl"] < 0:
            cfg["mult"] = round(max(0.10, old * 0.85), 3)
            if cfg["mult"] <= 0.10 and s["n"] >= 10: cfg["enabled"] = False
        if cfg["mult"] != old or not cfg["enabled"]: changes.append({"tier": t, "old": old, "new": cfg["mult"], "enabled": cfg["enabled"], **s})
    if len(ts) >= 3:
        h = pol["risk_overrides"]["time_stop"]["hours"]; avg = sum(ts) / len(ts)
        nh = min(6, h + 0.5) if avg > 0 else max(1.5, h - 0.5)
        if nh != h: pol["risk_overrides"]["time_stop"]["hours"] = nh; changes.append({"time_stop_h": [h, nh], "avg": avg})
    pol["last_tuned"] = D.datetime.now().astimezone().isoformat(timespec="seconds"); pol["last_stats"] = st and {str(k): v for k, v in st.items()}
    json.dump(pol, open(P, "w"), indent=1)
    if changes: open(f"{B}/auto/policy_history.jsonl", "a").write(json.dumps({"at": pol["last_tuned"], "changes": changes}) + "\n")
    print(json.dumps({"changes": changes, "stats": pol["last_stats"]}))
if __name__ == "__main__": main()
