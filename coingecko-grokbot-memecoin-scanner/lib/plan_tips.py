#!/usr/bin/env python3
"""Capability notes: tell the owner when a feature needs a higher CoinGecko plan, or when credits or the rate limit run out.

Each note is its own short message (Telegram, when TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set,
and a queue the Grok Bot chat relays). It is not appended to a scan alert.
Missing-feature notes: at most once a day. Credit exhaustion and an invalid key: once per event, and
they still send when plan tips are off. Set plan_tips.enabled to false to hide the other notes.
Scans are not slowed or paused.
"""
import json, os, sys, time, uuid
import os as _os
_ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
sys.path.insert(0, _ROOT + "/lib")
import common as C
import utm
DAY = 86400
WEEK = 7 * 86400
WINDOWS = {"wallet_gap": DAY, "rate_limit": DAY, "weekly": WEEK}
CRITICAL = {"credits_exhausted", "invalid_key"}
TRIGGERS = ("rate_limit", "wallet_gap", "weekly", "credits_exhausted", "credits_low", "invalid_key")
_SENT = "plan_tips_sent"
_EVENTS = "plan_tip_events"
_QUEUE = "plan_notices"
_FLAG = "plan_tips_enabled"

def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def enabled(mc=None):
    own = mc is None; mc = mc or C.mdb()
    try:
        flag = C.kv_get(mc, _FLAG, None)
        if flag is not None: return bool(flag)
        try: return bool((C.risk_cfg().get("plan_tips") or {}).get("enabled", True))
        except Exception: return True
    finally:
        if own: mc.close()

def set_enabled(on, mc=None):
    own = mc is None; mc = mc or C.mdb()
    try:
        C.kv_set(mc, _FLAG, bool(on)); mc.commit()
    finally:
        if own: mc.close()

def _sent(mc):
    v = C.kv_get(mc, _SENT, {}) or {}
    return v if isinstance(v, dict) else {}

def _window(trigger):
    return WINDOWS.get(trigger, DAY)

def due(trigger, now=None, mc=None):
    if trigger not in WINDOWS: return False
    own = mc is None; mc = mc or C.mdb()
    try:
        if not enabled(mc): return False
        last = _sent(mc).get(trigger)
        if last is None: return True
        try: last_ts = float(last)
        except (TypeError, ValueError): return True
        now = time.time() if now is None else float(now)
        return (now - last_ts) >= _window(trigger)
    finally:
        if own: mc.close()

def _events(mc):
    v = C.kv_get(mc, _EVENTS, {}) or {}
    return v if isinstance(v, dict) else {}

def event_open(trigger, signature, mc=None):
    """True when this exact event has not been sent yet. Ignores plan_tips.enabled."""
    own = mc is None; mc = mc or C.mdb()
    try:
        prev = _events(mc).get(trigger) or {}
        return prev.get("sig") != signature
    finally:
        if own: mc.close()

def clear_event(trigger, mc=None):
    own = mc is None; mc = mc or C.mdb()
    try:
        ev = _events(mc)
        if trigger in ev:
            ev.pop(trigger, None)
            C.kv_set(mc, _EVENTS, ev); mc.commit()
    finally:
        if own: mc.close()

def mark(trigger, now=None, mc=None):
    own = mc is None; mc = mc or C.mdb()
    try:
        sent = _sent(mc); sent[trigger] = time.time() if now is None else float(now)
        C.kv_set(mc, _SENT, sent); mc.commit()
    finally:
        if own: mc.close()

