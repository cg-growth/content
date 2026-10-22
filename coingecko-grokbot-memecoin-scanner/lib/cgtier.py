#!/usr/bin/env python3
"""Detect which CoinGecko API plan a key belongs to and which features that plan includes.

Sets no secrets. Prints the plan name and tier only. The demo tier uses https://api.coingecko.com
with header x-cg-demo-api-key. A paid key uses https://pro-api.coingecko.com with header
x-cg-pro-api-key. There is no keyless path.

  lib/cgtier.py --export     shell `export` lines for start.sh (stdout); notes on stderr
  lib/cgtier.py --json       tier record as JSON
  lib/cgtier.py              tier name only

MEMESCAN_CG_TIER=demo|basic|analyst skips the network check (tests, or when you already know).
"""
import json, os, sys, urllib.request, urllib.error
PRO_ROOT = "https://pro-api.coingecko.com/api/v3"
DEMO_ROOT = "https://api.coingecko.com/api/v3"
_RANK = {"demo": 0, "basic": 1, "analyst": 2}
# Minimum tier. WebSocket and /key need the basic tier or higher. Wallet, trader, holder and Megafilter
# endpoints need the analyst tier or higher (docs: endpoint overview, 💼).
_NEED = {
    "wallets": "analyst", "top_traders": "analyst", "top_holders": "analyst",
    "holders_chart": "analyst", "megafilter": "analyst", "ws": "basic", "key_usage": "basic",
}
_LABELS = {
    "megafilter": "Megafilter", "top_traders": "top traders", "top_holders": "top holders",
    "holders_chart": "holder history", "wallets": "wallet PnL and trades", "ws": "WebSocket price stream",
}
# Owner-facing names. Machine tiers stay demo | basic | analyst.
PLAN_LABELS = {
    "demo": "CoinGecko API Demo (free)",
    "basic": "CoinGecko API Basic",
    "analyst": "CoinGecko API Analyst",
}

def plan_label(tier=None, kind="plan"):
    """Full product name, e.g. 'CoinGecko API Demo (free) plan' or '... key'."""
    t = (tier if tier is not None else current() or "analyst")
    t = str(t).strip().lower()
    if t not in PLAN_LABELS: t = "analyst"
    return PLAN_LABELS[t] + (" key" if kind == "key" else " plan")

def needs_plan(min_tier):
    """'a CoinGecko API Analyst plan or higher'."""
    return "a " + plan_label(min_tier) + " or higher"

def display_api_plan(name):
    """Name a plan string from GET /key without leaving it as a bare word."""
    n = (name or "").strip()
    if not n or n.lower() in ("paid", "none"): return plan_label("analyst")
    if n.lower() in PLAN_LABELS: return plan_label(n.lower())
    return "CoinGecko API " + n + " plan"

class ProbeError(Exception):
    def __init__(self, message, code=3):
        super().__init__(message); self.code = code

def _saved_tier():
    """Tier written by the last successful start. Used by status.sh, which does not inherit CG_TIER."""
    try:
        import common as C
        mc = C.mdb()
        try: rec = C.kv_get(mc, "cg_tier") or {}
        finally: mc.close()
        t = (rec.get("tier") or "").strip().lower() if isinstance(rec, dict) else ""
        return t if t in _RANK else ""
    except Exception:
        return ""

def current():
    t = os.environ.get("CG_TIER", "").strip().lower()
    if t in _RANK: return t
    if os.environ.get("COINGECKO_DEMO_API_KEY", "").strip() and not os.environ.get("COINGECKO_PRO_API_KEY", "").strip():
        return "demo"
    saved = _saved_tier()
    if saved: return saved
    return "analyst"

def cg_has(feature, tier_name=None):
    need = _NEED.get(feature)
    if not need: return False
    return _RANK.get(tier_name or current(), 0) >= _RANK[need]

def feature_summary(tier_name=None):
    t = tier_name or current()
    on, off = [], []
    for key, label in _LABELS.items():
        (on if cg_has(key, t) else off).append(label)
    return on, off

