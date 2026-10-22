#!/usr/bin/env python3
"""/report Report Card image: realized/unrealized, stats, open + closed tables, by tag / decision source. PAPER."""
import datetime as D, json, sys, time, os
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
sys.path.insert(0, _ROOT + "/lib"); sys.path.insert(0, _ROOT + "/alerts"); sys.path.insert(0, _ROOT + "/telegram")
import common as C, core, pf_html as H
esc = H.esc; GR, RD, OR, MU, AC = H.GR, H.RD, H.OR, H.MU, H.AC
def reason(src):
    s = (src or "").lower()
    if "illiquid" in s or "rugged" in s: return "ILLIQUID"
    if s.startswith("risk-"):
        k = s[5:]
        if "trail" in k: return "TRAIL"
        if k.startswith("sl") or "stop" in k: return "SL"
        if "tp" in k: return "TP"
        if "time" in k: return "TIME"
        return "DANGER"
    if s == "tp-confirm": return "TP"
    return "MANUAL"
def ts(x): return D.datetime.fromisoformat(x).timestamp()
def hold(sec):
    sec = max(0, int(sec)); d, r = divmod(sec, 86400); h, r = divmod(r, 3600); m = r // 60
    return f"{d}d {h}h" if d else (f"{h}h {m}m" if h else f"{m}m")
def closed_trades(c):
    """One row per sell, paired with the cost basis of the buys before it (round-trip legs)."""
    out = []; book = {}
    for t in c.execute("select * from trades order by id"):
        b = book.setdefault(t["ca"], {"qty": 0.0, "cost": 0.0, "first": t["ts"], "tag": t["tag"], "src": t["source"]})
        if t["side"] == "buy":
            if b["qty"] <= 1e-12: b.update(qty=0.0, cost=0.0, first=t["ts"], tag=t["tag"], src=t["source"])
            b["qty"] += t["qty"] or 0; b["cost"] += t["usd_notional"] or 0
        else:
            if not (t["qty"] or 0) and not (t["usd_notional"] or 0): continue   # voided by audit correction (see trade_audit)
            q = t["qty"] or 0; basis = b["cost"] * (q / b["qty"]) if b["qty"] else 0
            pnl = t["realized_pnl"] or 0; entry = b["cost"] / b["qty"] if b["qty"] else 0
            out.append(dict(symbol=t["symbol"] or "?", network=t["network"], entry=entry, exit=t["fill_price"], held=ts(t["ts"]) - ts(b["first"]),
                            pnl=pnl, pct=pnl / basis * 100 if basis else 0, why=reason(t["source"]), tag=b["tag"] or "—", src=b["src"] or "—", at=t["ts"]))
            b["qty"] -= q; b["cost"] -= basis
    return out
def srcname(s):
    s = (s or "").lower()
    if s.startswith("button"): return "Button"
    if s.startswith("nl-voice"): return "Voice"
    if s.startswith("nl"): return "Natural lang."
    if s.startswith("cmd"): return "Command"
    return s or "—"
