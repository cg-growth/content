#!/usr/bin/env python3
"""Long-poll Telegram daemon: owner lock, paper-trading commands, inline buttons, natural language, voice notes,
and fallback forwarding. Token from env only (TELEGRAM_BOT_TOKEN); forward key from env only (TELEGRAM_FORWARD_KEY)."""
import json, os, re, sys, time, traceback, urllib.request, urllib.error, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core, nl, tg_ext
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
sys.path.insert(0, _ROOT + '/lib'); import fwdq, threading
BUSY_NOTE = [0]
def _drain_loop():
    while True:
        try:
            if fwdq.drain(log, kind="freeform"): BUSY_NOTE[0] = 0
        except Exception as e: log('fwdq drain err', e)
        time.sleep(30)

OFF = f"{core.TG}/offset.json"; UNAUTH = f"{core.TG}/unauthorized_notified.json"
def log(*a): print(core.now(), *[_red(x) for x in a], flush=True)
def _red(x):
    s = core.redact(x); k = os.environ.get("TELEGRAM_FORWARD_KEY", "")
    return s.replace(k, "<redacted>") if k else s
def jload(p, d):
    try: return json.load(open(p))
    except Exception: return d
def jsave(p, o): tmp = p + ".tmp"; json.dump(o, open(tmp, "w"), indent=1); os.replace(tmp, p)
DRY = os.environ.get("TG_DRY_RUN") == "1"
def main():
    me = core.tg("getMe", timeout=15)
    log("getMe", "ok" if me.get("ok") else me.get("description"), "@" + str((me.get("result") or {}).get("username")),
        "forward=" + ("on" if os.environ.get("TELEGRAM_FORWARD_URL") else "off"))
    core.tg("deleteWebhook", timeout=15)
    try: log("setMyCommands", tg_ext.set_commands().get("ok"))
    except Exception as e: log("setMyCommands error", e)
    if not DRY: threading.Thread(target=_drain_loop, daemon=True).start()
    threading.Thread(target=tg_ext.warm_loop, daemon=True).start()   # pre-render portfolio/report cards
    off = jload(OFF, {}).get("offset", 0); last_snap = 0
    while True:
        r = _raw_get_updates(off)
        if not r.get("ok"): log("getUpdates error", r.get("description")); time.sleep(5); continue
        for u in r["result"]:
            off = u["update_id"] + 1; jsave(OFF, {"offset": off})
            try: dispatch(u)
            except Exception: log("handler error", traceback.format_exc(limit=3))
        if time.time() - last_snap > 3600:
            try:
                c = core.db()
                if c.execute("select count(*) from positions").fetchone()[0]: core.snapshot(c)
                c.close()
            except Exception as e: log("snapshot error", e)
            last_snap = time.time()
