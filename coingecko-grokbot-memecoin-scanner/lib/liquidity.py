"""Liquidity removal, reserve drops, and realistic paper marks. Paper only.

Liquidity-event detail (GET /onchain/networks/{network}/pools/{pool}/liquidity_events)
is fetched only on a CoinGecko API Analyst plan or higher, and only for Solana
PumpSwap and Meteora DAMM v2 pools. Other chains and DEXes are skipped with no call.
Amounts on that endpoint are always positive; kind is the direction. History starts May 2026.
"""
import time, datetime as D
_DEFAULTS = {
    "large_remove_pct_of_reserve": 20,
    "min_remove_usd": 500,
    "events_per_page": 20,
    "sharp_drop_pct": 40,
    "sharp_drop_window_min": 5,
    "exit_max_impact_pct": 50,
    "partial_impact_pct": 5,
    "reserve_refresh_s": 60,
    "alert_cooldown_s": 1800,
}
_DEX = {"pumpswap", "meteora-damm-v2"}
_ALIASES = {
    "pump-swap": "pumpswap",
    "pump_swap": "pumpswap",
    "meteora-dammv2": "meteora-damm-v2",
    "meteora-damm-v-2": "meteora-damm-v2",
    "meteora_damm_v2": "meteora-damm-v2",
}
_DEX_KEY = "pool_dex"
_ALERT_KEY = "liq_alert_at"


def settings():
    """risk.json liquidity section wins over these defaults. Keys starting with _ are docs.
    On the AI book, auto/policy.json risk_overrides.liquidity wins over risk.json."""
    out = dict(_DEFAULTS)
    try:
        import os, common as C
        raw = dict(C.risk_cfg().get("liquidity") or {})
        if os.environ.get("BOOK") == "auto":
            try:
                import json
                pol = json.load(open(f"{C.BASE}/auto/policy.json"))
                ov = (pol.get("risk_overrides") or {}).get("liquidity") or {}
                if isinstance(ov, dict): raw.update(ov)
            except Exception:
                pass
        if isinstance(raw, dict):
            for k, v in raw.items():
                if str(k).startswith("_") or k not in _DEFAULTS: continue
                out[k] = v
    except Exception:
        pass
    return out


def nsfw_discard():
    """Owner toggle. Default true. risk.json nsfw.discard false keeps the flag as data only."""
    try:
        import common as C
        block = C.risk_cfg().get("nsfw")
        if isinstance(block, dict) and "discard" in block: return bool(block["discard"])
    except Exception:
        pass
    return True


def flagged_nsfw(info):
    v = (info or {}).get("is_nsfw") if isinstance(info, dict) else None
    if isinstance(v, str): return v.strip().lower() in ("true", "1", "yes")
    return v is True or v == 1


def nsfw_reason(info):
    if not flagged_nsfw(info): return ""
    return "NSFW token (name or symbol flagged)"


def dex_key(raw):
    s = (raw or "").strip().lower().replace("_", "-")
    if not s: return ""
    for prefix in ("solana-",):
        if s.startswith(prefix): s = s[len(prefix):]
    return _ALIASES.get(s, s)


def dex_from_pool(pool):
    rel = ((pool or {}).get("relationships") or {}).get("dex") or {}
    data = rel.get("data") if isinstance(rel, dict) else None
    if isinstance(data, dict): return dex_key(data.get("id") or "")
    return ""


def supported_pool(network, dex):
    return (network or "").lower() == "solana" and dex_key(dex) in _DEX


def can_fetch(network, dex, tier=None):
    """False on a CoinGecko API Demo (free) key, the CoinGecko API Basic plan, and unsupported pools.
    Unknown DEX is unsupported: no liquidity-events call (those pools return HTTP 400)."""
    import cgtier
    if not cgtier.cg_has("liquidity_events", tier): return False
    return supported_pool(network, dex)


def _f(x, d=0.0):
    try: return float(x)
    except (TypeError, ValueError): return d


def usd_k(n):
    n = _f(n)
    sign = "-" if n < 0 else ""
    n = abs(n)
    if n >= 1_000_000:
        v = n / 1_000_000
        return f"{sign}${v:.0f}m" if v >= 10 else f"{sign}${v:.1f}m"
    if n >= 1000:
        v = n / 1000
        return f"{sign}${v:.0f}k" if v >= 10 else f"{sign}${v:.1f}k"
    return f"{sign}${n:,.0f}"