def _body(trigger):
    if trigger == "credits_exhausted":
        return ("Your CoinGecko API credits for this month are used up. "
                "Scans keep running on the normal schedule and will succeed again when the limit allows. "
                "A CoinGecko API plan with a higher monthly cap covers more calls.")
    if trigger == "credits_low":
        return ("About 90% of this month's CoinGecko API credits are used. "
                "Scans keep running on the normal schedule. A CoinGecko API plan with a higher monthly cap covers more calls.")
    if trigger == "invalid_key":
        return ("CoinGecko rejected this API key. Scans keep running and will succeed again when the key is valid. "
                "New to CoinGecko API? Sign up on the CoinGecko API pricing page first. Sign-up opens the developer dashboard, where you copy the key. "
                "Already have a CoinGecko API account? Copy the key from your developer dashboard.")
    if trigger == "rate_limit":
        return ("CoinGecko returned HTTP 429 (per-minute rate limit). "
                "Scans keep running on the normal schedule and will succeed again when the limit allows. "
                "A CoinGecko API plan with a higher per-minute limit allows more calls.")
    if trigger == "wallet_gap":
        import cgtier
        return ("Top-trader and wallet checks (spotting smart money vs bots) need " + cgtier.needs_plan("analyst") +
                ", so this scan skipped them. Holder history and Megafilter need that plan too.")
    if trigger == "weekly":
        import cgtier
        return (f"Your plan: {cgtier.plan_label()}. Top-trader and wallet checks (spotting smart money vs bots) skipped this month: {wallet_skips()}. "
                f"Those checks and Megafilter need {cgtier.needs_plan('analyst')}. The WebSocket price stream needs {cgtier.needs_plan('basic')}.")
    return ""

def _link(trigger):
    return utm.pricing("tg-plan-tip", source="grokbot"), "Plans"

def message(trigger, html=False):
    body = _body(trigger)
    if not body: return ""
    if trigger == "invalid_key":
        price = utm.pricing("tg-invalid-key-pricing", source="grokbot")
        dash = utm.developer_dashboard("tg-invalid-key", source="grokbot")
        if html:
            return (_esc(body) + f' <a href="{utm.html_href(price)}">CoinGecko API pricing</a>'
                    f' · <a href="{utm.html_href(dash)}">Developer Dashboard</a>')
        return body + " CoinGecko API pricing: " + price + " Developer Dashboard: " + dash
    link, label = _link(trigger)
    if html: return _esc(body) + f' <a href="{utm.html_href(link)}">{label}</a>'
    return body + " " + label + ": " + link

def _notices_path():
    return os.environ.get("MEMESCAN_NOTICES_FILE") or os.path.join(C.BASE, "notices", "pending.json")

def pending(mc=None):
    own = mc is None; mc = mc or C.mdb()
    try:
        q = C.kv_get(mc, _QUEUE, []) or []
        return q if isinstance(q, list) else []
    finally:
        if own: mc.close()

def _mirror(q):
    path = _notices_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        json.dump(q, open(tmp, "w"), indent=1)
        os.replace(tmp, path)
    except Exception: pass

def ack(notice_id, mc=None):
    own = mc is None; mc = mc or C.mdb()
    try:
        q = [n for n in pending(mc) if str(n.get("id")) != str(notice_id)]
        C.kv_set(mc, _QUEUE, q); mc.commit(); _mirror(q)
    finally:
        if own: mc.close()

def _enqueue(trigger, plain, html):
    mc = C.mdb()
    try:
        q = pending(mc)
        item = {"id": uuid.uuid4().hex[:12], "trigger": trigger, "text": plain, "html": html, "at": C.now_iso()}
        q.append(item)
        q = q[-50:]
        C.kv_set(mc, _QUEUE, q)
        C.kv_set(mc, "plan_tip_latest", {"trigger": trigger, "at": item["at"], "text": plain})
        mc.commit(); _mirror(q)
        return item
    finally:
        mc.close()