def data():
    c = C.pinit(core.db()); rows = core.mtm(c); cs = core.cash(c)
    plans = {r["ca"]: dict(r) for r in c.execute("select * from risk_plans")}
    first = {r["ca"]: r["source"] for r in c.execute("select ca,source,min(id) from trades where side='buy' group by ca")}
    tp_ = C.risk_cfg()["trailing_stop"]["trail_pct"]
    op = []
    for r in rows:
        pl = plans.get(r["ca"]); px = r["price"]; entry = (pl or {}).get("entry_px") or (r["cost_usd"] / r["qty"] if r["qty"] else 0)
        u = r["unrealized"] or 0; st = []
        if pl:
            st.append(f'SL {(pl["sl_px"]/entry-1)*100:+.0f}%')
            tps = sorted(t["multiple"] for t in json.loads(pl["tp"] or "[]") if t["status"] == "open")
            if tps: st.append(f"TP {tps[0]:.2f}x")
            if pl["trail_active"] and pl["peak_px"]: st.append(f'TRAIL {(pl["peak_px"]*(1-tp_/100)/entry):.2f}x')
            if not pl["auto"]: st.append("AUTO OFF")
        if r.get("liq_status"): st.append(r["liq_status"])
        op.append(dict(symbol=r["symbol"] or "?", network=r["network"], entry=entry, now=px, cost=r["cost_usd"],
                       value=r["value"] if r["value"] is not None else r["cost_usd"], u=u, pct=u / r["cost_usd"] * 100 if r["cost_usd"] else 0,
                       st=st, tag=r["entry_tag"] or "—", src=first.get(r["ca"])))
    cl = closed_trades(c); c.close()
    re_ = sum(x["pnl"] for x in cl); un = sum(x["u"] for x in op)
    W = [x["pnl"] for x in cl if x["pnl"] > 0]; L = [x["pnl"] for x in cl if x["pnl"] <= 0]
    def grp(key):
        g = {}
        for x in cl: e = g.setdefault(key(x), [0, 0, 0.0, 0.0]); e[0] += 1; e[1] += x["pnl"] > 0; e[2] += x["pnl"]
        for x in op: e = g.setdefault(key(x), [0, 0, 0.0, 0.0]); e[3] += x["u"]
        return sorted(g.items(), key=lambda kv: -(kv[1][2] + kv[1][3]))
    return dict(op=op, cl=cl, re=re_, un=un, cash=cs, eq=cs + sum(x["value"] for x in op), W=W, L=L,
                wr=len(W) / len(cl) * 100 if cl else None, aw=sum(W) / len(W) if W else None, al=sum(L) / len(L) if L else None,
                pf=(sum(W) / abs(sum(L))) if L and sum(L) else (float("inf") if W else None),
                best=max(cl, key=lambda x: x["pnl"]) if cl else None, worst=min(cl, key=lambda x: x["pnl"]) if cl else None,
                bytag=grp(lambda x: x["tag"]), bysrc=grp(lambda x: srcname(x["src"])))