def ago(ts):
    try:
        if isinstance(ts, (int, float)): t = float(ts)
        else: t = D.datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except Exception:
        return "recently"
    s = max(0, time.time() - t)
    if s < 45: return "just now"
    if s < 90: return "1 min ago"
    m = int(round(s / 60))
    if m < 60: return f"{m} min ago"
    h = int(round(s / 3600))
    if h < 48: return f"{h} hr ago"
    return f"{h // 24} days ago"


def remember_dex(mc, network, pool, dex):
    dex = dex_key(dex)
    if not mc or not dex or not pool: return
    import common as C
    cur = C.kv_get(mc, _DEX_KEY, {}) or {}
    if not isinstance(cur, dict): cur = {}
    key = f"{network}:{pool}"
    if cur.get(key) == dex: return
    cur[key] = dex
    C.kv_set(mc, _DEX_KEY, cur)


def known_dex(mc, network, pool):
    if not mc or not pool: return ""
    import common as C
    cur = C.kv_get(mc, _DEX_KEY, {}) or {}
    if not isinstance(cur, dict): return ""
    return dex_key(cur.get(f"{network}:{pool}") or "")


def fetch_removes(network, pool, mc=None, per_page=None):
    """Recent remove events. Caller must have passed can_fetch. Empty list on no events or a non-200."""
    import common as C
    n = int(per_page or settings()["events_per_page"] or 20)
    n = min(50, max(1, n))
    d = C.cg(f"/networks/{network}/pools/{pool}/liquidity_events", {"kind": "remove", "per_page": n}, mc)
    if not d: return []
    out = []
    for row in d.get("data") or []:
        a = row.get("attributes") if isinstance(row, dict) else None
        if not isinstance(a, dict): continue
        if a.get("kind") and a.get("kind") != "remove": continue
        out.append(a)
    return out


def _same_addr(a, b, network):
    import addr as A
    if not a or not b: return False
    return A.norm(a, network) == A.norm(b, network)


def assess_removes(events, developer, reserve, network):
    """-> {reason, deployer, volume, pct, at} or reason '' when nothing flags.
    A removal by the developer address, or a removal large versus reserve, is a Discard reason."""
    cfg = settings()
    reserve = _f(reserve, 0)
    pct_need = _f(cfg["large_remove_pct_of_reserve"], 20)
    usd_need = _f(cfg["min_remove_usd"], 500)
    best = None
    deployer_hit = None
    for a in events or []:
        vol = _f(a.get("volume_in_usd"))
        who = a.get("tx_from_address") or ""
        is_dev = _same_addr(who, developer, network)
        rel = (vol / reserve * 100) if reserve > 0 else 0
        large = reserve > 0 and rel + 1e-9 >= pct_need and vol + 1e-9 >= usd_need
        if not is_dev and not large: continue
        rec = {"volume": vol, "pct": rel, "at": a.get("block_timestamp"), "deployer": is_dev, "address": who}
        if is_dev and (deployer_hit is None or vol > deployer_hit["volume"]): deployer_hit = rec
        if best is None or vol > best["volume"]: best = rec
    hit = deployer_hit or best
    if not hit: return {"reason": "", "deployer": False, "volume": 0, "pct": 0, "at": None}
    if hit["deployer"]:
        reason = f"deployer removed {usd_k(hit['volume'])}"
    else:
        reason = f"removed {usd_k(hit['volume'])} ({hit['pct']:.0f}% of reserve)"
    hit["reason"] = reason
    return hit


def research_events(network, pool, dex, developer, reserve, mc=None):
    """Before a verdict. No call when the plan or the pool cannot serve liquidity events."""
    dex = dex_key(dex)
    if (network or "").lower() != "solana" or not dex or not supported_pool(network, dex):
        return {"skipped": "unsupported", "called": False, "reason": ""}
    if not can_fetch(network, dex):
        return {"skipped": "plan", "called": False, "reason": ""}
    rows = fetch_removes(network, pool, mc)
    hit = assess_removes(rows, developer, reserve, network)
    return {"skipped": None, "called": True, "reason": hit.get("reason") or "", "events": len(rows),
            "deployer": bool(hit.get("deployer")), "volume": hit.get("volume") or 0}