def unavailable(tier_name=None):
    t = tier_name or current()
    if t == "demo": return "not included with a " + plan_label("demo", "key")
    return "needs " + needs_plan("analyst")

def tier_from_plan(name):
    """Map /key `plan` to demo | basic | analyst. analyst here means that tier or higher (Lite, Pro, Enterprise)."""
    n = (name or "").strip().lower()
    if "demo" in n: return "demo"
    if n == "basic" or n.startswith("basic"): return "basic"
    return "analyst"

def err_code(data):
    import common as C
    return C._err_code(data)

def _call(url, header, key, opener=None):
    open_fn = opener or urllib.request.urlopen
    req = urllib.request.Request(url, headers={"accept": "application/json", header: key, "User-Agent": "cg-memecoin-scanner/1.0"})
    try:
        with open_fn(req, timeout=20) as r:
            raw = r.read(); status = getattr(r, "status", None) or getattr(r, "code", 200) or 200
            try: data = json.loads(raw.decode() or "{}")
            except Exception: data = {}
            return int(status), data, None
    except urllib.error.HTTPError as e:
        raw = e.read() if getattr(e, "fp", None) else b""
        try: data = json.loads(raw.decode() or "{}")
        except Exception: data = {}
        return int(e.code), data, None
    except Exception as e:
        return None, {}, type(e).__name__

def _result(tier, base, header, key_env, plan, monthly, rate, note):
    return {"tier": tier, "base": base, "header": header, "key_env": key_env, "plan": plan or "",
            "monthly_call_credit": monthly, "rate_limit_request_per_minute": rate, "note": note or ""}

def _paid_from_key(key, key_env, opener, note_if_moved):
    status, data, net_err = _call(PRO_ROOT + "/key", "x-cg-pro-api-key", key, opener)
    if net_err:
        raise ProbeError(f"Could not reach CoinGecko to detect the plan ({net_err}).", 4)
    if status == 429:
        raise ProbeError("CoinGecko rate limit while detecting the plan (HTTP 429). Nothing was started. Try again shortly.", 4)
    if status and status >= 500:
        raise ProbeError(f"CoinGecko /key returned HTTP {status}. Try again shortly.", 4)
    if status == 200 and isinstance(data, dict) and (data.get("plan") or "monthly_call_credit" in data):
        tier = tier_from_plan(data.get("plan"))
        if tier == "demo":
            return None
        rec = _result(tier, PRO_ROOT, "x-cg-pro-api-key", key_env, data.get("plan"),
                      data.get("monthly_call_credit"), data.get("rate_limit_request_per_minute"), note_if_moved)
        try:
            import usage
            rec["usage"] = usage.parse_key_body(data)
        except Exception:
            pass
        return rec
    return None

def _demo_from_key(key, key_env, opener, note):
    status, data, net_err = _call(DEMO_ROOT + "/onchain/networks?page=1", "x-cg-demo-api-key", key, opener)
    if net_err:
        raise ProbeError(f"Could not reach CoinGecko to detect the plan ({net_err}).", 4)
    if status == 429:
        raise ProbeError("CoinGecko rate limit while detecting the plan (HTTP 429). Nothing was started. Try again shortly.", 4)
    if status and status >= 500:
        raise ProbeError(f"CoinGecko returned HTTP {status} while detecting the plan. Try again shortly.", 4)
    if status == 200 and isinstance(data, dict):
        return _result("demo", DEMO_ROOT, "x-cg-demo-api-key", key_env, "demo", None, None, note)
    return None