def _m(v, s=True): return "—" if v is None else H.money(v, s)
def _c(v): return MU if v is None else (GR if v >= 0 else RD)
def chip(t, col): return f'<span class="chip" style="color:{col};border-color:{col}55">{esc(t)}</span>'
RC = {"TP": GR, "TRAIL": OR, "SL": RD, "DANGER": RD, "TIME": AC, "MANUAL": MU, "ILLIQUID": RD}
def html_doc(d):
    tot = d["re"] + d["un"]; col = GR if tot >= 0 else RD
    def kpi(l, v, cc="#eef1f8", sub=""): return f'<div class="k"><div class="lbl">{l}</div><div class="v" style="color:{cc}">{v}</div>{f"<div class=sub>{sub}</div>" if sub else ""}</div>'
    pf = d["pf"]; pfs = "—" if pf is None else ("∞" if pf == float("inf") else f"{pf:.2f}")
    b, w = d["best"], d["worst"]
    stats = "".join([kpi("Win rate", f'{d["wr"]:.0f}%' if d["wr"] is not None else "—", sub=f'{len(d["W"])}W · {len(d["L"])}L'),
        kpi("Avg win", _m(d["aw"]), _c(d["aw"])), kpi("Avg loss", _m(d["al"]), _c(d["al"])), kpi("Profit factor", pfs),
        kpi("Best", f'{esc(b["symbol"][:8])} {H.pct(b["pct"])}' if b else "—", GR if b else MU), kpi("Worst", f'{esc(w["symbol"][:8])} {H.pct(w["pct"])}' if w else "—", RD if w and w["pnl"] < 0 else MU)])
    lab = lambda n: chip(*H.CHAIN.get(n, (n[:4].upper(), MU)))
    orows = "".join(f'<tr><td><b>{esc(p["symbol"][:10])}</b> {lab(p["network"])}</td><td>{H.fmtpx(p["entry"])}<br><span class="mu">{H.fmtpx(p["now"])}</span></td><td>{H.money(p["value"])}</td>'
                    f'<td style="color:{_c(p["u"])}"><b>{H.pct(p["pct"])}</b><br>{H.money(p["u"],True)}</td><td class="st">{"<br>".join(esc(s) for s in p["st"]) or "—"}</td></tr>' for p in d["op"])
    otab = f'<table><tr><th>Token</th><th>Entry / now</th><th>Size</th><th>uPnL</th><th>Risk</th></tr>{orows}</table>' if d["op"] else '<div class="empty">No open positions.</div>'
    crows = "".join(f'<tr><td><b>{esc(x["symbol"][:10])}</b> {lab(x["network"])}</td><td>{H.fmtpx(x["entry"])}<br><span class="mu">{H.fmtpx(x["exit"])}</span></td><td>{hold(x["held"])}</td>'
                    f'<td style="color:{_c(x["pnl"])}"><b>{H.pct(x["pct"])}</b><br>{H.money(x["pnl"],True)}</td><td>{chip(x["why"], RC.get(x["why"], MU))}</td></tr>' for x in d["cl"][::-1][:10])
    ctab = f'<table><tr><th>Token</th><th>Entry / exit</th><th>Held</th><th>Realized</th><th>Exit</th></tr>{crows}</table>' if d["cl"] else \
        '<div class="empty">No closed trades yet — stats fill in after the first exit.</div>'
    def brk(title, g):
        r = "".join(f'<tr><td>{esc(k)}</td><td>{v[0]}</td><td>{(f"{v[1]/v[0]*100:.0f}%" if v[0] else "—")}</td><td style="color:{_c(v[2])}">{H.money(v[2],True)}</td><td style="color:{_c(v[3])}">{H.money(v[3],True)}</td></tr>' for k, v in g)
        return f'<div class="card"><div class="lbl">{title}</div><table class="sm"><tr><th></th><th>Closed</th><th>Win</th><th>Real.</th><th>Unreal.</th></tr>{r or "<tr><td colspan=5 class=mu>—</td></tr>"}</table></div>'
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0;padding:0}} html{{background:#070910}}
body{{background:#070910;width:540px}} .wrap{{width:540px;font-family:Inter,sans-serif;color:#eef1f8;background:radial-gradient(120% 50% at 0% 0%,#1b2350 0%,transparent 60%),radial-gradient(90% 40% at 100% 100%,{col}22 0%,transparent 60%),linear-gradient(160deg,#0b0e1a,#070910);padding:22px;display:flex;flex-direction:column;gap:12px;font-feature-settings:"tnum"}}
.card{{background:linear-gradient(180deg,#ffffff0d,#ffffff06);border:1px solid #ffffff14;border-radius:18px;padding:14px 16px;box-shadow:0 8px 30px #0006}}
.hd{{display:flex;justify-content:space-between;align-items:center}} .brand{{font-weight:700;font-size:13px;letter-spacing:.4px}} .brand i{{display:inline-block;width:8px;height:8px;border-radius:50%;background:{GR};box-shadow:0 0 10px {GR};margin-right:7px}}
.tag{{font-size:10px;font-weight:700;letter-spacing:1.2px;color:{OR};border:1px solid {OR}66;padding:3px 8px;border-radius:99px}}
.lbl{{font-size:11px;color:{MU};font-weight:500;letter-spacing:.3px;text-transform:uppercase;margin-bottom:6px}}
.big{{font-size:38px;font-weight:800;letter-spacing:-1.2px;color:{col}}} .split{{display:flex;gap:10px;margin-top:10px}} .split div{{flex:1;padding:8px 10px;border-radius:12px;background:#ffffff08;border:1px solid #ffffff10}} .split b{{display:block;font-size:17px;margin-top:2px}}
.grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px 10px}} .k .v{{font-size:16px;font-weight:700;white-space:nowrap}} .sub{{font-size:10px;color:{MU};margin-top:2px}}
table{{width:100%;border-collapse:collapse;font-size:11.5px}} th{{text-align:left;font-size:9.5px;color:{MU};font-weight:600;text-transform:uppercase;letter-spacing:.5px;padding:0 4px 6px}}
td{{padding:7px 4px;border-top:1px solid #ffffff0f;vertical-align:middle;line-height:1.35}} .mu{{color:{MU}}} .st{{font-size:10px;color:#cfd5e4}}
table.sm td{{padding:5px 4px}} .chip{{font-size:8.5px;font-weight:700;letter-spacing:.8px;border:1px solid;border-radius:6px;padding:2px 5px;margin-left:3px;white-space:nowrap}}
.row2{{display:flex;flex-direction:column;gap:12px}} .row2 .card{{min-width:0}} table.sm{{font-size:11.5px;table-layout:fixed}} table.sm td:first-child,table.sm th:first-child{{width:34%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}} table.sm th{{font-size:9.5px;padding:0 2px 5px}} table.sm td{{padding:5px 2px}} .empty{{color:{MU};font-size:12.5px;text-align:center;padding:14px}}
.ft{{display:flex;justify-content:space-between;font-size:10px;color:{MU}}}
</style></head><body><div class="wrap">
<div class="hd"><div class="brand"><i></i>MEMECOIN SCANNER · {os.environ.get("REPORT_LABEL","Report Card")}</div><div class="tag">{os.environ.get("REPORT_TAG","PAPER")}</div></div>
<div class="card"><div class="lbl">Total PnL (realized + unrealized)</div><div class="big">{H.money(tot,True)}</div>
<div class="split"><div><span class="lbl">Realized</span><b style="color:{_c(d["re"])}">{H.money(d["re"],True)}</b></div><div><span class="lbl">Unrealized</span><b style="color:{_c(d["un"])}">{H.money(d["un"],True)}</b></div><div><span class="lbl">Equity</span><b>{H.money(d["eq"])}</b></div></div></div>
<div class="card grid">{stats}</div>
<div class="card"><div class="lbl">Open positions · {len(d["op"])}</div>{otab}</div>
<div class="card"><div class="lbl">Closed trades · {len(d["cl"])}{" (last 10)" if len(d["cl"])>10 else ""}</div>{ctab}</div>
<div class="row2">{brk("By entry tag", d["bytag"])}{brk("By decision source", d["bysrc"])}</div>
<div class="ft"><span>Live GeckoTerminal marks · fills incl. slippage + fees</span><span>{C.now_iso()[:16].replace("T"," ")} {C.TZ_LABEL}</span></div></div></body></html>'''
def render(out):
    d = data(); doc = html_doc(d)
    h = 900 + 56 * max(len(d["op"]), 1) + 52 * max(min(len(d["cl"]), 10), 1) + 30 * max(len(d["bytag"]), len(d["bysrc"]), 1)
    H.shoot(doc, out, h)
    try:  # trim to content
        from PIL import Image, ImageChops
        im = Image.open(out); bg = Image.new(im.mode, im.size, im.getpixel((im.width - 1, im.height - 1)))
        bb = ImageChops.difference(im, bg).getbbox()
        if bb and bb[3] < im.height - 20:
            im.crop((0, 0, im.width, bb[3] + 2)).save(out, format="PNG", optimize=True, compress_level=9)
    except Exception: pass
    H.tighten(out)
    pfv = d["pf"]; pfs = "—" if pfv is None else ("∞" if pfv == float("inf") else f"{pfv:.2f}")
    cap = (f"🧾 <b>Report Card</b> (paper)\nTotal {H.money(d['re']+d['un'],True)} · realized {H.money(d['re'],True)} · unrealized {H.money(d['un'],True)}\n"
           f"{len(d['op'])} open · {len(d['cl'])} closed · win rate {('%.0f%%' % d['wr']) if d['wr'] is not None else '—'} · PF {pfs}")
    try:
        cc = core.db(); import sys as _s; _s.path.insert(0, _ROOT + "/lib"); import clips as CL; CL.init(cc)
        n = cc.execute("select count(*), coalesce(sum(realized_pnl),0), coalesce(sum(usd_notional),0) from trades where side='sell' and qty>0 and (source like '%clip%' or source like 'tranche%')").fetchone()
        hm = [r[0] for r in cc.execute("select p.symbol from position_meta m join positions p on p.ca=m.ca where m.initial_out=1")]
        cap += f"\n✂️ Clips {n[0]} · realized from clips {H.money(n[1], True)} (proceeds ${n[2]:,.2f})" + (f"\n🏠 House money: {', '.join(hm)}" if hm else "")
    except Exception: pass
    return out, cap
if __name__ == "__main__":
    _p, _cap = render(sys.argv[1] if len(sys.argv) > 1 else f"{C.BASE}/alerts/report_sample.png")
    print(json.dumps({"path": _p, "cap": _cap}))   # used by auto/book.py (PAPER_DB=auto.db REPORT_LABEL=...)
