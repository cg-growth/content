#!/usr/bin/env python3
"""Read-only memecoin scanner dashboard (stdlib only)."""
import json, os, re, sys, sqlite3, http.server, socketserver
from urllib.parse import urlparse, parse_qs
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
def _utm_q(placement):
    import sys as _sy; _sy.path.insert(0, _ROOT + "/lib"); import utm
    return utm.query(placement, "grokbot") if os.environ.get("MEMESCAN_UTM", "1") != "0" else ""
BASE = _ROOT; DB = f"{BASE}/wallets.db"; HERE = os.path.dirname(os.path.abspath(__file__))
def q(sql, args=()):
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=5); c.row_factory = sqlite3.Row
    try: return [dict(r) for r in c.execute(sql, args)]
    finally: c.close()
def state():
    try: return json.load(open(f"{BASE}/state.json"))
    except Exception: return {}
def tokens():
    out = []
    for k, v in (state().get("assessed") or {}).items():
        net, _, pool = k.partition("_"); d = dict(v); d["network"] = net; d["pool"] = pool
        m = re.search(r"human[^0-9]{0,20}(\d{1,3})", json.dumps(v), re.I)
        d["human_score"] = v.get("human_score", int(m.group(1)) if m else None)
        d["src"] = "x-first" if str(v.get("source") or "").lower().startswith("x") else "cg-first"; out.append(d)
    return sorted(out, key=lambda x: x.get("at", ""), reverse=True)
def runs():
    try: txt = open(f"{BASE}/log.md").read()
    except Exception: txt = ""
    rs = []
    for m in re.finditer(r"^## (\S+)(.*)$", txt, re.M):
        body = txt[m.end():].split("\n## ")[0]
        r = re.search(r"(\d+) Organic [Hh]ype / (\d+) Watch / (\d+) Discard", body)
        xr = re.search(r"X-first:\s*(\d+)", body)
        rs.append({"at": m.group(1), "kind": m.group(2).strip(), "xfirst": int(xr.group(1)) if xr else 0, "organic": int(r.group(1)) if r else 0,
                   "watch": int(r.group(2)) if r else 0, "discard": int(r.group(3)) if r else 0})
    return rs, txt
def _plan():
    try:
        sys.path.insert(0, _ROOT + "/lib"); import plan_tips, cgtier, utm
        t = cgtier.current(); _on, off = cgtier.feature_summary(t)
        import usage
        snap = usage.cached() or {}
        return {"tier": t, "label": cgtier.plan_label(t), "unavailable": off, "note": cgtier.unavailable(t) if off else "",
                "calls_month": plan_tips.C.month_calls(), "tips": plan_tips.enabled(),
                "text": plan_tips.status_text(), "usage": snap,
                "pricing": utm.pricing("dashboard-plan", source="grokbot") if os.environ.get("MEMESCAN_UTM", "1") != "0" else "https://www.coingecko.com/en/api/pricing"}
    except Exception as e:
        return {"tier": None, "error": str(e)}
def api(path, qs):
    if path == "/api/overview":
        t = tokens(); rs, _ = runs(); st = state()
        return {"wallets_by_label": q("select coalesce(label,'unknown') label,count(*) n from wallets group by 1 order by 2 desc"),
                "totals": {"wallets": q("select count(*) n from wallets")[0]["n"], "sightings": q("select count(*) n from sightings")[0]["n"],
                           "clusters": q("select count(*) n from clusters")[0]["n"], "tokens": len(t), "runs": len(rs),
                           "pending": len(st.get("pending") or {}), "last_run": st.get("last_run")},
                "sources": {sname: sum(1 for x in t if x.get("src") == sname) for sname in ("cg-first", "x-first")},
                "verdicts": {v: sum(1 for x in t if (x.get("verdict") or "").lower().replace(" ", "_") == v) for v in ["organic_hype", "watch", "scout", "discard"]},
                "runs": rs, "plan": _plan()}
    if path == "/api/wallets": return q("select * from wallets order by coalesce(realized_pnl,0) desc")
    if path == "/api/wallet":
        a = qs.get("address", [""])[0]; w = q("select * from wallets where address=?", (a,))
        cl = [c for c in q("select * from clusters") if a.lower() in (c["members"] or "").lower()]
        return {"wallet": w[0] if w else None, "sightings": q("select * from sightings where address=? order by seen_at desc", (a,)), "clusters": cl}
    if path == "/api/tokens": return tokens()
    if path == "/api/clusters":
        cs = q("select * from clusters order by created_at desc")
        for c in cs:
            try: c["members"] = json.loads(c["members"])
            except Exception: c["members"] = [c["members"]]
        return cs
    if path == "/api/log": return {"log": runs()[1], "pending": state().get("pending")}
    if path == "/api/paper": return paper()
    if path in ("/api/auto", "/api/compare"):   # AI autonomous book (read-only views over auto.db / paper.db)
        sys.path.insert(0, _ROOT + "/auto"); import book, sqlite3 as _s
        if path == "/api/compare": return {k: {x: y for x, y in book.stats(k).items() if x != "positions"} for k in ("human", "auto")}
        st = book.stats("auto")
        try:
            c = book.ro("auto"); st["trades_list"] = [dict(r) for r in c.execute("select ts,side,symbol,network,usd_notional,realized_pnl,tier,source,rationale from trades order by id desc limit 60")]
            st["notices"] = [dict(r) for r in c.execute("select ts,text from notices order by id desc limit 20")]; c.close()
        except Exception as e: st["trades_list"] = []; st["notices"] = []
        try: st["policy"] = json.load(open(_ROOT + "/auto/policy.json"))
        except Exception: st["policy"] = {}
        return st
    if path == "/api/live": return live()
    return None