def _telegram_send(html):
    """Telegram only when both the bot token and the chat id are set. Returns True if Telegram accepted it."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat: return False
    try:
        sys.path.insert(0, _ROOT + "/telegram")
        import core
        r = core.send(chat, html)
        return bool(r and r.get("ok"))
    except Exception as e:
        C.logger("plan")("telegram not sent", C.redact(e))
        return False

def _weekly_relevant():
    import cgtier
    if cgtier.current() != "analyst": return True
    mc = C.mdb()
    try: limited = bool(C.kv_get(mc, "cg_limit_status"))
    finally: mc.close()
    return bool(wallet_skips() or limited)

def notify(trigger, signature=None):
    """Queue one short note for the Grok Bot chat and send it on Telegram when a chat id is set.
    Returns True when the note was accepted (queued). Does not change the scan schedule."""
    if trigger not in TRIGGERS: return False
    critical = trigger in CRITICAL
    if not critical and not enabled(): return False
    now = time.time()
    if trigger == "weekly" and not _weekly_relevant(): return False
    if trigger in WINDOWS:
        if not due(trigger, now): return False
    else:
        signature = signature or trigger
        if not event_open(trigger, signature): return False
    plain = message(trigger, html=False)
    html = message(trigger, html=True)
    if not plain: return False
    _enqueue(trigger, plain, html)
    _telegram_send(html)
    if trigger in WINDOWS: mark(trigger, now)
    else:
        mc = C.mdb()
        try:
            ev = _events(mc); ev[trigger] = {"sig": signature, "at": now}
            C.kv_set(mc, _EVENTS, ev); mc.commit()
        finally:
            mc.close()
    return True

def note_wallet_skip():
    mc = C.mdb()
    try:
        key = "wallet_skips_" + C.today()[:7]
        n = C.kv_get(mc, key, 0) or 0
        C.kv_set(mc, key, int(n) + 1); mc.commit()
    finally:
        mc.close()

def wallet_skips():
    mc = C.mdb()
    try: return int(C.kv_get(mc, "wallet_skips_" + C.today()[:7], 0) or 0)
    finally: mc.close()

def weekly_recap_line():
    """Send the weekly note on its own. Returns empty so it is not mixed into the recap caption."""
    notify("weekly")
    return ""

def status_text():
    import cgtier
    t = cgtier.current()
    _on, off = cgtier.feature_summary(t)
    lines = [f"plan        {cgtier.plan_label(t)}"]
    if off:
        lines.append("unavailable " + ", ".join(off) + f" ({cgtier.unavailable(t)})")
    else:
        lines.append("unavailable none")
    try:
        import usage
        lines.extend(usage.lines())
    except Exception:
        lines.append(f"calls       {C.month_calls():.0f} this month (local count, estimate)")
    mc = C.mdb()
    try:
        lim = C.kv_get(mc, "cg_limit_status")
        saved = C.kv_get(mc, "cg_tier") or {}
    finally:
        mc.close()
    if isinstance(saved, dict) and saved.get("monthly_call_credit"):
        lines.append(f"allowance   {saved.get('monthly_call_credit')} calls/month reported at last plan check")
    if lim:
        lines.append(f"limit       HTTP {lim.get('code')} ({lim.get('kind')}) at {lim.get('at')} — next try is on the normal schedule")
    lines.append("plan tips   " + ("on" if enabled() else "off"))
    return "\n".join(lines)

def status_html():
    import cgtier
    t = cgtier.current()
    _on, off = cgtier.feature_summary(t)
    link = utm.pricing("telegram-plan", source="grokbot")
    off_s = ", ".join(off) if off else "none"
    return (f"<b>{_esc(cgtier.plan_label(t))}</b>\n"
            f"Not included: {_esc(off_s)}\n"
            f"Plan tips: {'on' if enabled() else 'off'}. Set plan_tips.enabled to false to hide plan-related tips. Credits used up and an invalid key still send.\n"
            f'<a href="{utm.html_href(link)}">Plans</a>')

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else "status"
    if cmd == "due" and len(argv) > 1:
        print("yes" if due(argv[1]) else "no"); return 0
    if cmd == "claim" and len(argv) > 1:
        if due(argv[1]):
            print(message(argv[1])); mark(argv[1])
        return 0
    if cmd == "pending":
        print(json.dumps(pending(), indent=1)); return 0
    if cmd == "ack" and len(argv) > 1:
        ack(argv[1]); return 0
    if cmd == "off":
        set_enabled(False); print("plan tips off"); return 0
    if cmd == "on":
        set_enabled(True); print("plan tips on"); return 0
    print(status_text()); return 0

if __name__ == "__main__":
    sys.exit(main())