def _raw_get_updates(off):
    import urllib.parse
    data = urllib.parse.urlencode({"offset": off, "timeout": 50, "allowed_updates": json.dumps(["message", "callback_query"])}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{core._tok()}/getUpdates", data=data), timeout=65) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try: return json.load(e)
        except Exception: return {"ok": False, "description": f"HTTP {e.code}"}
    except Exception as e: return {"ok": False, "description": core.redact(f"{type(e).__name__}: {e}")}
from concurrent.futures import ThreadPoolExecutor
POOL = ThreadPoolExecutor(max_workers=6, thread_name_prefix="tg")
def _run(fn, arg, t0):
    try: fn(arg)
    except Exception: log("handler error", traceback.format_exc(limit=3))
    finally: log("latency", fn.__name__, f"{time.time()-t0:.2f}s")
def dispatch(u):
    """Never block the long-poll loop: each update runs in the thread pool."""
    t0 = time.time()
    if u.get("callback_query"): POOL.submit(_run, on_callback, u["callback_query"], t0)
    elif u.get("message"): POOL.submit(_run, on_message, u["message"], t0)

# ---------- helpers ----------
def reply(c, cid, text, reply_to=None, kb=None, ca=None, kind="fill"):
    r = core.send(cid, text, reply_to=reply_to, reply_markup=kb)
    if r.get("ok") and ca: core.remember(c, cid, r["result"]["message_id"], ca, kind)
    return r
def ok_trade(out): return out.startswith("🟢") or out.startswith("🔴") or out.startswith("✂️")
def refresh_msg(c, cid, mid, kind, ca):
    """Edit an alert to show the current position, or re-render a positions message."""
    if kind == "alert":
        a = c.execute("select text from alerts where chat_id=? and message_id=?", (cid, mid)).fetchone()
        if not a: return
        txt = (a["text"] or "").split("\n\n📊")[0] + "\n\n" + core.position_line(c, ca) + f"\n<i>updated {core.now()[11:16]} {core.TZ_LABEL}</i>"
        core.tg("editMessageText", chat_id=cid, message_id=mid, text=txt[:4000], parse_mode="HTML",
                disable_web_page_preview="true", reply_markup=core.alert_kb(ca))
    elif kind == "positions":
        txt, rows = core.positions_view(c)
        core.tg("editMessageText", chat_id=cid, message_id=mid, text=txt[:4000], parse_mode="HTML",
                disable_web_page_preview="true", reply_markup=core.positions_kb(rows) if rows else None)
def send_positions(c, cid, reply_to=None):
    txt, rows = core.positions_view(c)
    r = core.send(cid, txt, reply_to=reply_to, reply_markup=core.positions_kb(rows) if rows else None)
    if r.get("ok"): core.remember(c, cid, r["result"]["message_id"], rows[0]["ca"] if len(rows) == 1 else None, "positions")
def run_query(c, cid, cmd, reply_to):
    if cmd == "positions": return send_positions(c, cid, reply_to)
    if cmd == "portfolio": return tg_ext.portfolio(cid, reply_to)
    if cmd == "report": return tg_ext.report(cid, reply_to)
    if cmd == "auto": return tg_ext.ai_book(cid, reply_to)
    if cmd == "autoreport": return tg_ext.autoreport(cid, reply_to)
    if cmd == "compare": return tg_ext.compare(cid, reply_to)
    reply(c, cid, core.handle(c, "/" + cmd), reply_to)
def execute(c, intent, source):
    if intent["side"] == "clip":
        import clips as CL; return CL.clip(c, intent["ca"], intent["spec"], source=source)
    if intent["side"] == "buy": return core.buy(c, intent["ca"], float(intent["usd"]), source=source)
    return core.sell(c, intent["ca"], intent["amt"], source=source)
def _busy_note(cid, m):
    if time.time() - BUSY_NOTE[0] > 1800:   # tell the user once per outage, not per message
        BUSY_NOTE[0] = time.time()
        core.send(cid, "⏳ The assistant is busy right now. I've queued your message and will reply when it's back. "
                       "Quick trades/queries (e.g. <code>buy $50 of TICKER</code>, /pnl, /positions) still work instantly.", reply_to=m["message_id"])
def forward(cid, m, text, reply_ca, source):
    url = os.environ.get("TELEGRAM_FORWARD_URL"); key = os.environ.get("TELEGRAM_FORWARD_KEY", "")
    if not url:
        core.send(cid, "🤷 I didn't catch that. Try: <code>buy $100 of altai</code>, <code>sell half</code>, <code>take profits 30%</code>, "
                       "<code>close axis</code>, <code>what's my pnl</code>, <code>show positions</code> — or /help.", reply_to=m["message_id"]); return False
    body = {"text": text, "chat_id": cid, "message_id": m["message_id"], "reply_to_ca": reply_ca, "source": source}
    dedupe = f"freeform:{cid}:{m['message_id']}"
    if fwdq.forwarding_paused():
        fwdq.enqueue("freeform", body, dedupe, "automation disabled; forward paused", chat_id=cid); _busy_note(cid, m); return False
    raw = json.dumps(body).encode()
    h = {"Content-Type": "application/json", "User-Agent": "cg-memecoin-scanner-tg/2"}
    if key: h["Authorization"] = f"Bearer {key}"; h["X-Api-Key"] = key
    try:
        if not DRY:
            with urllib.request.urlopen(urllib.request.Request(url, data=raw, headers=h, method="POST"), timeout=15) as r: st = r.status
        else: st = "dry"
        log("forwarded", source, "status", st)
        tradeish = re.search(r"\b(buy|sell|ape|get into|put|close|dump|trim|take profits?)\b|\$\s?\d", text or "", re.I)
        core.send(cid, ("⏳ On it, researching… This needs the assistant, so expect ~1–3 min. "
                        + ("I won't double-fill: if you already traded this token in the last 10 min it'll ask first. Faster: <code>buy $50 of TICKER</code> or reply to the alert with <code>buy 50</code>." if tradeish
                           else "Quick stuff (buy/sell/pnl/positions) is instant if phrased like <code>buy $50 of TICKER</code>.")),
                  reply_to=m["message_id"]); return True
    except Exception as e:
        try: eb = e.read()[:200].decode(errors="replace") if hasattr(e, "read") else ""
        except Exception: eb = ""
        st = getattr(e, "code", type(e).__name__)
        if not fwdq.note_automation_disabled(st, eb, log=log):
            log("forward failed", st, _red(eb))
        fwdq.enqueue("freeform", body, dedupe, f"{st} {eb}", chat_id=cid)
        _busy_note(cid, m)
        return False
def confirm(c, cid, intent, reply_to, source):
    pid = core.add_pending(c, cid, {**intent, "source": source})
    kb = {"inline_keyboard": [[{"text": "✅ Yes", "callback_data": f"y:{pid}"}, {"text": "❌ No", "callback_data": f"n:{pid}"}]]}
    reply(c, cid, nl.describe(intent, core, c), reply_to, kb, ca=intent["ca"], kind="confirm")
def show_pick(c, cid, ticker, usd, hits, reply_to, source="nl"):
    hits = core.enrich_hits(hits)
    lines = [f"⚠️ <b>${core.esc(ticker)}</b> matches {len(hits)} tokens — pick the one you mean (never auto-picks a namesake):"]
    for h in hits:
        liq = h.get("liq"); age = h.get("age_h")
        liq_s = f"${liq:,.0f}" if liq else "?"; age_s = f"{age}h" if age is not None else "?"
        lines.append(f"• <b>{core.esc(h.get('symbol') or ticker)}</b> on <code>{h['network']}</code> · liq {liq_s} · age {age_s} · {(h.get('verdict') or '?')}"
                     f"\n  <code>{h['ca']}</code>")
    kb = core.pick_kb(hits, usd, ticker)
    return core.send(cid, "\n".join(lines), reply_to=reply_to, reply_markup=kb)
def natural(c, cid, m, text, reply_ca, source):
    it = nl.parse(text, reply_ca, c, core)
    if it is None: return forward(cid, m, text, reply_ca, source)
    if it["kind"] == "query": return run_query(c, cid, it["cmd"], m["message_id"])
    if it["kind"] == "error": return core.send(cid, "🤔 " + core.esc(it["msg"]), reply_to=m["message_id"])
    if it["kind"] == "ambiguous":
        return show_pick(c, cid, it["ticker"], it["usd"], it["hits"], m["message_id"], source)
    confirm(c, cid, it, m["message_id"], source)

# ---------- messages ----------
def on_message(m):
    chat = m.get("chat") or {}; cid = chat.get("id"); text = (m.get("text") or "").strip()
    if cid is None: return
    own = core.owner()
    if own is None:
        if chat.get("type") == "private" and text.split(" ")[0].split("@")[0] == "/start":
            jsave(core.OWNER, {"chat_id": cid, "username": (m.get("from") or {}).get("username"),
                               "first_name": (m.get("from") or {}).get("first_name"), "registered_at": core.now()})
            log("owner registered", cid); core.send(cid, "✅ Owner registered.\n\n" + core.HELP)
        return
    if cid != own["chat_id"]:
        seen = jload(UNAUTH, [])
        if cid not in seen: seen.append(cid); jsave(UNAUTH, seen); core.send(cid, "unauthorized", parse_mode=None); log("unauthorized chat", cid)
        return
    c = core.db()
    try:
        reply_ca, kind = (None, None); rt = m.get("reply_to_message")
        if rt: reply_ca, kind = core.msg_ctx(c, cid, rt["message_id"])
        # answer to a "Custom $" force_reply prompt
        if rt:
            p = c.execute("select * from prompts where chat_id=? and message_id=?", (cid, rt["message_id"])).fetchone()
            if p and text:
                mm = re.search(r"(\d+(?:\.\d+)?)", text.replace(",", ""))
                if not mm: return core.send(cid, "Need a number, e.g. 75", reply_to=m["message_id"])
                c.execute("delete from prompts where chat_id=? and message_id=?", (cid, rt["message_id"])); c.commit()
                out = core.buy(c, p["ca"], float(mm.group(1)), source="button-custom")
                reply(c, cid, out, m["message_id"], core.alert_kb(p["ca"]) if ok_trade(out) else None, ca=p["ca"])
                log("custom buy", p["ca"][:10]); return
        if m.get("voice") or m.get("audio"):
            return on_voice(c, cid, m, reply_ca)
        if not text: return
        q = tg_ext.QUICK.get(text.lower())
        if q: return run_query(c, cid, q, m["message_id"])
        cmd = text.split()[0].lower().split("@")[0]
        if cmd == "/report": return tg_ext.report(cid, m["message_id"])
        if cmd in ("/auto", "/aibook"): return tg_ext.ai_book(cid, m["message_id"])
        if cmd == "/autoreport": return tg_ext.autoreport(cid, m["message_id"])
        if cmd == "/compare": return tg_ext.compare(cid, m["message_id"])
        if cmd == "/keyboard": return tg_ext.install_keyboard(cid)
        if cmd == "/positions": return send_positions(c, cid, m["message_id"])
        if cmd == "/portfolio": return tg_ext.portfolio(cid, m["message_id"])
        if cmd in ("/mute", "/unmute"):
            arg = text.split()[1] if len(text.split()) > 1 else reply_ca
            ca, _ = core.resolve(arg, c) if arg else (None, None)
            if not ca: return core.send(cid, f"Usage: {cmd} &lt;CA|ticker&gt; (or reply to an alert)", reply_to=m["message_id"])
            core.set_mute(ca, cmd == "/mute", core.symbol_of(c, ca))
            return core.send(cid, f"{'🔕 Muted' if cmd=='/mute' else '🔔 Unmuted'} <code>{ca}</code>", reply_to=m["message_id"])
        if cmd == "/muted":
            mu = core.muted()
            return core.send(cid, "<b>Muted tokens</b>\n" + "\n".join(f"• {core.esc(v.get('symbol') or '?')} <code>{k}</code>" for k, v in mu.items()) if mu else "No muted tokens.")
        legacy = reply_ca and re.fullmatch(r"(buy\s+\$?\d+(\.\d+)?|sell\s+(\d+(\.\d+)?%?|all))", text, re.I)
        if text.startswith("/") or legacy:   # exact commands execute directly (no confirmation)
            out = core.handle(c, text, reply_ca)
            if out and isinstance(out, str) and out.startswith("AMBIGUOUS:"):
                import json as _j; d = _j.loads(out[len("AMBIGUOUS:"):])
                show_pick(c, cid, d["ticker"], d["usd"], d["hits"], m["message_id"], d.get("source") or "cmd"); return
            if out:
                tca = reply_ca
                if not tca:
                    try:
                        import sys; sys.path.insert(0, _ROOT + "/lib"); import addr as A
                        cas = A.find_cas(text); tca = cas[0] if cas else None
                    except Exception:
                        tca = (re.findall(r"0x[0-9a-f]{40}", text.lower()) or [None])[0]
                reply(c, cid, out, m["message_id"], core.alert_kb(tca) if ok_trade(out) and tca else None, ca=tca if ok_trade(out) else None)
                log("cmd", text[:60])
                if ok_trade(out) and rt and kind in ("alert", "positions"): refresh_msg(c, cid, rt["message_id"], kind, reply_ca)
            return
        natural(c, cid, m, text, reply_ca, "text"); log("nl", text[:60])
    finally: c.close()
def on_voice(c, cid, m, reply_ca):
    import voice
    f = m.get("voice") or m.get("audio")
    if (f.get("duration") or 0) > 120: return core.send(cid, "Voice note too long (max 2 min).", reply_to=m["message_id"])
    info = core.tg("getFile", file_id=f["file_id"])
    if not info.get("ok"): return core.send(cid, "⚠️ Couldn't download the voice note.", reply_to=m["message_id"])
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "v.oga")
        with urllib.request.urlopen(f"https://api.telegram.org/file/bot{core._tok()}/{info['result']['file_path']}", timeout=60) as r, open(p, "wb") as o:
            o.write(r.read())
        tick = [r[0] for r in c.execute("select distinct token from alerts where token is not null order by sent_at desc limit 30")] + \
               [r[0] for r in c.execute("select symbol from positions")]
        try: text, dt = voice.transcribe(p, list(dict.fromkeys(tick)))
        except Exception as e: log("transcribe error", type(e).__name__); return core.send(cid, "⚠️ Transcription failed.", reply_to=m["message_id"])
    log("voice transcribed", f"{dt:.1f}s", len(text), "chars")
    if not text: return core.send(cid, "🎙 Heard nothing intelligible — try again?", reply_to=m["message_id"])
    core.send(cid, f"🎙 Heard: “{core.esc(text)}”", reply_to=m["message_id"])
    natural(c, cid, m, text, reply_ca, "voice")

