"""Sleek HTML -> headless Chrome renderer for /portfolio + daily recap. PAPER."""
import datetime as D, html, json, math, os, subprocess, sys, tempfile, time
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
sys.path.insert(0, _ROOT + "/lib"); import common as C
GR, RD, AC, OR, MU = "#22f59a", "#ff4d6d", "#7c9cff", "#ffb547", "#8a93a8"
CHAIN = {"robinhood": ("RH", "#c3f53c"), "base": ("BASE", "#3b82f6"), "bsc": ("BSC", "#f3ba2f"), "eth": ("ETH", "#8c9eff")}
esc = html.escape
def money(v, sign=False): return (("+" if v >= 0 else "−") if sign else ("−" if v < 0 else "")) + f"${abs(v):,.2f}"
def pct(v): return ("+" if v >= 0 else "−") + f"{abs(v):.2f}%"
def fmtpx(p):
    if not p: return "—"
    if p >= 1: return f"${p:,.4f}"
    e = int(math.floor(math.log10(p)));  return f"${p:.{max(2, -e + 3)}f}" if e > -6 else f"${p:.3e}"
def path(xs, ys, w, h, pad=4):
    if len(ys) < 2: return "", ""
    x0, x1 = min(xs), max(xs); y0, y1 = min(ys), max(ys); y1 = y1 if y1 > y0 else y0 + 1e-12
    P = [(pad + (x - x0) / ((x1 - x0) or 1) * (w - 2 * pad), pad + (1 - (y - y0) / (y1 - y0)) * (h - 2 * pad)) for x, y in zip(xs, ys)]
    d = f"M{P[0][0]:.1f},{P[0][1]:.1f}"
    for i in range(1, len(P)):  # smooth (catmull-rom -> bezier)
        p0 = P[max(i - 2, 0)]; p1 = P[i - 1]; p2 = P[i]; p3 = P[min(i + 1, len(P) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6); c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        lo_, hi_ = min(p1[1], p2[1]), max(p1[1], p2[1]); c1 = (c1[0], min(max(c1[1], lo_), hi_)); c2 = (c2[0], min(max(c2[1], lo_), hi_))
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d, d + f" L{P[-1][0]:.1f},{h} L{P[0][0]:.1f},{h} Z"
def spark(pool):
    try:
        mc = C.mdb()
        for iv in ("1m", "15s", "1s"):
            r = mc.execute("select t,c from ohlcv where pool=? and iv=? order by t desc limit 90", (pool, iv)).fetchall()[::-1]
            if len(r) >= 8: return [x["t"] for x in r], [x["c"] for x in r]
    except Exception: pass
    return [], []
def html_doc(d):
    eq, ret = d["eq"], d["ret"]; up = ret >= 0; col = GR if up else RD
    xs = [s[0] for s in d["snaps"]]; ys = [s[1] for s in d["snaps"]]
    lp, ap = path(xs, ys, 464, 150)
    t0 = D.datetime.fromtimestamp(xs[0], C.MYT).strftime("%d %b %H:%M") if xs else ""; t1 = D.datetime.fromtimestamp(xs[-1], C.MYT).strftime("%H:%M") if xs else ""
    inv = d["pv"]; cash = d["cash"]; tot = max(inv + cash, 1e-9); f = inv / tot; R = 34; circ = 2 * math.pi * R
    rows = ""
    for p in d["pos"]:
        lab, cc = CHAIN.get(p["network"], (p["network"][:4].upper(), MU)); pc = p["pnl_pct"]; pcol = GR if pc >= 0 else RD
        sx, sy = spark(p["pool"]); sl, _ = path(sx, sy, 110, 34, 2)
        lo, hi = p["sl_x"], p["tp_x"] or max(p["now_x"] * 1.3, 2); span = (hi - lo) or 1
        pos_ = lambda m: max(0, min(100, (m - lo) / span * 100))
        marks = f'<i class="mk" style="left:{pos_(1):.1f}%;background:#fff6"></i>'
        if p["trail_x"]: marks += f'<i class="mk tr" style="left:{pos_(p["trail_x"]):.1f}%"></i>'
        rows += f'''<div class="card pos"><div class="pl"><div class="sym">{esc(p["symbol"][:12])} <span class="chip" style="color:{cc};border-color:{cc}55">{lab}</span>{'<span class="chip" style="color:'+OR+';border-color:'+OR+'55">TRAIL</span>' if p["trail_x"] else ''}{'<span class="chip" style="color:#22c55e;border-color:#22c55e55">🏠 HOUSE</span>' if p.get("house") else ''}</div>
<div class="sub">{fmtpx(p["entry"])} → <b>{fmtpx(p["now"])}</b> · {money(p["value"])}</div></div>
<svg class="spk" viewBox="0 0 110 34"><path d="{sl}" fill="none" stroke="{pcol}" stroke-width="1.6" stroke-linecap="round"/></svg>
<div class="pr"><div class="pp" style="color:{pcol}">{pct(pc)}</div><div class="sub" style="color:{pcol}">{money(p["unreal"], True)}</div></div>
<div class="bar"><div class="trk"><div class="fill" style="width:{pos_(p["now_x"]):.1f}%;background:linear-gradient(90deg,{RD},{OR} 45%,{GR})"></div>{marks}<i class="dot" style="left:{pos_(p["now_x"]):.1f}%"></i></div>
<div class="bl"><span style="color:{RD}">SL {p["sl_x"]:.2f}x</span>{f'<span style="color:{OR}">trail {p["trail_x"]:.2f}x</span>' if p["trail_x"] else ''}<span style="color:#fff">now {p["now_x"]:.2f}x</span><span style="color:{GR}">{('TP '+format(p["tp_x"],'.2f')+'x') if p["tp_x"] else 'no TP'}</span></div></div></div>'''
    if not d["pos"]: rows = '<div class="card empty">No open positions — all cash, ready for the next signal.</div>'
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:540px;height:{d["h"]}px;font-family:Inter,sans-serif;color:#eef1f8;background:radial-gradient(120% 60% at 0% 0%,#1b2350 0%,transparent 60%),radial-gradient(90% 50% at 100% 100%,{col}22 0%,transparent 60%),linear-gradient(160deg,#0b0e1a,#070910);padding:22px;display:flex;flex-direction:column;gap:12px;font-feature-settings:"tnum"}}
.card{{background:linear-gradient(180deg,#ffffff0d,#ffffff06);border:1px solid #ffffff14;border-radius:18px;padding:14px 16px;box-shadow:0 8px 30px #0006}}
.hd{{display:flex;justify-content:space-between;align-items:center}} .brand{{font-weight:700;font-size:13px;letter-spacing:.4px}} .brand i{{display:inline-block;width:8px;height:8px;border-radius:50%;background:{GR};box-shadow:0 0 10px {GR};margin-right:7px}}
.tag{{font-size:10px;font-weight:700;letter-spacing:1.2px;color:{OR};border:1px solid {OR}66;padding:3px 8px;border-radius:99px}}
.lbl{{font-size:11px;color:{MU};font-weight:500;letter-spacing:.3px;text-transform:uppercase}}
.eq{{font-size:40px;font-weight:800;letter-spacing:-1.2px;margin-top:2px}} .pill{{display:inline-block;margin-left:10px;font-size:14px;font-weight:700;padding:4px 10px;border-radius:99px;vertical-align:10px;color:{col};background:{col}1f;border:1px solid {col}55}}
.stats{{display:flex;gap:18px;margin-top:6px;font-size:12px;color:{MU}}} .stats b{{color:#eef1f8;font-weight:600}}
.chart{{position:relative;margin-top:8px}} .ax{{display:flex;justify-content:space-between;font-size:10px;color:{MU};margin-top:2px}}
.row2{{display:flex;gap:12px}} .row2 .card{{flex:1}}
.donut{{display:flex;align-items:center;gap:14px}} .lg div{{font-size:12px;color:{MU};margin:3px 0}} .lg b{{color:#eef1f8}} .sq{{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:6px}}
.kv{{display:grid;grid-template-columns:1fr 1fr;gap:8px 10px}} .kv .v{{font-size:16px;font-weight:700;margin-top:2px}}
.pos{{display:grid;grid-template-columns:1fr 110px 92px;grid-template-rows:auto auto;gap:6px 12px;align-items:center}}
.sym{{font-size:16px;font-weight:700}} .chip{{font-size:9px;font-weight:700;letter-spacing:.8px;border:1px solid;border-radius:6px;padding:2px 5px;margin-left:5px;vertical-align:2px}}
.sub{{font-size:11px;color:{MU};margin-top:2px}} .sub b{{color:#eef1f8}} .pr{{text-align:right}} .pp{{font-size:18px;font-weight:800}}
.bar{{grid-column:1/4}} .trk{{position:relative;height:6px;border-radius:99px;background:#ffffff12}} .fill{{position:absolute;inset:0 auto 0 0;border-radius:99px;opacity:.85}}
.mk{{position:absolute;top:-3px;width:2px;height:12px;border-radius:1px}} .mk.tr{{background:{OR};box-shadow:0 0 6px {OR}}}
.dot{{position:absolute;top:50%;width:12px;height:12px;margin:-6px 0 0 -6px;border-radius:50%;background:#fff;box-shadow:0 0 0 3px #ffffff30,0 0 12px #fff8}}
.bl{{display:flex;justify-content:space-between;font-size:10px;font-weight:600;margin-top:5px}} .empty{{color:{MU};font-size:13px;text-align:center;padding:22px}}
.ft{{margin-top:auto;display:flex;justify-content:space-between;font-size:10px;color:{MU}}}
</style></head><body>
<div class="hd"><div class="brand"><i></i>MEMECOIN SCANNER · {esc(d["title"])}</div><div class="tag">PAPER</div></div>
<div class="card"><div class="lbl">Total equity</div><div class="eq">{money(eq)}<span class="pill">{"▲" if up else "▼"} {pct(ret)}</span></div>
<div class="stats"><span>Realized <b style="color:{GR if d["re"]>=0 else RD}">{money(d["re"],True)}</b></span><span>Unrealized <b style="color:{GR if d["un"]>=0 else RD}">{money(d["un"],True)}</b></span><span>Open <b>{len(d["pos"])}</b></span></div>
<div class="chart"><svg width="464" height="150" viewBox="0 0 464 150" overflow="visible"><defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{col}" stop-opacity=".35"/><stop offset="1" stop-color="{col}" stop-opacity="0"/></linearGradient><filter id="gl" x="-10%" y="-30%" width="120%" height="160%"><feGaussianBlur stdDeviation="4"/></filter></defs>
<path d="{ap}" fill="url(#g)"/><path d="{lp}" fill="none" stroke="{col}" stroke-width="5" opacity=".45" filter="url(#gl)"/><path d="{lp}" fill="none" stroke="{col}" stroke-width="2.2" stroke-linecap="round"/></svg>
<div class="ax"><span>{t0}</span><span>start {money(d["start"])}</span><span>{t1} {C.TZ_LABEL}</span></div></div></div>
<div class="row2"><div class="card donut"><svg width="84" height="84" viewBox="0 0 84 84"><circle cx="42" cy="42" r="{R}" fill="none" stroke="#ffffff14" stroke-width="10"/><circle cx="42" cy="42" r="{R}" fill="none" stroke="{AC}" stroke-width="10" stroke-linecap="round" stroke-dasharray="{max(f*circ,0.01):.2f} {circ:.2f}" transform="rotate(-90 42 42)"/><text x="42" y="46" text-anchor="middle" fill="#eef1f8" font-size="13" font-weight="700" font-family="Inter">{f*100:.1f}%</text></svg>
<div class="lg"><div class="lbl">Allocation</div><div><span class="sq" style="background:{AC}"></span>Invested <b>{money(inv)}</b></div><div><span class="sq" style="background:#ffffff30"></span>Cash <b>{money(cash)}</b></div></div></div>
<div class="card kv"><div><div class="lbl">Trades</div><div class="v">{d["ntr"]}</div></div><div><div class="lbl">Win rate</div><div class="v">{d["wr"]}</div></div><div><div class="lbl">Best</div><div class="v" style="color:{GR};font-size:14px;white-space:nowrap">{d["best"]}</div></div><div><div class="lbl">Day Δ</div><div class="v" style="color:{GR if d["day"]>=0 else RD}">{money(d["day"],True)}</div></div></div></div>
<div class="lbl" style="margin:2px 2px -4px">Open positions</div>{rows}
<div class="ft"><span>Live GeckoTerminal marks · fills incl. slippage + fees</span><span>{d["ts"]} {C.TZ_LABEL}</span></div></body></html>'''
def chrome_bin():
    """Headless Chrome/Chromium used to render HTML cards. Override with CHROME_BIN."""
    import shutil
    for c in [os.environ.get("CHROME_BIN", ""), "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Chromium.app/Contents/MacOS/Chromium"]:
        if c and (shutil.which(c) or os.path.exists(c)): return shutil.which(c) or c
    raise RuntimeError("Chrome/Chromium not found: install it or set CHROME_BIN (needed for portfolio/report cards)")
def shoot(doc, out, h):
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f: f.write(doc); fn = f.name
    try:
        subprocess.run([chrome_bin(), "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                        f"--window-size=540,{h}", "--default-background-color=00000000", f"--screenshot={out}", "file://" + fn],
                       check=True, capture_output=True, timeout=75)
    finally: os.unlink(fn)
    return out
