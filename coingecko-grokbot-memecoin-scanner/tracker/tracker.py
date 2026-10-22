#!/usr/bin/env python3
"""Outcome tracker (price at 1h/6h/24h + max for every alert, bought or skipped) + daily 21:00 local-time (MEMESCAN_TZ) recap image. TRACKER_DRY=1 -> no TG."""
import datetime as D, json, os, sys, time
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
sys.path.insert(0, _ROOT + "/lib"); sys.path.insert(0, _ROOT + "/alerts")
import common as C, core
log = C.logger("tracker"); DRY = os.environ.get("TRACKER_DRY") == "1"; mc = C.mdb()
def px(net, ca):
    d = C.cg(f"/simple/networks/{net}/token_price/{ca}", None, mc)
    v = (((d or {}).get("data") or {}).get("attributes", {}).get("token_prices") or {}).get(ca)
    return float(v) if v else None
def outcomes():
    c = C.pinit(core.db()); n = 0
    for r in c.execute("select * from outcomes where px_24h is null").fetchall():
        age = time.time() - D.datetime.fromisoformat(r["alerted_at"]).timestamp(); p = px(r["network"], r["ca"]); n += 1
        if p is None: continue
        upd = {"max_px": max(r["max_px"] or 0, p)}
        if r["alert_px"] is None: upd["alert_px"] = p
        base = r["alert_px"] or p
        for h, col in ((1, "1h"), (6, "6h"), (24, "24h")):
            if age >= h * 3600 and r[f"px_{col}"] is None: upd[f"px_{col}"] = p; upd[f"ret_{col}"] = p / base - 1
        if r["decision"] == "pending" and age > 3600: upd["decision"] = "ignored"
        c.execute("update outcomes set " + ",".join(f"{k}=?" for k in upd) + " where ca=? and alerted_at=?", (*upd.values(), r["ca"], r["alerted_at"])); c.commit()   # short txn: never hold the write lock across network calls
    c.commit(); c.close(); return n
def hit_rates(c=None):
    """Per alert tier (Organic Hype / Watch / Scout): n, hit = max price >= 1.5x alert price, avg 1h/24h return."""
    c = c or C.pinit(core.db()); out = {}
    for r in c.execute("select tag, alert_px, max_px, ret_1h, ret_24h from outcomes where alert_px > 0"):
        t = (r["tag"] or "?").split()[0].rstrip("?").capitalize(); o = out.setdefault(t, {"n": 0, "hit": 0, "r1": [], "r24": []}); o["n"] += 1
        if (r["max_px"] or 0) >= 1.5 * r["alert_px"]: o["hit"] += 1
        if r["ret_1h"] is not None: o["r1"].append(r["ret_1h"])
        if r["ret_24h"] is not None: o["r24"].append(r["ret_24h"])
    return {t: {"n": o["n"], "hit_rate": round(o["hit"] / o["n"], 3) if o["n"] else None, "avg_1h": round(sum(o["r1"]) / len(o["r1"]), 3) if o["r1"] else None,
                "avg_24h": round(sum(o["r24"]) / len(o["r24"]), 3) if o["r24"] else None} for t, o in out.items()}
def recap():
    import portfolio as P
    path, cap = P.render(f"{C.BASE}/cards/recap_{C.today()}.png", "Daily recap"); cap += P.recap_text()
    cr = dict(mc.execute("select kind,n from credits where day=?", (C.today(),)).fetchall())
    hr = hit_rates(); cap += "\nHit rate (≥1.5x): " + " · ".join(f"{t} {(v['hit_rate'] or 0)*100:.0f}% of {v['n']}" for t, v in hr.items())
    cap += f"\nCredits today: REST {cr.get('rest',0):,.0f} · WS {cr.get('ws',0):,.1f}"
    if DRY: log("DRY recap", path, cap.replace("\n", " | ")); return
    own = core.owner(); r = P.send_photo(own["chat_id"], path, cap); log("recap sent", r.get("ok"))
def main():
    log("start", "DRY" if DRY else "RUN (paper)"); last_o = 0; beat = 0
    while True:
        try:
            if time.time() - last_o > 300: n = outcomes(); last_o = time.time()
            t = D.datetime.now(C.MYT); done = C.kv_get(mc, "recap_day")
            if t.hour == 21 and done != C.today(): recap(); C.kv_set(mc, "recap_day", C.today()); mc.commit()
        except Exception as e: log("err", C.redact(e))
        if time.time() - beat > 60: log("heartbeat"); beat = time.time()
        time.sleep(20)
if __name__ == "__main__":
    if "--recap-now" in sys.argv: recap()
    elif "--stats" in sys.argv: print(json.dumps(hit_rates(), indent=1))
    elif "--once" in sys.argv: print("outcomes checked", outcomes())
    else: main()
