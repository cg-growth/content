#!/usr/bin/env python3
"""Price stream. The basic tier and above: CoinGecko WebSocket (G3 OHLCV, G2 trades, G1 price).
The demo tier: WebSocket is not on that plan, so token prices are polled over REST at stream.poll_interval_s
(default 60s). The poll interval is not changed when credits run out. REST fallback if a paid WebSocket drops."""
import asyncio, json, os, sys, time
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
sys.path.insert(0, _ROOT + "/lib"); import common as C
import websockets
log = C.logger("stream"); URL = "wss://stream.coingecko.com/v1"
CH = {"G3": "OnchainOHLCV", "G2": "OnchainTrade", "G1": "OnchainSimpleTokenPrice"}
mc = C.mdb(); mc.execute("pragma synchronous=NORMAL"); state = {"subs": {}, "ws_up": False, "msgs": 0, "last_msg": 0}
def ident(ch): return json.dumps({"channel": ch})
def msg(ch, d): return json.dumps({"command": "message", "identifier": ident(ch), "data": json.dumps(d)})
def want():
    pos, watch = C.tracked()
    return {"1s": sorted({f"{n}:{p}" for n, p, _ in pos}), "1m": sorted({f"{n}:{p}" for n, p, _ in watch}),
            "trade": sorted({f"{n}:{p}" for n, p, _ in pos + watch}), "price": sorted({f"{n}:{a}" for n, _, a in pos + watch})}
async def sync(ws, cur):
    w = want()
    for key, (ch, field, act, extra) in {"1s": ("OnchainOHLCV", "network_id:pool_addresses", "pools", {"interval": "1s", "token": "base"}),
                                         "1m": ("OnchainOHLCV", "network_id:pool_addresses", "pools", {"interval": "1m", "token": "base"}),
                                         "trade": ("OnchainTrade", "network_id:pool_addresses", "pools", {}),
                                         "price": ("OnchainSimpleTokenPrice", "network_id:token_addresses", "tokens", {})}.items():
        old, new = set(cur.get(key, [])), set(w[key])
        if new - old: await ws.send(msg(ch, {field: sorted(new - old)[:100], **extra, "action": f"set_{act}"}))
        if old - new: await ws.send(msg(ch, {field: sorted(old - new), **extra, "action": f"unset_{act}"}))
        if new != old: log("sub", key, "+%d -%d" % (len(new - old), len(old - new)))
    return w
def store(d):
    ch = d.get("ch") or d.get("c")
    if ch == "G3":
        mc.execute("insert or replace into ohlcv values(?,?,?,?,?,?,?,?,?, 'ws')", (d["n"], d["pa"], d["i"], d["t"], d["o"], d["h"], d["l"], d["c"], d["v"]))
    elif ch == "G2":
        if d.get("is_anomalous") is True or d.get("ia") is True: return False
        mc.execute("insert or ignore into trades values(?,?,?,?,?,?,?,?,null,'ws')", (d["n"], d["pa"], d.get("tx"), d.get("ty"), d.get("vo"), d.get("pu"), d.get("to"), int((d.get("t") or 0) / 1000)))
    elif ch == "G1":
        mc.execute("insert into prices values(?,?,?,?,?,?,?,?,?)", (d["n"], d["ta"], d.get("p"), d.get("r"), d.get("tr"), d.get("m"), d.get("v"), d.get("pa"), d.get("t") or int(time.time())))
    else: return False
    return True
def prune():
    t = time.time()
    mc.execute("delete from ohlcv where iv='1s' and t<?", (t - 6 * 3600,)); mc.execute("delete from ohlcv where iv in ('15s','1m') and t<?", (t - 3 * 86400,))
    mc.execute("delete from trades where t<?", (t - 2 * 86400,)); mc.execute("delete from prices where t<?", (t - 2 * 86400,)); mc.commit()
def status(**k):
    state.update(k); C.kv_set(mc, "stream_status", {"ws_up": state["ws_up"], "msgs": state["msgs"], "last_msg": state["last_msg"], "subs": {k: len(v) for k, v in state["subs"].items()}, "mode": k.get("mode", state.get("mode"))}); mc.commit()
