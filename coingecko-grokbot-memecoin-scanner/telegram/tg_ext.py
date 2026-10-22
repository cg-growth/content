"""Daemon extensions: /portfolio image, Skip, risk prompts (Sell/Hold/Adjust), SL/TP adjust, auto toggle, decision logging."""
import json, sys, time
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
sys.path.insert(0, _ROOT + "/lib"); sys.path.insert(0, _ROOT + "/alerts")
import common as C, core
import threading, os, shutil
_CACHE = {}   # kind -> (path, cap, ts)
_LK = threading.Lock()
def _render(kind):
    import portfolio as P, report as R
    tmp = f"{C.BASE}/cards/{kind}_{int(time.time())}.png"
    if kind in ("autoreport", "compare"):
        sys.path.insert(0, f"{C.BASE}/auto"); import book
        path, cap = (book.render_auto_report(tmp) if kind == "autoreport" else book.render_compare(tmp))
    else: path, cap = (P.render(tmp) if kind == "portfolio" else R.render(tmp))
    with _LK: _CACHE[kind] = (path, cap, time.time())
    return path, cap
def cached(kind, max_age=180):
    """Pre-rendered card (refreshed every ~150s by warm_loop); headless Chrome takes 5-65s under load."""
    with _LK: h = _CACHE.get(kind)
    if h and time.time() - h[2] <= max_age and os.path.exists(h[0]):
        return h[0], h[1] + f"\n<i>card rendered {int(time.time()-h[2])}s ago · tap 🔄 for fresh</i>"
    return _render(kind)
def card_kind(name):
    """Group cards/<kind>_<stamp>.png. Recap dates stay one group; other names stay their own group."""
    base = name[:-4] if name.lower().endswith(".png") else name
    if base.startswith("recap_"): return "recap"
    head, _, tail = base.rpartition("_")
    if head and tail.isdigit(): return head
    return base
def prune_cards(directory=None, keep=3):
    """Delete old PNGs under cards/, leaving the newest few of each kind and anything still cached."""
    d = directory or f"{C.BASE}/cards"
    try: names = [n for n in os.listdir(d) if n.lower().endswith(".png")]
    except OSError: return
    with _LK: live = {os.path.basename(h[0]) for h in _CACHE.values() if h and h[0]}
    groups = {}
    for n in names: groups.setdefault(card_kind(n), []).append(n)
    for files in groups.values():
        files.sort(key=lambda n: os.path.getmtime(os.path.join(d, n)), reverse=True)
        for n in files[keep:]:
            if n in live: continue
            try: os.remove(os.path.join(d, n))
            except OSError: pass
def warm_loop():
    while True:
        for k in ("portfolio", "report", "autoreport", "compare"):
            try: _render(k)
            except Exception: pass
        try: prune_cards()
        except Exception: pass
        time.sleep(150)
def portfolio(cid, reply_to=None, fresh=False):
    import portfolio as P
    path, cap = _render("portfolio") if fresh else cached("portfolio")
    return P.send_photo(cid, path, cap, {"inline_keyboard": [[{"text": "🔄 Refresh", "callback_data": "pf"}, {"text": "📈 Positions", "callback_data": "p"}, {"text": "🧾 Report", "callback_data": "rc"}]]}, reply_to)
REPLY_KB = {"keyboard": [[{"text": "📊 Portfolio"}, {"text": "🧾 Report Card"}, {"text": "📈 Positions"}], [{"text": "🤖 AI Book"}, {"text": "⚖️ Compare"}]], "resize_keyboard": True, "is_persistent": True,
            "input_field_placeholder": "buy $100 of … · sell half · or tap below"}
QUICK = {"📊 portfolio": "portfolio", "🧾 report card": "report", "📈 positions": "positions", "🤖 ai book": "auto", "⚖️ compare": "compare"}
COMMANDS = [("portfolio", "Portfolio chart image"), ("report", "Report card: realized/unrealized, open + closed, by tag"),
            ("positions", "Open positions"), ("pnl", "Realized + unrealized PnL"), ("balance", "Cash + equity"), ("ledger", "Last 15 trades"),
            ("buy", "Paper buy: /buy <CA|ticker> <usd>"), ("sell", "Paper sell: /sell <CA|ticker> <pct|all|usd>"),
            ("auto", "AI autonomous book: positions + PnL"), ("autoreport", "AI book report card"), ("compare", "Human vs AI book"), ("muted", "Muted tokens"), ("keyboard", "Show quick buttons"), ("help", "Help")]
