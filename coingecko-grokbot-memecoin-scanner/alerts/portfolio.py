#!/usr/bin/env python3
"""/portfolio image: equity curve, per-position PnL bars, distance to TP/SL. Also daily recap (recap()). PAPER."""
import datetime as D, json, sys, time
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
sys.path.insert(0, _ROOT + "/lib"); sys.path.insert(0, _ROOT + "/alerts")
import common as C, core, card
plt = card.plt; BG, FG, GR, RD, MU = card.BG, card.FG, card.GR, card.RD, card.MU
def data():
    c = C.pinit(core.db()); rows = core.mtm(c); cs, pv, un, re_ = core.snapshot(c, rows)
    snaps = c.execute("select ts,equity from snapshots order by ts").fetchall()
    plans = {r["ca"]: dict(r) for r in c.execute("select * from risk_plans")}
    return c, rows, cs, pv, un, re_, snaps, plans
def render(out, title="Portfolio"):
    try: return render_html(out, title)
    except Exception as e: print('html render failed, falling back:', e, file=sys.stderr)
    return render_mpl(out, title)
def render_mpl(out, title="Portfolio"):
    c, rows, cs, pv, un, re_, snaps, plans = data(); eq = cs + pv; start = core.book_start(c)
    fig = plt.figure(figsize=(9, 7), dpi=110, facecolor=BG); gs = fig.add_gridspec(3, 1, height_ratios=[1.3, 1, 1], hspace=0.55)
    a = fig.add_subplot(gs[0]); card._style(a)
    if snaps:
        xs = [D.datetime.fromisoformat(s["ts"]) for s in snaps] + [D.datetime.now(C.MYT)]; ys = [s["equity"] for s in snaps] + [eq]
        a.plot(xs, ys, color="#58a6ff", lw=1.6); a.axhline(start, color=MU, ls=":", lw=0.8)
        a.fill_between(xs, ys, start, where=[y >= start for y in ys], color=GR, alpha=0.15)
        a.fill_between(xs, ys, start, where=[y < start for y in ys], color=RD, alpha=0.15)
        a.xaxis.set_major_formatter(card.matplotlib.dates.DateFormatter("%m-%d %H:%M", tz=C.MYT))
    a.set_title(f"{title} · equity ${eq:,.2f} ({((eq/start-1)*100 if start else 0):+.2f}%) · cash ${cs:,.0f} · realized ${re_:+,.2f} · unrealized ${un:+,.2f}", color=FG, fontsize=9.5, loc="left")
    b = fig.add_subplot(gs[1]); card._style(b)
    if rows:
        lab = [r["symbol"][:10] for r in rows]; pct = [((r["unrealized"] or 0) / r["cost_usd"] * 100) for r in rows]
        b.bar(lab, pct, width=0.4 if len(lab) < 3 else 0.7, color=[GR if p >= 0 else RD for p in pct])
        for i, (p, r) in enumerate(zip(pct, rows)): b.text(i, p, f"{p:+.1f}%\n${r['unrealized'] or 0:+,.2f}", color=FG, ha="center", va="bottom" if p >= 0 else "top", fontsize=8)
        [t.set_color(FG) for t in b.get_xticklabels()]; b.axhline(0, color=MU, lw=0.7)
    else: b.text(0.5, 0.5, "no open positions", color=MU, ha="center", transform=b.transAxes)
    b.set_title("open position PnL (unrealized)", color=FG, fontsize=9, loc="left")
    d = fig.add_subplot(gs[2]); card._style(d)
    for i, r in enumerate(rows):
        pl = plans.get(r["ca"])
        if not pl or not r["price"]: continue
        m = r["price"] / pl["entry_px"]; sl = pl["sl_px"] / pl["entry_px"]; tps = [t["multiple"] for t in json.loads(pl["tp"]) if t["status"] == "open"]
        hi = max([m * 1.2] + tps); d.hlines(i, sl, hi, color="#30363d", lw=6)
        d.scatter([sl], [i], color=RD, marker="|", s=300, zorder=3); d.text(sl, i + 0.25, f"SL {sl:.2f}x", color=RD, fontsize=7, ha="center")
        if pl["trail_active"]:
            tr = pl["peak_px"] * (1 - C.risk_cfg()["trailing_stop"]["trail_pct"] / 100) / pl["entry_px"]
            d.scatter([tr], [i], color="#db6d28", marker="|", s=300, zorder=3); d.text(tr, i - 0.4, f"trail {tr:.2f}x", color="#db6d28", fontsize=7, ha="center")
        for t in tps: d.scatter([t], [i], color=GR, marker="|", s=300, zorder=3); d.text(t, i + 0.25, f"TP {t:.2f}x", color=GR, fontsize=7, ha="center")
        d.scatter([m], [i], color="#58a6ff", s=50, zorder=4); d.text(m, i - 0.4, f"now {m:.2f}x", color="#58a6ff", fontsize=7, ha="center")
    d.set_yticks(range(len(rows))); d.set_yticklabels([r["symbol"][:10] for r in rows], color=FG); d.set_ylim(-0.8, max(len(rows), 1) - 0.2)
    d.set_title("distance to SL / trailing / TP (multiple of entry)", color=FG, fontsize=9, loc="left")
    fig.text(0.99, 0.005, "PAPER ONLY · " + C.now_iso()[:16].replace("T", " ") + " " + C.TZ_LABEL, color=MU, fontsize=7, ha="right")
    fig.savefig(out, facecolor=BG, bbox_inches="tight"); plt.close(fig)
    cap = (f"📈 <b>{title}</b> (paper)\nEquity <b>${eq:,.2f}</b> ({((eq/start-1)*100 if start else 0):+.2f}%) · cash ${cs:,.2f}\n"
           f"Realized ${re_:+,.2f} · Unrealized ${un:+,.2f} · {len(rows)} open")
    c.close(); return out, cap