def poll_interval():
    try: return max(1, int((C.risk_cfg().get("stream") or {}).get("poll_interval_s", 60)))
    except Exception: return 60
def _pick(d, addr):
    if not isinstance(d, dict): return None
    if addr in d: return d[addr]
    low = {str(k).lower(): v for k, v in d.items()}
    return low.get(str(addr).lower())
def poll_prices():
    """One batched simple-price call per network. The demo tier allows 30 addresses; the analyst tier and above allow 100."""
    status(ws_up=False, mode="rest-poll")
    pos, watch = C.tracked(); by = {}
    for n, p, a in pos + watch:
        by.setdefault(n, {})[a] = p
    lim = 100 if C.tier() == "analyst" else 30
    n_ok = 0
    for n, amap in by.items():
        addrs = list(amap)
        for i in range(0, len(addrs), lim):
            chunk = addrs[i:i + lim]
            pr = C.cg(f"/simple/networks/{n}/token_price/{','.join(chunk)}", {"include_total_reserve_in_usd": "true"}, mc)
            pa = ((pr or {}).get("data") or {}).get("attributes") or {}
            prices, reserves = pa.get("token_prices") or {}, pa.get("total_reserve_in_usd") or {}
            now = int(time.time())
            for a in chunk:
                px = _pick(prices, a)
                if not px: continue
                rv = _pick(reserves, a)
                try: rv = float(rv) if rv not in (None, "") else None
                except Exception: rv = None
                mc.execute("insert into prices values(?,?,?,?,?,?,?,?,?)", (n, a, float(px), None, rv, None, None, amap.get(a), now))
                n_ok += 1
    mc.commit(); return n_ok
def poll_loop():
    import cgtier
    log("The WebSocket price stream needs", cgtier.needs_plan("basic") + ". Polling token prices over REST every", poll_interval(), "s.")
    while True:
        t = time.time()
        try:
            import usage
            usage.refresh()
        except Exception as e: log("usage", C.redact(e))
        try: n = poll_prices(); log("heartbeat", "rest-poll", "prices", n, "tier", C.tier())
        except Exception as e: log("poll err", C.redact(e))
        remain = max(1, poll_interval() - (time.time() - t))
        while remain > 0:
            step = min(60, remain); time.sleep(step); remain -= step
            if remain > 0: log("heartbeat", "rest-poll", "tier", C.tier())
class WsRefused(Exception):
    """The socket accepted the connection, then refused the key."""
def _ws_refused(message):
    """True for the first-message body {"message":"Unauthorized access, invalid API key"}."""
    d = message
    if isinstance(d, str):
        try: d = json.loads(d)
        except Exception: return False
    if not isinstance(d, dict): return False
    return str(d.get("message") or "").strip() == "Unauthorized access, invalid API key"
def ws_first_action(message):
    """'poll' when that first message refuses the key, otherwise stay on the socket."""
    return "poll" if _ws_refused(message) else "ws"
def _refuse_ws():
    log("WebSocket refused the API key. Polling token prices over REST.")
    try:
        import plan_tips
        plan_tips.notify("invalid_key", signature="ws-unauthorized")
    except Exception as e:
        log("plan tip", C.redact(e))
    raise WsRefused()