def set_commands(): return core.tg("setMyCommands", commands=json.dumps([{"command": c, "description": d} for c, d in COMMANDS]))
def install_keyboard(cid, text="Quick buttons are ready below."): return core.send(cid, text, parse_mode=None, reply_markup=REPLY_KB)
def report(cid, reply_to=None):
    import report as R, portfolio as P
    path, cap = cached("report")
    return P.send_photo(cid, path, cap, {"inline_keyboard": [[{"text": "🔄 Refresh", "callback_data": "rc"}, {"text": "📊 Portfolio", "callback_data": "pf"}, {"text": "📈 Positions", "callback_data": "p"}]]}, reply_to)
def ai_book(cid, reply_to=None):
    sys.path.insert(0, f"{C.BASE}/auto"); import book
    return core.send(cid, book.auto_text(), reply_to=reply_to, reply_markup={"inline_keyboard": [[{"text": "🧾 AI Report", "callback_data": "ar"}, {"text": "⚖️ Compare", "callback_data": "cmp"}]]})
def autoreport(cid, reply_to=None, fresh=False):
    import portfolio as P
    path, cap = _render("autoreport") if fresh else cached("autoreport")
    return P.send_photo(cid, path, cap, {"inline_keyboard": [[{"text": "🔄 Refresh", "callback_data": "arf"}, {"text": "🤖 AI Book", "callback_data": "ab"}, {"text": "⚖️ Compare", "callback_data": "cmp"}]]}, reply_to)
def compare(cid, reply_to=None, fresh=False):
    import portfolio as P
    path, cap = _render("compare") if fresh else cached("compare")
    return P.send_photo(cid, path, cap, {"inline_keyboard": [[{"text": "🔄 Refresh", "callback_data": "cmpf"}, {"text": "🤖 AI Book", "callback_data": "ab"}, {"text": "🧾 AI Report", "callback_data": "ar"}]]}, reply_to)
def decision(c, ca, action, usd=None, source="button"):
    C.pinit(c); a = c.execute("select * from alerts where lower(ca)=? order by sent_at desc limit 1", (ca,)).fetchone()
    c.execute("insert into decisions(ts,ca,network,pool,action,usd,tag,confidence,score,source) values(?,?,?,?,?,?,?,?,?,?)",
              (C.now_iso(), ca, a["network"] if a else None, a["pool"] if a else None, action, usd, a["tag"] if a else None, a["confidence"] if a else None, a["human_score"] if a else None, source))
    c.execute("update outcomes set decision=? where ca=? and decision in ('pending','skip')", (action, ca)); c.commit()
def adjust_kb(ca):
    return {"inline_keyboard": [
        [{"text": f"SL {p}%", "callback_data": f"rs:{p}:{ca}"} for p in (-20, -30, -45, -60)],
        [{"text": "SL → breakeven", "callback_data": f"rs:0:{ca}"}],
        [{"text": f"TP1 {m}x", "callback_data": f"rt:{m}:{ca}"} for m in (1.5, 2, 3, 5)],
        [{"text": "TP → dynamic", "callback_data": f"rt:0:{ca}"}, {"text": "⏯ Toggle auto", "callback_data": f"rx:{ca}"}]]}
