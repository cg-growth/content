"""Render PNG chart cards (matplotlib, Agg)."""
import datetime as D, json, sys, time
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
sys.path.insert(0, _ROOT + "/lib"); import common as C
import matplotlib; matplotlib.use("Agg"); matplotlib.rcParams["text.parse_math"] = False; import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
BG, FG, GR, RD, MU = "#0b0e1a", "#eef1f8", "#22f59a", "#ff4d6d", "#8a93a8"
from matplotlib import font_manager as _fm
for _f in ("/usr/share/fonts/truetype/sand-box/google/Inter/Inter-VariableFont_opsz,wght.ttf",):
    try: _fm.fontManager.addfont(_f); matplotlib.rcParams["font.family"] = "Inter"
    except Exception: pass
def _style(ax):
    ax.set_facecolor(BG); [s.set_visible(False) for s in ax.spines.values()]; ax.grid(color="#ffffff12", lw=0.6); ax.tick_params(colors=MU, labelsize=8)
def candles(ax, rows, w):
    for r in rows:
        x = D.datetime.fromtimestamp(r["t"], C.MYT); col = GR if r["c"] >= r["o"] else RD
        xn = matplotlib.dates.date2num(x); ax.vlines(xn, r["l"], r["h"], color=col, lw=0.7)
        ax.add_patch(Rectangle((xn - w / 2, min(r["o"], r["c"])), w, abs(r["c"] - r["o"]) or r["c"] * 0.001, color=col))
    ax.xaxis_date(tz=C.MYT); ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%H:%M", tz=C.MYT)); ax.autoscale_view()
def render(a, out):
    """a: dict with network,pool,symbol,tag,confidence,score,components{},mix{},metrics{},pool_created_at,smart_buys[{t,price}]"""
    src = a.get("source") or "cg-first"; src_lbl = "X-first" if str(src).startswith("x") else "CG-first"
    mc = C.mdb()
    try: C.backfill(mc, a["network"], a["pool"], ("15s", "1m"))
    except Exception: pass
    rows = mc.execute("select * from ohlcv where pool=? and iv='15s' order by t desc limit 120", (a["pool"],)).fetchall()[::-1]; iv, w = "15s", 15 / 86400 * 0.7
    if len(rows) < 20: rows = mc.execute("select * from ohlcv where pool=? and iv='1m' order by t desc limit 120", (a["pool"],)).fetchall()[::-1]; iv, w = "1m", 60 / 86400 * 0.7
    fig = plt.figure(figsize=(9, 6.2), dpi=110, facecolor=BG); gs = fig.add_gridspec(2, 2, height_ratios=[2.2, 1], hspace=0.35, wspace=0.3)
    ax = fig.add_subplot(gs[0, :]); _style(ax)
    if rows: candles(ax, rows, w)
    pc = a.get("pool_created_at")
    if pc:
        t = D.datetime.fromisoformat(pc.replace("Z", "+00:00"))
        if rows and t.timestamp() >= rows[0]["t"]: ax.axvline(matplotlib.dates.date2num(t), color="#d29922", ls="--", lw=1); ax.text(matplotlib.dates.date2num(t), ax.get_ylim()[1], " launch", color="#d29922", fontsize=8, va="top")
    for s in a.get("smart_buys") or []:
        ax.scatter([matplotlib.dates.date2num(D.datetime.fromtimestamp(s["t"], C.MYT))], [s["price"]], marker="^", color="#58a6ff", s=60, zorder=5)
    m = a.get("metrics") or {}
    ax.set_title(f"{a.get('symbol','?')} · {a['network']} · {iv} · {src_lbl}   [{"SCOUT · near-miss" if str(a.get('tag','')).lower().startswith('scout') else a.get('tag','?') + ' / ' + str(a.get('confidence','?'))}]  score {a.get('score','-')}",
                 color=FG, fontsize=11, loc="left")
    ax.text(0.01, 0.95, f"liq ${m.get('liq',0):,.0f} · FDV ${m.get('fdv',0):,.0f} · age {m.get('age_min','?')}m · human {a.get('human_score','-')}" +
            ("  ▲ smart-money buy" if a.get("smart_buys") else ""), transform=ax.transAxes, color=MU, fontsize=8, va="top")
    b = fig.add_subplot(gs[1, 0]); _style(b); comp = a.get("components") or {}
    if comp:
        ks = list(comp); vs = [comp[k] for k in ks]
        b.barh(ks, vs, color=["#22f59a" if v >= 60 else "#ffb547" if v >= 35 else "#ff4d6d" for v in vs]); b.set_xlim(0, 100)
        for i, v in enumerate(vs): b.text(v + 1, i, f"{v:.0f}", color=FG, va="center", fontsize=8)
    b.set_title("score breakdown", color=FG, fontsize=9, loc="left"); [t.set_color(FG) for t in b.get_yticklabels()]
    p = fig.add_subplot(gs[1, 1]); p.set_facecolor(BG); mix = {k: v for k, v in (a.get("mix") or {}).items() if v}
    if mix:
        cols = {"smart": "#7c9cff", "human": "#22f59a", "unknown": "#8b949e", "bot": "#ff4d6d", "insider": "#db6d28", "bundle": "#a371f7"}
        p.pie(list(mix.values()), labels=[f"{k} {v}" for k, v in mix.items()], colors=[cols.get(k, "#666") for k in mix], textprops={"color": FG, "fontsize": 8}, wedgeprops={"width": 0.45})
    p.set_title("holder / trader mix", color=FG, fontsize=9, loc="left")
    fig.text(0.01, 0.005, src_lbl, color="#58a6ff" if src_lbl.startswith("X") else MU, fontsize=7, ha="left")
    fig.text(0.99, 0.005, "PAPER · CoinGecko onchain · " + C.now_iso()[:16].replace("T", " ") + " " + C.TZ_LABEL, color=MU, fontsize=7, ha="right")
    fig.savefig(out, facecolor=BG, bbox_inches="tight"); plt.close(fig); return out