def render_html(out, title="Portfolio"):
    import pf_html as H
    c, rows, cs, pv, un, re_, snaps, plans = data(); eq = cs + pv; start = core.book_start(c)
    now = time.time(); ser = [(D.datetime.fromisoformat(s["ts"]).timestamp(), s["equity"]) for s in snaps] + [(now, eq)]
    day0 = [e for t, e in ser if t >= now - 86400]; day = eq - (day0[0] if day0 else eq)
    sells = c.execute("select realized_pnl p from trades where side='sell'").fetchall()
    wins = [r["p"] for r in sells if (r["p"] or 0) > 0]
    pos = []
    for r in rows:
        pl = plans.get(r["ca"]); px = r["price"]; entry = (pl or {}).get("entry_px") or (r["cost_usd"] / r["qty"] if r["qty"] else 0)
        now_x = (px / entry) if px and entry else 1.0; sl_x = (pl["sl_px"] / entry) if pl else 0.55
        tps = sorted(t["multiple"] for t in json.loads(pl["tp"]) if t["status"] == "open") if pl else []
        tr = pl["peak_px"] * (1 - C.risk_cfg()["trailing_stop"]["trail_pct"] / 100) / entry if pl and pl["trail_active"] and pl["peak_px"] else None
        val = r["value"] if r["value"] is not None else r["cost_usd"]; u = r["unrealized"] or 0
        pos.append(dict(symbol=r["symbol"] or "?", network=r["network"], pool=r["pool"], entry=entry, now=px, value=val, unreal=u,
                        pnl_pct=u / r["cost_usd"] * 100 if r["cost_usd"] else 0, now_x=now_x, sl_x=sl_x, tp_x=tps[0] if tps else None, trail_x=tr, house=bool((core.house_badge(c, r["ca"]) or "").strip().startswith("🏠"))))
    best = max(pos, key=lambda p: p["pnl_pct"]) if pos else None
    h = max(675, 560 + 92 * max(len(pos), 1))
    d = dict(title=title, eq=eq, ret=((eq / start - 1) * 100 if start else 0), start=start, cash=cs, pv=pv, un=un, re=re_, snaps=ser, pos=pos, h=h,
             ntr=c.execute("select count(*) from trades").fetchone()[0], wr=(f"{len(wins)/len(sells)*100:.0f}%" if sells else "—"),
             best=(f"{best['symbol'][:6]} {best['pnl_pct']:+.0f}%" if best else "—"), day=day, ts=C.now_iso()[:16].replace("T", " "))
    H.shoot(H.html_doc(d), out, h)
    cap = (f"📈 <b>{title}</b> (paper)\nEquity <b>${eq:,.2f}</b> ({((eq/start-1)*100 if start else 0):+.2f}%) · cash ${cs:,.2f}\n"
           f"Realized ${re_:+,.2f} · Unrealized ${un:+,.2f} · {len(rows)} open")
    c.close(); return out, cap
def send_photo(chat_id, path, cap, kb=None, reply_to=None):
    import requests
    d = {"chat_id": chat_id, "caption": cap[:1024], "parse_mode": "HTML"}
    if kb: d["reply_markup"] = json.dumps(kb)
    if reply_to: d["reply_to_message_id"] = reply_to
    return core.session().post(f"https://api.telegram.org/bot{core._tok()}/sendPhoto", data=d, files={"photo": open(path, "rb")}, timeout=(10, 60)).json()
def recap_text():
    c = C.pinit(core.db()); since = (D.datetime.now(C.MYT) - D.timedelta(days=1)).isoformat()
    tr = c.execute("select side,count(*) n,sum(coalesce(realized_pnl,0)) p from trades where ts>? group by side", (since,)).fetchall()
    al = c.execute("select count(*) from alerts where sent_at>?", (since,)).fetchone()[0]
    dec = dict(c.execute("select action,count(*) from decisions where ts>? group by action", (since,)).fetchall())
    ev = dict(c.execute("select kind,count(*) from risk_events where ts>? and action in ('sold','asked') group by kind", (since,)).fetchall())
    oc = c.execute("select symbol,tag,decision,ret_1h,ret_6h,ret_24h from outcomes where alerted_at>? order by alerted_at", (since,)).fetchall()
    s = f"\n24h: {al} alerts · buys {dec.get('buy',0)} · skips {dec.get('skip',0)}\nTrades: " + ", ".join(f"{r['side']} {r['n']}" for r in tr) + \
        f" · realized ${sum(r['p'] for r in tr):+,.2f}\nRisk actions: " + (", ".join(f"{k} {v}" for k, v in ev.items()) or "none")
    if oc: s += "\nAlert outcomes (1h/6h): " + "; ".join(f"{r['symbol']} {r['decision']} {('%+.0f%%' % (r['ret_1h']*100)) if r['ret_1h'] is not None else '-'}/{('%+.0f%%' % (r['ret_6h']*100)) if r['ret_6h'] is not None else '-'}" for r in oc[:8])
    c.close(); return s
if __name__ == "__main__":
    p, cap = render(f"{C.BASE}/cards/portfolio_test.png"); print(p, cap, recap_text())