# ---------- buttons ----------
def on_callback(q):
    cid = ((q.get("message") or {}).get("chat") or {}).get("id"); data = q.get("data") or ""; msg = q.get("message") or {}
    own = core.owner(); mid = msg.get("message_id")
    def toast(t, alert=False): core.tg("answerCallbackQuery", callback_query_id=q["id"], text=t[:190], show_alert="true" if alert else None)
    if not own or (q.get("from") or {}).get("id") != own["chat_id"] or cid != own["chat_id"]: return toast("unauthorized")
    c = core.db()
    try:
        _, kind = core.msg_ctx(c, cid, mid)
        op, _, rest = data.partition(":")
        if tg_ext.handle_cb(c, cid, mid, op, rest, toast): log("button", op); return
        if op == "pick":
            # pick:<usd>:<network>:<ca>  (disambiguation after ticker namesake)
            parts = rest.split(":", 2)
            if len(parts) < 3: return toast("bad pick", True)
            usd, net, ca = parts[0], parts[1], parts[2]
            toast(f"Buying ${usd} on {net}…")
            out = core.buy(c, ca, float(usd), chain=net, source="pick", prefer_ca=ca)
            if ok_trade(out): tg_ext.decision(c, ca, "buy", float(usd))
            core.tg("editMessageReplyMarkup", chat_id=cid, message_id=mid, reply_markup={"inline_keyboard": []})
            reply(c, cid, out, mid, core.alert_kb(ca) if ok_trade(out) else None, ca=ca if ok_trade(out) else None)
        elif op == "b":
            usd, _, ca = rest.partition(":"); toast(f"Buying ${usd}…")
            out = core.buy(c, ca, float(usd), source="button", prefer_ca=ca)
            if ok_trade(out): tg_ext.decision(c, ca, "buy", float(usd))
            reply(c, cid, out, mid, ca=ca if ok_trade(out) else None)
            if ok_trade(out): refresh_msg(c, cid, mid, kind, ca)
        elif op == "s":
            amt, _, ca = rest.partition(":")
            if not c.execute("select 1 from positions where ca=?", (ca,)).fetchone(): return toast("No open position in this token.", True)
            toast(f"Selling {'all' if amt=='all' else amt+'%'}…")
            out = core.sell(c, ca, "all" if amt == "all" else amt + "%", source="button")
            reply(c, cid, out, mid, ca=ca if ok_trade(out) else None)
            if ok_trade(out): refresh_msg(c, cid, mid, kind, ca)
        elif op == "c":
            toast("Enter amount")
            r = core.send(cid, f"💵 How many USD of <b>{core.esc(core.symbol_of(c, rest))}</b> to paper-buy? Reply with a number.",
                          reply_to=mid, reply_markup={"force_reply": True, "input_field_placeholder": "e.g. 75", "selective": True})
            if r.get("ok"):
                c.execute("insert or replace into prompts values(?,?,?,?,?)", (cid, r["result"]["message_id"], rest, "custom_buy", time.time())); c.commit()
        elif op == "p":
            toast("Positions")
            if kind == "positions": refresh_msg(c, cid, mid, "positions", None)
            else: send_positions(c, cid, mid)
        elif op == "m":
            on = not core.is_muted(rest); core.set_mute(rest, on, core.symbol_of(c, rest))
            toast("🔕 Muted — scanner won't re-alert this token" if on else "🔔 Unmuted")
            core.tg("editMessageReplyMarkup", chat_id=cid, message_id=mid, reply_markup=core.alert_kb(rest))
        elif op in ("y", "n"):
            pid = int(rest); it, err = core.take_pending(c, pid, cid)
            if err: toast(f"This confirmation is {err}.", True); core.tg("editMessageReplyMarkup", chat_id=cid, message_id=mid, reply_markup={"inline_keyboard": []}); return
            base = re.sub(r"^🤖 Confirm paper trade:", "", msg.get("text") or "").strip()
            if op == "n":
                core.close_pending(c, pid, "cancelled"); toast("Cancelled")
                core.tg("editMessageText", chat_id=cid, message_id=mid, text="❌ Cancelled: " + base[:300]); return
            core.close_pending(c, pid, "done"); toast("Executing…")
            out = execute(c, it, "nl-" + it.get("source", "text"))
            core.tg("editMessageText", chat_id=cid, message_id=mid, text=("✅ Confirmed: " if ok_trade(out) else "⚠️ Failed: ") + base[:300])
            reply(c, cid, out, mid, core.alert_kb(it["ca"]) if ok_trade(out) else None, ca=it["ca"] if ok_trade(out) else None)
        else: toast("Unknown button")
        log("button", op)
    except Exception as e:
        log("callback error", traceback.format_exc(limit=3)); toast("⚠️ Error: " + _red(e)[:150], True)
    finally: c.close()
if __name__ == "__main__":
    main()