_QC = {}
def _px(ca, net):
    import sys, time; sys.path.insert(0, f"{BASE}/telegram"); import core
    k = (ca, net); hit = _QC.get(k)
    if hit and time.time() - hit[0] < 60: return hit[1]
    try: q = core.quote(ca, net); p = q["price"] if q else None
    except Exception: p = None
    _QC[k] = (time.time(), p); return p
def _ro(db):
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5); c.row_factory = sqlite3.Row; return c
def live():
    import time
    m = _ro(f"{BASE}/market.db"); p = _ro(f"{BASE}/paper.db"); out = {}
    try:
        st = m.execute("select v,at from kv where k='stream_status'").fetchone(); out["stream"] = dict(json.loads(st["v"]), at=st["at"]) if st else None
        out["credits"] = [dict(r) for r in m.execute("select * from credits order by day desc limit 14")]
        plans = {r["ca"]: dict(r) for r in p.execute("select * from risk_plans")} if p.execute("select 1 from sqlite_master where name='risk_plans'").fetchone() else {}
        pos = []
        for r in p.execute("select * from positions"):
            d = dict(r); pr = m.execute("select p,r,t from prices where ta=? order by t desc limit 1", (r["ca"],)).fetchone()
            d["price"] = pr["p"] if pr else None; d["reserve"] = pr["r"] if pr else None; d["px_age"] = round(time.time() - pr["t"]) if pr else None
            try:
                import liquidity as L
                mk = L.mark(d.get("qty"), d["price"], d["reserve"], r["network"]) if d["price"] is not None else {}
                d["liq_status"] = mk.get("status") or ""
            except Exception: d["liq_status"] = ""
            d["plan"] = plans.get(r["ca"]); 
            if d["plan"]: d["plan"]["tp"] = json.loads(d["plan"]["tp"]); d["plan"]["notes"] = json.loads(d["plan"]["notes"] or "{}")
            d["n_1s"] = m.execute("select count(*) from ohlcv where pool=? and iv='1s' and t>?", (r["pool"], time.time() - 600)).fetchone()[0]
            d["n_trades_10m"] = m.execute("select count(*) from trades where pool=? and t>?", (r["pool"], time.time() - 600)).fetchone()[0]
            pos.append(d)
        out["positions"] = pos
        has = lambda t: p.execute("select 1 from sqlite_master where name=?", (t,)).fetchone()
        out["events"] = [dict(r) for r in p.execute("select * from risk_events order by id desc limit 25")] if has("risk_events") else []
        out["prompts"] = [dict(r) for r in p.execute("select * from risk_prompts order by id desc limit 10")] if has("risk_prompts") else []
        out["decisions"] = [dict(r) for r in p.execute("select * from decisions order by id desc limit 20")] if has("decisions") else []
        out["outcomes"] = [dict(r) for r in p.execute("select * from outcomes order by alerted_at desc limit 20")] if has("outcomes") else []
        out["discoveries"] = [dict(r) for r in m.execute("select key,symbol,network,stage,reason,score,seen_at from discoveries where stage!='recheck' order by seen_at desc limit 30")] if m.execute("select 1 from sqlite_master where name='discoveries'").fetchone() else []
        svc = {}
        for n in ("stream", "risk", "discovery", "tracker", "supervise"):
            f = f"{BASE}/logs/{n}.log"; svc[n] = round(time.time() - os.path.getmtime(f)) if os.path.exists(f) else None
        f = f"{BASE}/telegram/daemon.log"; svc["telegram"] = round(time.time() - os.path.getmtime(f)) if os.path.exists(f) else None
        out["services"] = svc; out["risk"] = json.load(open(f"{BASE}/risk.json"))
    finally: m.close(); p.close()
    return out