def mark(qty, price, liq, network):
    """Paper value of an open position.
    Illiquid / rugged (value 0) when a full exit would exceed exit_max_impact_pct.
    Otherwise the value is what the pool would pay (constant-product, DEX fee, gas), not the last price.
    """
    cfg = settings()
    if price is None or qty is None:
        return {"value": None, "status": "", "impact_pct": None, "mid": None, "payout": None}
    try: mid = float(qty) * float(price)
    except (TypeError, ValueError):
        return {"value": None, "status": "", "impact_pct": None, "mid": None, "payout": None}
    if liq is None:
        return {"value": mid, "status": "", "impact_pct": None, "mid": mid, "payout": None}
    import clips
    f = clips.fill(mid, _f(liq), network or "")
    impact = f.get("impact_pct") or 0
    max_imp = _f(cfg["exit_max_impact_pct"], 50) / 100.0
    if mid > 0 and (_f(liq) <= 0 or impact + 1e-12 >= max_imp):
        return {"value": 0.0, "status": "illiquid / rugged", "impact_pct": impact, "mid": mid, "payout": 0.0}
    partial_at = _f(cfg["partial_impact_pct"], 5) / 100.0
    status = ""
    if mid > 0 and (impact + 1e-12 >= partial_at or (f["net"] < mid * (1 - partial_at))):
        status = "partial liquidity"
    return {"value": f["net"], "status": status, "impact_pct": impact, "mid": mid, "payout": f["net"]}


def should_auto_exit(book, plan_auto, status):
    """AI book writes off an illiquid position. auto off is the owner override and skips the exit."""
    if status != "illiquid / rugged": return False
    if not plan_auto: return False
    return (book or "") == "auto"


def record_reserve(mc, network, ca, pool, reserve, total=None, ts=None):
    if mc is None or reserve is None or not ca: return
    mc.execute("insert into prices values(?,?,?,?,?,?,?,?,?)",
               (network, ca, None, float(reserve), None if total is None else float(total), None, None, pool, int(ts or time.time())))


def fresh_reserve(mc, ca, pool, max_age):
    if mc is None or not ca or not pool: return None
    cut = time.time() - max_age
    r = mc.execute("select r, t from prices where ta=? and r is not null and pa=? and t>=? order by t desc limit 1",
                   (ca, pool, cut)).fetchone()
    if not r or r["r"] is None: return None
    return float(r["r"]), r["t"]


def cached_pool_reserve(ca, pool, max_age=3600):
    """Latest stored reserve for this pool. No HTTP."""
    try:
        import common as C
        mc = C.mdb()
        try:
            hit = fresh_reserve(mc, ca, pool, max_age)
            return None if not hit else hit[0]
        finally:
            mc.close()
    except Exception:
        return None


def _parse_pool(d):
    data = (d or {}).get("data") or {}
    if not isinstance(data, dict): return None, ""
    attrs = data.get("attributes") or {}
    reserve = attrs.get("reserve_in_usd")
    return (None if reserve in (None, "") else _f(reserve)), dex_from_pool(data)


def ensure_reserve(mc, network, ca, pool, max_age=None, fetch=True):
    """Return (reserve_usd, source). Uses a fresh stored sample, else one pool GET."""
    max_age = settings()["reserve_refresh_s"] if max_age is None else max_age
    hit = fresh_reserve(mc, ca, pool, max_age)
    if hit: return hit[0], "stored"
    if not fetch: return None
    import common as C
    d = C.cg(f"/networks/{network}/pools/{pool}", None, mc) or {}
    reserve, dex = _parse_pool(d)
    if dex: remember_dex(mc, network, pool, dex)
    if reserve is None: return None
    record_reserve(mc, network, ca, pool, reserve)
    try: mc.commit()
    except Exception: pass
    return reserve, "rest"


def series_drop(rows):
    if not rows or len(rows) < 2: return None
    vals = [v for v, _t in rows if v is not None]
    if len(vals) < 2: return None
    mx = max(vals)
    last = vals[-1]
    if mx <= 0: return None
    return {"pct": (1 - last / mx) * 100, "before": mx, "after": last}


