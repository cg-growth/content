#!/usr/bin/env python3
"""CoinGecko API usage.

Paid keys (basic tier and above): GET /key on pro-api.coingecko.com is the source of truth.
Documented fields (docs.coingecko.com/reference/api-usage): plan, rate_limit_request_per_minute,
monthly_call_credit, current_total_monthly_calls, current_remaining_monthly_calls, and the
per-key fields api_key_monthly_call_credit, api_key_current_total_monthly_calls,
api_key_rate_limit_request_per_minute.

The demo tier's endpoint overview lists /ping and does not list /key. Usage there is the
API error (HTTP 429 or a credit-limit body) plus a local call count labeled as an estimate.
Nothing here changes the scan schedule.
"""
import os, sys, time
import os as _os
_ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
sys.path.insert(0, _ROOT + "/lib")
import common as C
import cgtier

_KEY = "cg_usage"
_HOUR = 3600
_LOW = 0.90


def _num(v):
    if v is None or v == "": return None
    try: return float(v)
    except (TypeError, ValueError): return None


def parse_key_body(data):
    """Map a GET /key JSON object to used / remaining / limit. No secrets."""
    if not isinstance(data, dict): return None
    per_limit = _num(data.get("api_key_monthly_call_credit"))
    if per_limit:
        used = _num(data.get("api_key_current_total_monthly_calls")) or 0
        remaining = max(0, per_limit - used)
        limit = per_limit
        rate = _num(data.get("api_key_rate_limit_request_per_minute"))
        if rate is None: rate = _num(data.get("rate_limit_request_per_minute"))
    else:
        limit = _num(data.get("monthly_call_credit"))
        used = _num(data.get("current_total_monthly_calls"))
        remaining = _num(data.get("current_remaining_monthly_calls"))
        if remaining is None and limit is not None and used is not None:
            remaining = max(0, limit - used)
        rate = _num(data.get("rate_limit_request_per_minute"))
    pct = (used / limit) if (limit and used is not None and limit > 0) else None
    return {
        "source": "api",
        "plan": data.get("plan") or "",
        "rate_limit_request_per_minute": rate,
        "monthly_limit": limit,
        "used": used,
        "remaining": remaining,
        "pct": None if pct is None else round(pct, 4),
    }


def demo_snapshot():
    return {
        "source": "estimate",
        "plan": "demo",
        "rate_limit_request_per_minute": None,
        "monthly_limit": None,
        "used": C.month_calls(),
        "remaining": None,
        "pct": None,
        "note": "GET /key is not included on the CoinGecko API Demo (free) plan. This count is a local estimate.",
    }


def store(snap):
    if not snap: return
    mc = C.mdb()
    try:
        rec = dict(snap)
        rec["at"] = time.time()
        rec["at_iso"] = C.now_iso()
        C.kv_set(mc, _KEY, rec); mc.commit()
    finally:
        mc.close()


def cached():
    mc = C.mdb()
    try: snap = C.kv_get(mc, _KEY)
    finally: mc.close()
    # A demo-tier estimate must not stand in for GET /key after the plan is paid.
    if isinstance(snap, dict) and snap.get("source") == "estimate" and cgtier.cg_has("key_usage"):
        return None
    if isinstance(snap, dict) and snap.get("source") == "estimate":
        snap = dict(snap); snap["used"] = C.month_calls()
    if isinstance(snap, dict): return snap
    if not cgtier.cg_has("key_usage"): return demo_snapshot()
    return None


def _age(snap):
    if not isinstance(snap, dict) or snap.get("at") is None: return 1e12
    try: return time.time() - float(snap["at"])
    except (TypeError, ValueError): return 1e12


