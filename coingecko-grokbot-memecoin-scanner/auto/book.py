"""Read-only views over both books (human paper.db, AI auto.db). Used by Telegram (/auto, /compare, /autoreport) and the dashboard."""
import os, sys, json, sqlite3, subprocess, time, html
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
B = _ROOT
sys.path.insert(0, f"{B}/lib"); sys.path.insert(0, f"{B}/telegram"); sys.path.insert(0, f"{B}/alerts")
import core, bankroll
DBS = {"human": f"{B}/paper.db", "auto": f"{B}/auto.db"}
def ro(book):
    c = sqlite3.connect(f"file:{DBS[book]}?mode=ro", uri=True, timeout=10); c.row_factory = sqlite3.Row; c.execute("pragma busy_timeout=10000"); return c
def _policy_start():
    try: return float(json.load(open(f"{B}/auto/policy.json"))["start_cash"])
    except Exception: return None
def start_cash(book):
    """Both books use PAPER_START_CASH while they have no trades. A traded AI book keeps its recorded start."""
    fallback = _policy_start() if book == "auto" else None
    try: c = ro(book)
    except Exception: return bankroll.configured() if fallback is None else fallback
    try: return bankroll.baseline(c, fallback=fallback)
    finally: c.close()
def stats(book):
    try: c = ro(book)
    except Exception: return {"book": book, "error": "no ledger yet"}
    try:
        rows = core.mtm(c); cash = c.execute("select v from account where k='cash'").fetchone()[0]
        sells = [dict(r) for r in c.execute("select * from trades where side='sell' and qty>0 order by id")]   # voided (corrected) rows have qty=0
        cols = [x[1] for x in c.execute("pragma table_info(trades)")]
        rat = {r["ca"]: r["rationale"] for r in c.execute("select ca, rationale from trades where side='buy' and rationale is not null order by id")} if "rationale" in cols else {}
        n_tr = c.execute("select count(*) from trades").fetchone()[0]
    finally: c.close()
    pv = sum((r["value"] if r["value"] is not None else r["cost_usd"]) for r in rows); un = sum((r["unrealized"] or 0) for r in rows)
    rz = sum((s["realized_pnl"] or 0) for s in sells); w = [s["realized_pnl"] for s in sells if (s["realized_pnl"] or 0) > 0]; l = [s["realized_pnl"] for s in sells if (s["realized_pnl"] or 0) <= 0]
    best = max(sells, key=lambda s: s["realized_pnl"] or 0, default=None); worst = min(sells, key=lambda s: s["realized_pnl"] or 0, default=None)
    sc = start_cash(book); eq = cash + pv
    for r in rows: r["rationale"] = rat.get(r["ca"])
    return {"book": book, "start": sc, "cash": cash, "pos_value": pv, "equity": eq, "ret_pct": (eq / sc - 1) * 100 if sc else 0, "realized": rz, "unrealized": un,
            "sells": len(sells), "trades": n_tr, "win_rate": len(w) / len(sells) * 100 if sells else None, "avg_win": sum(w) / len(w) if w else None,
            "avg_loss": sum(l) / len(l) if l else None, "best": best and {"symbol": best["symbol"], "pnl": best["realized_pnl"]},
            "worst": worst and {"symbol": worst["symbol"], "pnl": worst["realized_pnl"]}, "positions": rows, "open": len(rows)}
def m(v, s=True): return "—" if v is None else (("+" if v >= 0 else "−") if s else "") + f"${abs(v):,.2f}"
def auto_text():
    s = stats("auto")
    if s.get("error"): return "🤖 AI book: no ledger yet."
    L = [f"🤖 <b>AI AUTONOMOUS BOOK</b> (paper)", f"Equity <b>{m(s['equity'], False)}</b> ({s['ret_pct']:+.2f}%) · cash {m(s['cash'], False)}",
         f"Realized {m(s['realized'])} · Unrealized {m(s['unrealized'])}", f"Closed sells {s['sells']} · win {('%.0f%%' % s['win_rate']) if s['win_rate'] is not None else '—'} · open {s['open']}", ""]
    for r in s["positions"]:
        u = r["unrealized"]; pc = (u / r["cost_usd"] * 100) if u is not None and r["cost_usd"] else None
        st = f" · {core.esc(r['liq_status'])}" if r.get("liq_status") else ""
        L.append(f"• <b>{core.esc(html.unescape(r['symbol']))}</b> {r['network']} · {r.get('entry_tag') or ''} · cost {m(r['cost_usd'], False)} → {m(r['value'], False) if r['value'] is not None else '?'} ({'%+.1f%%' % pc if pc is not None else '?'}){st}")
        if r.get("rationale"): L.append(f"   <i>{core.esc(r['rationale'][:160])}</i>")
    if not s["positions"]: L.append("<i>No open positions — waiting for qualifying candidates.</i>")
    L.append("\n<i>Read-only · exits fully automatic · /compare · /autoreport</i>")
    return "\n".join(L)