def handle_cb(c, cid, mid, op, rest, toast):
    """Return True if handled."""
    C.pinit(c)
    if op == "pf": toast("Rendering…"); portfolio(cid, mid); return True
    if op == "rc": toast("Rendering report card…"); report(cid, mid); return True
    if op == "ab": toast("AI book"); ai_book(cid, mid); return True
    if op in ("ar", "arf"): toast("AI report card…"); autoreport(cid, mid, fresh=op == "arf"); return True
    if op in ("cmp", "cmpf"): toast("Comparing books…"); compare(cid, mid, fresh=op == "cmpf"); return True
    if op == "k":
        decision(c, rest, "skip"); toast("Skipped — logged for learning")
        core.tg("editMessageReplyMarkup", chat_id=cid, message_id=mid, reply_markup={"inline_keyboard": [[{"text": "⏭ Skipped", "callback_data": "noop"}]]}); return True
    if op == "noop": toast("—"); return True
    if op == "cl":
        spec, _, ca = rest.partition(":"); spec = "initial" if spec == "init" else spec + "%"
        if not c.execute("select 1 from positions where ca=?", (ca,)).fetchone(): toast("No open position", True); return True
        toast(f"Clipping {spec}…"); import clips as CL
        core.send(cid, CL.clip(c, ca, spec, source="button"), reply_to=mid, reply_markup={"inline_keyboard": [core.clip_row(ca)]}); return True
    if op == "ac":
        import clips as CL; m = CL.meta(c, rest)
        if not m: toast("No open position", True); return True
        on = 0 if m["auto_clip"] else 1; c.execute("update position_meta set auto_clip=? where ca=?", (on, rest)); c.commit()
        toast("🤖 Auto-clip ON — ladder clips execute without asking" if on else "Auto-clip OFF — I'll ask at each level", True); return True
    if op == "rk":
        pr = c.execute("select * from risk_prompts where id=?", (int(rest),)).fetchone()
        if not pr or pr["status"] != "open": toast("Already handled", True); return True
        c.execute("update risk_prompts set status='skipped' where id=?", (pr["id"],))
        p = c.execute("select tp from risk_plans where ca=?", (pr["ca"],)).fetchone()
        if p and pr["level"] is not None:
            tp = json.loads(p["tp"]); tp[pr["level"]]["status"] = "skipped"; c.execute("update risk_plans set tp=? where ca=?", (json.dumps(tp), pr["ca"]))
        c.commit(); toast("Skipped this level")
        core.tg("editMessageReplyMarkup", chat_id=cid, message_id=mid, reply_markup={"inline_keyboard": [[{"text": "⏭ Skipped", "callback_data": "noop"}]]}); return True
    if op in ("ry", "rh"):
        pr = c.execute("select * from risk_prompts where id=?", (int(rest),)).fetchone()
        if not pr or pr["status"] != "open": toast("Already handled", True); return True
        if op == "rh":
            c.execute("update risk_prompts set status='hold' where id=?", (pr["id"],)); c.commit(); toast("Holding")
            core.tg("editMessageReplyMarkup", chat_id=cid, message_id=mid, reply_markup={"inline_keyboard": [[{"text": "✋ Held", "callback_data": "noop"}]]}); return True
        if not c.execute("select 1 from positions where ca=?", (pr["ca"],)).fetchone(): toast("Position already closed", True); return True
        spec = (pr["spec"] if "spec" in pr.keys() and pr["spec"] else f"{pr['sell_pct']:g}%")
        toast(f"Clipping {spec}…"); import clips as CL; out = CL.clip(c, pr["ca"], spec, source="tp-confirm")
        c.execute("update risk_prompts set status='sold' where id=?", (pr["id"],)); c.commit()
        core.tg("editMessageReplyMarkup", chat_id=cid, message_id=mid, reply_markup={"inline_keyboard": [[{"text": "✅ Sold", "callback_data": "noop"}]]})
        core.send(cid, out, reply_to=mid); return True
    if op == "ra":
        p = c.execute("select * from risk_plans where ca=?", (rest,)).fetchone()
        if not p: toast("No plan / position", True); return True
        tp = ", ".join(f"{t['sell_pct']}%@{t['multiple']}x({t['status']})" for t in json.loads(p["tp"]))
        core.send(cid, f"⚙️ <b>{core.esc(core.symbol_of(c, rest))}</b> plan\nSL ${p['sl_px']:.6g} ({(p['sl_px']/p['entry_px']-1)*100:+.0f}%) · auto {'ON' if p['auto'] else 'OFF'} · trail {'armed' if p['trail_active'] else 'off'}\nTP: {tp}",
                  reply_to=mid, reply_markup=adjust_kb(rest)); toast("Adjust"); return True
    if op == "rs":
        pct, _, ca = rest.partition(":"); p = c.execute("select * from risk_plans where ca=?", (ca,)).fetchone()
        if not p: toast("No plan", True); return True
        c.execute("update risk_plans set sl_px=?, sl_pct=? where ca=?", (p["entry_px"] * (1 + float(pct) / 100), float(pct), ca)); c.commit(); toast(f"SL set {pct}%"); return True
    if op == "rt":
        m, _, ca = rest.partition(":"); p = c.execute("select * from risk_plans where ca=?", (ca,)).fetchone()
        if not p: toast("No plan", True); return True
        tp = json.loads(p["tp"])
        if float(m) == 0: [t.pop("override", None) for t in tp]
        else: tp[0].update(multiple=float(m), override=True, status="open")
        c.execute("update risk_plans set tp=? where ca=?", (json.dumps(tp), ca)); c.commit(); toast("TP1 " + ("dynamic" if float(m) == 0 else f"{m}x")); return True
    if op == "rx":
        p = c.execute("select auto from risk_plans where ca=?", (rest,)).fetchone()
        if not p: toast("No plan", True); return True
        c.execute("update risk_plans set auto=? where ca=?", (0 if p["auto"] else 1, rest)); c.commit()
        toast("Auto exits " + ("OFF — SL/danger will only notify" if p["auto"] else "ON"), True); return True
    return False