def paper():
    P = f"{BASE}/paper.db"
    if not os.path.exists(P): return {"empty": True}
    c = sqlite3.connect(f"file:{P}?mode=ro", uri=True, timeout=5); c.row_factory = sqlite3.Row
    try:
        g = lambda sql: [dict(r) for r in c.execute(sql)]
        sys.path.insert(0, _ROOT + "/lib"); import bankroll
        cash = (g("select v from account where k='cash'") or [{"v": bankroll.configured()}])[0]["v"]
        start = bankroll.baseline(c)
        pos = g("select * from positions order by opened_at")
        sys.path.insert(0, _ROOT + "/lib"); import liquidity as L
        for p in pos:
            q = None
            try:
                sys.path.insert(0, _ROOT + "/telegram"); import core
                q = core.cached_quote(p["ca"], p["network"])
            except Exception: q = None
            px = q.get("price") if q else _px(p["ca"], p["network"])
            liq = L.cached_pool_reserve(p["ca"], p["pool"])
            if liq is None and q: liq = q.get("liquidity")
            mk = L.mark(p["qty"], px, liq, p["network"])
            p["price"] = px; p["value"] = mk["value"]; p["liq_status"] = mk.get("status") or ""
            p["unrealized"] = (p["value"] - p["cost_usd"]) if p["value"] is not None else None
        trades = g("select * from trades order by id desc")
        sells = [t for t in trades if t["side"] == "sell"]
        bytag = {}
        for t in sells:
            k = (t["tag"] or "untagged"); b = bytag.setdefault(k, {"tag": k, "n": 0, "wins": 0, "pnl": 0.0})
            b["n"] += 1; b["wins"] += (t["realized_pnl"] or 0) > 0; b["pnl"] += t["realized_pnl"] or 0
        pv = sum(p["value"] if p["value"] is not None else p["cost_usd"] for p in pos)
        return {"cash": cash, "positions_value": pv, "equity": cash + pv, "start": start,
                "realized": sum(t["realized_pnl"] or 0 for t in sells), "unrealized": sum(p["unrealized"] or 0 for p in pos),
                "win_rate": (sum((t["realized_pnl"] or 0) > 0 for t in sells) / len(sells)) if sells else None,
                "positions": pos, "trades": trades, "closed": sells, "by_tag": list(bytag.values()),
                "snapshots": g("select ts, equity from snapshots order by ts")}
    finally: c.close()
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, code, body, ct):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code); self.send_header("Content-Type", ct); self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        u = urlparse(self.path)
        try:
            if u.path in ("/", "/index.html"):
                page = open(f"{HERE}/index.html", "rb").read()
                page = page.replace(b"__UTM_DASHBOARD__", _utm_q("dashboard-pool").encode())
                page = page.replace(b"__UTM_TOKEN__", _utm_q("dashboard-token").encode())
                page = page.replace(b"__UTM_FOOTER__", _utm_q("dashboard-attribution").encode())
                return self.send(200, page, "text/html; charset=utf-8")
            if u.path == "/health": return self.send(200, "ok", "text/plain")
            r = api(u.path, parse_qs(u.query))
            if r is None: return self.send(404, '{"error":"not found"}', "application/json")
            self.send(200, json.dumps(r, default=str), "application/json")
        except Exception as e: self.send(500, json.dumps({"error": str(e)}), "application/json")
class S(socketserver.ThreadingMixIn, http.server.HTTPServer): daemon_threads = True; allow_reuse_address = True
if __name__ == "__main__":
    S((os.environ.get("DASHBOARD_HOST", "127.0.0.1"), int(os.environ.get("PORT", 8787))), H).serve_forever()