def detect(pro_key="", demo_key="", opener=None):
    """Return a tier record or raise ProbeError. Never includes the key."""
    pro_key, demo_key = (pro_key or "").strip(), (demo_key or "").strip()
    if not pro_key and not demo_key:
        raise ProbeError("No CoinGecko API key is set. Set COINGECKO_DEMO_API_KEY or COINGECKO_PRO_API_KEY.", 2)
    if pro_key:
        hit = _paid_from_key(pro_key, "COINGECKO_PRO_API_KEY", opener, "")
        if hit: return hit
    if demo_key:
        hit = _demo_from_key(demo_key, "COINGECKO_DEMO_API_KEY", opener, "")
        if hit: return hit
        hit = _paid_from_key(demo_key, "COINGECKO_DEMO_API_KEY", opener,
                             "This paid key is in COINGECKO_DEMO_API_KEY. It works. You can move it to COINGECKO_PRO_API_KEY.")
        if hit: return hit
    if pro_key:
        hit = _demo_from_key(pro_key, "COINGECKO_PRO_API_KEY", opener,
                             "This CoinGecko API Demo (free) key is in COINGECKO_PRO_API_KEY. It works. You can move it to COINGECKO_DEMO_API_KEY.")
        if hit: return hit
    raise ProbeError("CoinGecko did not accept this API key. Check COINGECKO_DEMO_API_KEY or COINGECKO_PRO_API_KEY.", 3)

def assumed_result():
    name = os.environ.get("MEMESCAN_CG_TIER", "").strip().lower()
    if name not in _RANK: return None
    pro = os.environ.get("COINGECKO_PRO_API_KEY", "").strip()
    demo = os.environ.get("COINGECKO_DEMO_API_KEY", "").strip()
    if not pro and not demo: return None
    if name == "demo":
        env = "COINGECKO_DEMO_API_KEY" if demo else "COINGECKO_PRO_API_KEY"
        return _result("demo", DEMO_ROOT, "x-cg-demo-api-key", env, "demo", None, None, "")
    env = "COINGECKO_PRO_API_KEY" if pro else "COINGECKO_DEMO_API_KEY"
    return _result(name, PRO_ROOT, "x-cg-pro-api-key", env, name, None, None, "")

def export_sh(result):
    import shlex
    lines = [
        f"export CG_TIER={shlex.quote(result['tier'])}",
        f"export CG_BASE={shlex.quote(result['base'])}",
        f"export CG_AUTH_HEADER={shlex.quote(result['header'])}",
        f"export CG_KEY_ENV={shlex.quote(result['key_env'])}",
        f"export CG_PLAN={shlex.quote(str(result.get('plan') or ''))}",
    ]
    return "\n".join(lines)

def save(result):
    """Cache the tier record in market.db. The key itself is not stored."""
    try:
        import common as C
        mc = C.mdb()
        rec = {k: result.get(k) for k in ("tier", "plan", "base", "header", "key_env", "monthly_call_credit", "rate_limit_request_per_minute", "note")}
        rec["at"] = C.now_iso()
        C.kv_set(mc, "cg_tier", rec); mc.commit(); mc.close()
    except Exception:
        pass

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    assume = assumed_result()
    try:
        result = assume if assume else detect(os.environ.get("COINGECKO_PRO_API_KEY", ""), os.environ.get("COINGECKO_DEMO_API_KEY", ""))
    except ProbeError as e:
        print(str(e), file=sys.stderr)
        try:
            import plan_tips
            if e.code == 3: plan_tips.notify("invalid_key", signature="startup-" + str(e.code))
        except Exception:
            pass
        return e.code
    save(result)
    try:
        import usage
        if result.get("usage"):
            usage.store(result["usage"]); usage.evaluate(result["usage"])
        elif result.get("tier") == "demo":
            usage.store(usage.demo_snapshot())
    except Exception:
        pass
    if result.get("note"): print(result["note"], file=sys.stderr)
    shown = display_api_plan(result.get("plan")) if result.get("plan") else plan_label(result["tier"])
    print(f"Detected plan: {shown}", file=sys.stderr)
    if "--export" in argv: print(export_sh(result))
    elif "--json" in argv:
        print(json.dumps({k: result[k] for k in ("tier", "plan", "base", "header", "key_env", "monthly_call_credit", "rate_limit_request_per_minute")}))
    else: print(result["tier"])
    return 0

if __name__ == "__main__":
    sys.exit(main())