def _rows(mc, sql, args):
    try: return [(float(r[0]), r[1]) for r in mc.execute(sql, args) if r[0] is not None]
    except Exception: return []


def sharp_drop(mc, ca, pool):
    """Largest sharp drop across the position pool reserve (r / REST) and total reserve (tr)."""
    cfg = settings()
    window = _f(cfg["sharp_drop_window_min"], 5) * 60
    need = _f(cfg["sharp_drop_pct"], 40)
    cut = time.time() - window
    pool_rows = _rows(mc, "select r, t from prices where ta=? and r is not null and pa=? and t>=? order by t", (ca, pool, cut))
    total_rows = _rows(mc, "select tr, t from prices where ta=? and tr is not null and t>=? order by t", (ca, cut))
    best = None
    for kind, rows in (("pool", pool_rows), ("total", total_rows)):
        drop = series_drop(rows)
        if not drop or drop["pct"] + 1e-9 < need: continue
        drop["kind"] = kind
        drop["window_min"] = _f(cfg["sharp_drop_window_min"], 5)
        if best is None or drop["pct"] > best["pct"]: best = drop
    return best


def alert_text(network, pool, drop, detail=None):
    """Plain sentence plus a UTM-tagged GeckoTerminal pool link on its own is added by alert_html."""
    if detail and detail.get("volume"):
        who = "the deployer wallet" if detail.get("deployer") else ("wallet " + _short(detail.get("address")))
        line = f"Liquidity removed: {usd_k(detail['volume'])} by {who} {ago(detail.get('at'))}. Exit may not fill."
    elif drop:
        kind = "total reserve" if drop.get("kind") == "total" else "pool reserve"
        line = (f"Liquidity removed: {kind} fell {drop['pct']:.0f}% in {drop.get('window_min', 5):.0f} min "
                f"({usd_k(drop['before'])} → {usd_k(drop['after'])}). Exit may not fill.")
    else:
        line = "Liquidity removed. Exit may not fill."
    return line


def _short(addr):
    a = addr or ""
    if len(a) <= 12: return a or "unknown"
    return a[:4] + "…" + a[-4:]


def alert_html(network, pool, drop, detail=None):
    import utm
    text = alert_text(network, pool, drop, detail)
    url = utm.pool_url(network, pool, "tg-liq-alert")
    return text + f'\n<a href="{utm.html_href(url)}">Pool</a>'


def _cooled(mc, ca, now=None):
    import common as C
    cur = C.kv_get(mc, _ALERT_KEY, {}) or {}
    if not isinstance(cur, dict): return False
    last = cur.get(ca)
    if last is None: return False
    try: last = float(last)
    except (TypeError, ValueError): return False
    now = time.time() if now is None else now
    return (now - last) < _f(settings()["alert_cooldown_s"], 1800)


def _mark_alert(mc, ca, now=None):
    import common as C
    cur = C.kv_get(mc, _ALERT_KEY, {}) or {}
    if not isinstance(cur, dict): cur = {}
    cur[ca] = time.time() if now is None else float(now)
    C.kv_set(mc, _ALERT_KEY, cur)
    try: mc.commit()
    except Exception: pass


def handle_drop(pos, drop, dex, developer, mc, notify, book="human"):
    """Alert from the reserve drop on every chain. Event detail only when the pool and plan allow it.
    On a CoinGecko API Demo (free) key or the CoinGecko API Basic plan, a Solana drop also queues the plan tip."""
    network, pool, ca = pos["network"], pos["pool"], pos["ca"]
    dex = dex_key(dex) or known_dex(mc, network, pool)
    detail = None
    if can_fetch(network, dex):
        rows = fetch_removes(network, pool, mc)
        hit = assess_removes(rows, developer, drop.get("before") if drop else None, network)
        if not hit.get("reason") and rows:
            top = max(rows, key=lambda a: _f(a.get("volume_in_usd")))
            hit = {"volume": _f(top.get("volume_in_usd")), "deployer": _same_addr(top.get("tx_from_address"), developer, network),
                   "address": top.get("tx_from_address"), "at": top.get("block_timestamp"), "reason": "remove"}
        if hit.get("volume"): detail = hit
    elif (network or "").lower() == "solana":
        try:
            import cgtier
            if not cgtier.cg_has("liquidity_events"):
                import plan_tips
                plan_tips.notify("liquidity_gap")
        except Exception:
            pass
    text = alert_text(network, pool, drop, detail)
    html = alert_html(network, pool, drop, detail)
    if notify: notify(html)
    return {"text": text, "html": html, "detail": detail, "book": book}