async def run_ws():
    async with websockets.connect(URL, additional_headers=C.auth_headers(), ping_interval=None, open_timeout=20) as ws:
        try: raw = await asyncio.wait_for(ws.recv(), timeout=5)
        except asyncio.TimeoutError: raw = None
        saw_first = raw is not None
        if raw is not None and ws_first_action(raw) == "poll": _refuse_ws()
        for ch in CH.values(): await ws.send(json.dumps({"command": "subscribe", "identifier": ident(ch)}))
        await asyncio.sleep(1); cur = await sync(ws, {}); state["subs"] = cur; status(ws_up=True, mode="ws"); log("ws connected")
        last_sync = last_beat = last_prune = time.time(); n_since = 0
        while True:
            if raw is None:
                try: raw = await asyncio.wait_for(ws.recv(), timeout=5)
                except asyncio.TimeoutError: raw = None
            if raw and not saw_first:
                saw_first = True
                if ws_first_action(raw) == "poll": _refuse_ws()
            if raw:
                d = json.loads(raw)
                if d.get("type") == "ping": pass
                elif store(d): mc.commit(); n_since += 1; state["msgs"] += 1; state["last_msg"] = int(time.time())
                elif d.get("code") not in (2000, 3000, None) or d.get("type") == "reject_subscription": log("server", str(d)[:200])
            raw = None
            t = time.time()
            if t - last_sync > 5:
                mc.commit(); cur = await sync(ws, cur); state["subs"] = cur; last_sync = t
                if n_since: C.credit(mc, "ws", 0.1 * n_since); n_since = 0
                status(ws_up=True, mode="ws")
            if t - last_beat > 60:
                log("heartbeat", "msgs", state["msgs"], "subs", {k: len(v) for k, v in cur.items()}); last_beat = t
                try:
                    import usage
                    usage.refresh()
                except Exception as e: log("usage", C.redact(e))
            if t - last_prune > 600: prune(); last_prune = t
def rest_fallback(seconds=60):
    """Poll REST 1s/15s OHLCV (via minute/second timeframe) + pool trades for positions while WS is down."""
    status(ws_up=False, mode="rest-fallback"); end = time.time() + seconds; log("heartbeat rest-fallback")
    while time.time() < end:
        pos, watch = C.tracked()
        for n, p, a in pos + watch:
            try:
                o = C.cg(f"/networks/{n}/pools/{p}/ohlcv/second", {"aggregate": 15 if (n, p, a) in watch else 1, "limit": 120}, mc)
                iv = "15s" if (n, p, a) in watch else "1s"
                for t, op, h, l, cl, v in ((o or {}).get("data", {}).get("attributes", {}).get("ohlcv_list") or []):
                    mc.execute("insert or replace into ohlcv values(?,?,?,?,?,?,?,?,?,'rest')", (n, p, iv, t, op, h, l, cl, v))
                tr = C.cg(f"/networks/{n}/pools/{p}/trades", None, mc)
                import trades as TR
                for x in (tr or {}).get("data", []):
                    at = x["attributes"]
                    if TR.is_anomalous(at): continue
                    ty = "b" if at["kind"] == "buy" else "s"
                    pu = float(at["price_to_in_usd"] if ty == "b" else at["price_from_in_usd"])
                    import datetime as D
                    ts = int(D.datetime.fromisoformat(at["block_timestamp"].replace("Z", "+00:00")).timestamp())
                    mc.execute("insert or ignore into trades values(?,?,?,?,?,?,?,?,?,'rest')", (n, p, at["tx_hash"], ty, float(at["volume_in_usd"]), pu, None, ts, at["tx_from_address"]))
                pr = C.cg(f"/simple/networks/{n}/token_price/{a}", {"include_total_reserve_in_usd": "true"}, mc)
                pa = ((pr or {}).get("data") or {}).get("attributes") or {}
                px = (pa.get("token_prices") or {}).get(a)
                if px: mc.execute("insert into prices values(?,?,?,?,?,?,?,?,?)", (n, a, float(px), None, float((pa.get("total_reserve_in_usd") or {}).get(a) or 0) or None, None, None, p, int(time.time())))
            except Exception as e: log("fallback err", e)
        mc.commit(); time.sleep(5)
def main():
    C.start_heartbeat(log)
    if not C.cg_has("ws"):
        poll_loop(); return
    back = 2
    while True:
        try: asyncio.run(run_ws()); back = 2
        except WsRefused:
            poll_loop(); return
        except Exception as e:
            log("ws down:", type(e).__name__, str(e)[:120]); status(ws_up=False)
            rest_fallback(min(60, back * 5)); back = min(back * 2, 30)
if __name__ == "__main__": main()