def refresh(force=False, opener=None):
    """Refresh paid usage from GET /key. At most hourly, or after a 429 (force, still at most once a minute)."""
    if not cgtier.cg_has("key_usage"):
        snap = demo_snapshot(); store(snap); return snap
    prev = cached()
    age = _age(prev)
    if prev and prev.get("source") == "api" and age < (60 if force else _HOUR):
        return prev
    key = C.api_key()
    if not key: return prev
    status, data, err = cgtier._call(cgtier.PRO_ROOT + "/key", "x-cg-pro-api-key", key, opener)
    if err or status is None:
        return prev
    if C.plan_restricted(status, data):
        return prev
    if C.invalid_key_error(status, data):
        try:
            import plan_tips
            plan_tips.notify("invalid_key", signature=str(cgtier.err_code(data) or status))
        except Exception: pass
        return prev
    if status == 429:
        try:
            import plan_tips
            kind = C.limit_kind(429, data) or "rate"
            if kind == "credits":
                plan_tips.notify("credits_exhausted", signature=C.today()[:7] + ":0")
            else:
                plan_tips.notify("rate_limit")
        except Exception: pass
        return prev
    if status != 200:
        return prev
    snap = parse_key_body(data)
    if not snap: return prev
    store(snap)
    evaluate(snap)
    return snap


def evaluate(snap):
    """One 'running low' notice around 90%, and one 'used up' notice per exhaustion. Informational only."""
    if not snap or snap.get("source") != "api": return
    import plan_tips
    month = C.today()[:7]
    remaining = snap.get("remaining")
    pct = snap.get("pct")
    if remaining is not None and remaining <= 0:
        plan_tips.notify("credits_exhausted", signature=month + ":0")
        plan_tips.clear_event("credits_low")
        return
    if remaining is not None and remaining > 0:
        plan_tips.clear_event("credits_exhausted")
    if pct is not None and pct >= _LOW:
        plan_tips.notify("credits_low", signature=month + ":low")
    elif pct is not None and pct < _LOW:
        plan_tips.clear_event("credits_low")


def lines():
    snap = cached()
    if not snap: return ["usage      not checked yet"]
    if snap.get("source") == "estimate":
        return [f"usage       {snap.get('used', 0):.0f} local calls this month (estimate; a {cgtier.plan_label('demo', 'key')} has no GET /key)"]
    used = snap.get("used")
    limit = snap.get("monthly_limit")
    left = snap.get("remaining")
    rate = snap.get("rate_limit_request_per_minute")
    pct = snap.get("pct")
    pct_s = f"{pct * 100:.0f}%" if isinstance(pct, float) else "—"
    return [
        f"usage       {used if used is not None else '—'} used / {limit if limit is not None else '—'} monthly credits ({pct_s}), {left if left is not None else '—'} left",
        f"rate        {rate if rate is not None else '—'} / minute (from GET /key)",
    ]


def telegram_html():
    import utm
    snap = cached() or {}
    link = utm.pricing("tg-usage", source="grokbot")
    if snap.get("source") == "estimate":
        import cgtier
        body = (f"<b>CoinGecko usage</b> ({_esc(cgtier.plan_label('demo', 'key'))})\n"
                f"Local calls this month: {snap.get('used', 0):.0f} (estimate). "
                f"GET /key is not included on the {cgtier.plan_label('demo')}, so credits used and credits remaining are not reported here. "
                f"A used-up month shows up as an API error.")
    elif snap.get("source") == "api":
        import cgtier
        body = (f"<b>CoinGecko usage</b> ({_esc(cgtier.display_api_plan(snap.get('plan')))})\n"
                f"Used {snap.get('used') if snap.get('used') is not None else '—'} of "
                f"{snap.get('monthly_limit') if snap.get('monthly_limit') is not None else '—'} monthly credits. "
                f"Remaining: {snap.get('remaining') if snap.get('remaining') is not None else '—'}. "
                f"Rate limit: {snap.get('rate_limit_request_per_minute') if snap.get('rate_limit_request_per_minute') is not None else '—'} / minute.")
    else:
        body = "<b>CoinGecko usage</b>\nNot checked yet."
    return body + f'\n<a href="{utm.html_href(link)}">Plans</a>'


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--refresh" in argv:
        snap = refresh(force=True)
        print(snap.get("source") if snap else "none")
        return 0
    print("\n".join(lines()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