def open_positions():
    """Paper positions on both books. Read-only."""
    import os, sqlite3, common as C
    out = []
    for path in (os.environ.get("PAPER_DB", f"{C.BASE}/paper.db"), f"{C.BASE}/auto.db"):
        try:
            c = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
            c.row_factory = sqlite3.Row
            rows = c.execute("select network, pool, ca from positions").fetchall()
            c.close()
            for r in rows: out.append((r["network"], r["pool"], r["ca"]))
        except Exception:
            continue
    return out


def refresh_open_books(mc=None):
    """REST pool reserve for held positions when the stream has no fresh reserve sample."""
    import common as C
    own = mc is None
    mc = mc or C.mdb()
    n = 0
    try:
        for net, pool, ca in open_positions():
            before = fresh_reserve(mc, ca, pool, settings()["reserve_refresh_s"])
            if before: continue
            hit = ensure_reserve(mc, net, ca, pool, fetch=True)
            if hit: n += 1
        return n
    finally:
        if own:
            try: mc.close()
            except Exception: pass


def _pos_field(pos, key):
    try:
        if hasattr(pos, "keys") and key in pos.keys(): return pos[key]
    except Exception:
        pass
    if isinstance(pos, dict): return pos.get(key) or ""
    return ""


def watch_position(pos, plan, mc, book, notify, event, quote_fn=None, developer=""):
    """One held position. Returns 'sold' when the AI book wrote it off, 'alert' when a drop was sent, else ''."""
    import common as C
    network, pool, ca = pos["network"], pos["pool"], pos["ca"]
    try: ensure_reserve(mc, network, ca, pool)
    except Exception as e: C.logger("liquidity")("reserve", C.redact(e))
    drop = None
    try: drop = sharp_drop(mc, ca, pool)
    except Exception as e: C.logger("liquidity")("drop", C.redact(e))
    alerted = False
    if drop and not _cooled(mc, ca):
        dev = developer or _pos_field(pos, "dev")
        if not dev:
            try:
                info = (C.cg(f"/networks/{network}/tokens/{ca}/info", None, mc) or {}).get("data", {}).get("attributes", {})
                dev = info.get("developer_address") or ""
            except Exception:
                dev = ""
        info = handle_drop({"network": network, "pool": pool, "ca": ca}, drop, known_dex(mc, network, pool), dev, mc, notify, book)
        if event:
            event(ca, "liquidity", {"text": info["text"], "drop_pct": round(drop["pct"], 1), "kind": drop.get("kind")}, "alert")
        _mark_alert(mc, ca)
        alerted = True
    px = liq = None
    try:
        if quote_fn: q = quote_fn(pos) or {}
        else:
            import core
            q = core.cached_quote(ca, network) or core.quote(ca, network) or {}
        px = q.get("price")
        liq = cached_pool_reserve(ca, pool, max_age=settings()["reserve_refresh_s"] * 3)
        if liq is None: liq = q.get("liquidity")
    except Exception:
        q = {}
    mk = mark(pos["qty"], px, liq, network)
    plan_auto = True if plan is None else bool(plan["auto"] if hasattr(plan, "keys") else plan.get("auto", True))
    if should_auto_exit(book, plan_auto, mk["status"]):
        import core
        pc = core.db()
        try:
            out = core.sell(pc, ca, "all", source="risk-illiquid", liq_override=0 if liq is None else liq)
        finally:
            pc.close()
        if event: event(ca, "illiquid", {"text": "illiquid / rugged", "result": (out or "")[:180]}, "sold" if (out or "").startswith("🔴") else "failed")
        if notify: notify(f"🚨 <b>illiquid / rugged</b> — paper write-off\n{out}")
        return "sold"
    return "alert" if alerted else ""