def compare_text():
    h, a = stats("human"), stats("auto")
    def row(k, f): return f"{k:<11}{f(h):>13}{f(a):>13}"
    wr = lambda s: "—" if s.get("win_rate") is None else f"{s['win_rate']:.0f}%"
    bw = lambda s, k: "—" if not s.get(k) else f"{s[k]['symbol'][:6]} {s[k]['pnl']:+.0f}"
    lines = [row("", lambda s: "HUMAN" if s is h else "AI"), row("Equity", lambda s: f"${s['equity']:,.0f}"), row("Return", lambda s: f"{s['ret_pct']:+.1f}%"),
             row("Realized", lambda s: f"{s['realized']:+,.2f}"), row("Unrealized", lambda s: f"{s['unrealized']:+,.2f}"), row("Win rate", wr),
             row("Avg win", lambda s: m(s["avg_win"])), row("Avg loss", lambda s: m(s["avg_loss"])), row("Trades", lambda s: str(s["trades"])),
             row("Open", lambda s: str(s["open"])), row("Best", lambda s: bw(s, "best")), row("Worst", lambda s: bw(s, "worst"))]
    return "⚖️ <b>Human vs AI</b> (paper)\n<pre>" + html.escape("\n".join(lines)) + "</pre>"
def render_auto_report(out):
    env = {**os.environ, "PAPER_DB": DBS["auto"], "BOOK": "auto", "REPORT_LABEL": "AI AUTONOMOUS BOOK", "REPORT_TAG": "AI · PAPER"}
    r = subprocess.run([sys.executable, f"{B}/alerts/report.py", out], env=env, capture_output=True, text=True, timeout=150)
    d = json.loads(r.stdout.strip().splitlines()[-1]); return d["path"], "🤖 <b>AI AUTONOMOUS BOOK</b>\n" + d["cap"]
def render_compare(out):
    import pf_html as PH
    h, a = stats("human"), stats("auto")
    def col(s, name, acc):
        wr = "—" if s.get("win_rate") is None else f"{s['win_rate']:.0f}%"
        it = [("Equity", PH.money(s["equity"])), ("Return", PH.pct(s["ret_pct"])), ("Realized", PH.money(s["realized"], True)), ("Unrealized", PH.money(s["unrealized"], True)),
              ("Win rate", wr), ("Avg win", m(s["avg_win"])), ("Avg loss", m(s["avg_loss"])), ("Trades", s["trades"]), ("Open", s["open"]),
              ("Best", f"{html.escape(s['best']['symbol'])} {PH.money(s['best']['pnl'], True)}" if s.get("best") else "—"),
              ("Worst", f"{html.escape(s['worst']['symbol'])} {PH.money(s['worst']['pnl'], True)}" if s.get("worst") else "—")]
        rows = "".join(f'<div class="r"><span>{k}</span><b class="{("g" if str(v).startswith("+") else "rd" if str(v).startswith("−") else "")}">{v}</b></div>' for k, v in it)
        return f'<div class="col"><div class="h" style="color:{acc}">{name}</div>{rows}</div>'
    lead = "AI" if a["equity"] / a["start"] > h["equity"] / h["start"] else "HUMAN"
    doc = f"""<html><head><meta charset="utf-8"><style>
body{{margin:0;background:#0b0f17;color:#e6edf3;font-family:Inter,DejaVu Sans,sans-serif;width:540px}}
.w{{padding:16px}} .hd{{display:flex;justify-content:space-between;align-items:center}} .brand{{font-weight:800;font-size:16px;letter-spacing:.5px}}
.tag{{background:#1f6feb33;color:#58a6ff;padding:4px 10px;border-radius:8px;font-size:13px;font-weight:700}}
.cols{{display:flex;gap:10px;margin-top:14px}} .col{{flex:1;background:#121a26;border:1px solid #223047;border-radius:14px;padding:11px}}
.h{{font-weight:800;font-size:12.5px;margin-bottom:6px}} .r{{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #1b2636;font-size:11.5px}}
.r span{{color:#8b98a9}} .g{{color:#3fb950}} .rd{{color:#f85149}} .ft{{margin-top:10px;color:#8b98a9;font-size:10.5px}}
</style></head><body><div class="w"><div class="hd"><div class="brand">MEMECOIN SCANNER · Human vs AI</div><div class="tag">PAPER</div></div>
<div class="cols">{col(h, "🧑 HUMAN BOOK", "#58a6ff")}{col(a, "🤖 AI AUTONOMOUS BOOK", "#d2a8ff")}</div>
<div class="ft">Leader by return: <b>{lead}</b> · start ${h['start']:,.0f} vs ${a['start']:,.0f} · {time.strftime('%Y-%m-%d %H:%M')} {core.TZ_LABEL}</div></div></body></html>"""
    PH.shoot(doc, out, 425)
    return out, compare_text()
