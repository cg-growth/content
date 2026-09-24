"""Pump Pulse live session: CoinGecko G2 trades -> rolling windows -> debounced Jev scoring -> browser WebSocket."""
import asyncio
from datetime import datetime
import logging
import time
from collections import deque

from fastapi import WebSocket, WebSocketDisconnect

from .. import config, recorder
from ..cg_ws import CGStream
from ..jev import answers_to_dict
from ..util import f
from .questions import CRITERIA_SIZES, QUESTIONS
from .state import build_state
from .window import PoolWindow

log = logging.getLogger("pulse")
MARKER_THRESHOLD = 70
MARKER_CONF = 0.5
MARKER_DEBOUNCE_S = 20
QUIET_RESCORE_S = 5


class Client:
    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.q: asyncio.Queue = asyncio.Queue(maxsize=5000)
        self.task = asyncio.create_task(self._pump())

    async def _pump(self):
        try:
            while True:
                msg = await self.q.get()
                await self.ws.send_json(msg)
        except Exception:
            pass

    def send(self, ev, data):
        try:
            self.q.put_nowait({"ev": ev, "data": data})
        except asyncio.QueueFull:
            pass


class Session:
    def __init__(self, hub, chain: str, pools: list[dict]):
        self.hub, self.chain = hub, chain
        self.pools = {p["id"]: p for p in pools}
        self.windows = {pid: PoolWindow(pid) for pid in self.pools}
        self.key_to_id = {f"{chain}:{pid}".lower(): pid for pid in self.pools}
        self.dirty = {pid: False for pid in self.pools}
        self.last_scored = {pid: 0.0 for pid in self.pools}
        self.ema: dict[str, dict] = {}
        self.last_marker: dict[tuple, float] = {}
        self.stream = CGStream(self.on_ws_event)
        self.tasks: list[asyncio.Task] = []
        self.rec = recorder.Recorder("pulse", chain)
        self.started = time.time()
        self.last_command = time.time()
        self.msg_times: deque = deque(maxlen=5000)
        self.jev_times: deque = deque(maxlen=2000)
        self.stopped = False

    @property
    def focus(self):
        return next(pid for pid, p in self.pools.items() if p["role"] == "focus")

    def broadcast(self, ev, data):
        self.rec.write(ev, data)
        self.hub.broadcast(ev, data)

    # ---------- setup ----------
    async def seed(self):
        cg = self.hub.cg

        async def one(pid):
            w = self.windows[pid]
            meta = self.pools[pid]
            try:
                d = await cg.pool(self.chain, pid)
                a = d["data"]["attributes"]
                tok = next((i["attributes"] for i in d.get("included", []) if i.get("type") == "token"), {})
                w.liquidity_usd, w.fdv_usd = f(a.get("reserve_in_usd")), f(a.get("fdv_usd"))
                meta.update(
                    name=a.get("name"),
                    symbol=tok.get("symbol"),
                    image_url=tok.get("image_url") if tok.get("image_url") not in (None, "missing.png") else None,
                    token_address=tok.get("address"),
                    pool_created_at=a.get("pool_created_at"),
                    liquidity_usd=w.liquidity_usd,
                    fdv_usd=w.fdv_usd,
                    price_usd=f(a.get("base_token_price_usd")),
                )
            except Exception as e:
                log.warning("pool meta failed %s", e)
            for fn, args in ((w.seed_seconds, ("second", 1, 1000)), (w.seed_minutes, ("minute", 1, 240))):
                try:
                    fn(await cg.pool_ohlcv(self.chain, pid, *args))
                except Exception as e:
                    log.warning("ohlcv seed failed %s", e)
            try:
                w.seed_trades(await cg.pool_trades(self.chain, pid))
            except Exception as e:
                log.warning("trades seed failed %s", e)

        await asyncio.gather(*(one(pid) for pid in self.pools))

    def snapshot(self):
        seeds = {}
        for pid, w in self.windows.items():
            secs = sorted(w.candles)[-900:]
            seeds[pid] = {
                "candles": [[s, *w.candles[s][:5]] for s in secs],
                "trades": [[t, s, round(u, 2), p] for t, s, u, p in list(w.trades)[-40:]],
            }
        return {"chain": self.chain, "pools": list(self.pools.values()), "seeds": seeds, "live": True}

    async def start(self):
        await self.seed()
        self.broadcast("session", self.snapshot())
        keys = [f"{self.chain}:{pid}" for pid in self.pools]
        await self.stream.set_pools(keys, [])
        self.stream.start()
        self.tasks = [asyncio.create_task(self.scorer(pid)) for pid in self.pools]
        self.tasks += [asyncio.create_task(self.trades_poller()), asyncio.create_task(self.liq_poller()), asyncio.create_task(self.status_loop())]
        if self.chain in config.WALLET_CHAINS and getattr(self.hub, "profiler", None):
            self.tasks.append(asyncio.create_task(self.wallet_loop()))

    async def stop(self, reason="stopped"):
        if self.stopped:
            return
        self.stopped = True
        for t in self.tasks:
            t.cancel()
        await self.stream.stop()
        self.broadcast("stopped", {"reason": reason})
        self.rec.close()

    # ---------- live data ----------
    def on_ws_event(self, ch, m):
        if ch != "G2":
            return
        pid = self.key_to_id.get(f"{m.get('n')}:{m.get('pa')}".lower())
        if not pid:
            return
        self.msg_times.append(time.time())
        res = self.windows[pid].add_trade(int(m["t"]), m.get("ty", "b"), float(m.get("vo") or 0), float(m.get("pu") or 0))
        if not res:
            return
        sec, c = res
        self.dirty[pid] = True
        self.broadcast("trade", {"p": pid, "t": int(m["t"]), "s": m.get("ty"), "u": round(float(m.get("vo") or 0), 2),
                                 "pr": float(m["pu"]), "c": [sec, *c[:5]]})

    async def trades_poller(self):
        while True:
            await asyncio.sleep(config.PULSE_TRADES_POLL_S)
            pid = self.focus
            try:
                self.windows[pid].seed_trades(await self.hub.cg.pool_trades(self.chain, pid))
            except Exception as e:
                log.warning("trades poll failed %s", e)

    async def liq_poller(self):
        while True:
            await asyncio.sleep(config.PULSE_LIQ_POLL_S)
            for pid in list(self.pools):
                try:
                    d = await self.hub.cg.pool(self.chain, pid)
                    self.windows[pid].liquidity_usd = f(d["data"]["attributes"].get("reserve_in_usd"))
                except Exception:
                    pass


    # ---------- wallet layer ----------
    async def wallet_loop(self):
        seen: set = set()
        trades: deque = deque(maxlen=600)
        profiles: dict = {}
        inflight: set = set()
        await asyncio.sleep(3)
        while True:
            pid = self.focus
            meta = self.pools[pid]
            token = meta.get("token_address")
            try:
                rest = await self.hub.cg.pool_trades(self.chain, pid)
            except Exception:
                rest = []
            for t in reversed(rest):
                tx = t.get("tx_hash")
                if not tx or tx in seen:
                    continue
                seen.add(tx)
                try:
                    ts = datetime.fromisoformat(t["block_timestamp"].replace("Z", "+00:00")).timestamp() * 1000
                except (KeyError, ValueError):
                    continue
                trades.append({"p": pid, "t": int(ts), "s": "b" if t.get("kind") == "buy" else "s", "u": float(t.get("volume_in_usd") or 0), "w": t.get("tx_from_address")})
            if token:
                now = time.time() * 1000
                size: dict = {}
                for tr in trades:
                    if tr["p"] == pid and now - tr["t"] <= 600_000 and tr["u"] >= config.PULSE_WALLET_MIN_USD and tr["w"]:
                        size[tr["w"]] = size.get(tr["w"], 0) + tr["u"]
                visible = [t["w"] for t in sorted((t for t in trades if t["p"] == pid and t["u"] >= config.PULSE_WALLET_MIN_USD and t["w"]), key=lambda t: -t["t"])[:25]]
                ranked = list(dict.fromkeys(visible + [w for w, _ in sorted(size.items(), key=lambda kv: -kv[1])]))
                todo = [w for w in ranked if (pid, w) not in profiles and (pid, w) not in inflight][: config.PULSE_WALLET_NEW_PER_CYCLE]
                ctx = {"symbol": meta.get("symbol"), "price_usd": meta.get("price_usd"), "pool_created_at": meta.get("pool_created_at")}

                async def prof(w):
                    inflight.add((pid, w))
                    try:
                        profiles[(pid, w)] = await self.hub.profiler.profile(self.chain, token, {"address": w, "_source": "live trader"}, ctx)
                    except Exception:
                        pass
                    finally:
                        inflight.discard((pid, w))

                await asyncio.gather(*(prof(w) for w in todo))
                self.emit_wallets(pid, trades, profiles)
            await asyncio.sleep(config.PULSE_WALLET_POLL_S)

    def emit_wallets(self, pid, trades, profiles):
        now = time.time() * 1000
        recent = [t for t in trades if t["p"] == pid and now - t["t"] <= 300_000]
        smart_net = insider_sell = bot_vol = prof_vol = tot = 0.0
        for t in recent:
            tot += t["u"]
            pr = profiles.get((pid, t["w"]))
            if not pr or not pr.get("scored"):
                continue
            prof_vol += t["u"]
            signed = t["u"] if t["s"] == "b" else -t["u"]
            if pr["persona"] in ("proven_trader", "accumulator") and (pr.get("skill") or 0) >= 60:
                smart_net += signed
            if (pr["persona"] == "insider_like" or (pr.get("insider") or 0) >= 0.7) and t["s"] == "s":
                insider_sell += t["u"]
            if pr["persona"] == "market_maker_bot":
                bot_vol += t["u"]
        flow = {
            "smart_net_usd": round(smart_net), "insider_sell_usd": round(insider_sell),
            "bot_share": round(bot_vol / tot, 3) if tot else 0, "profiled_share": round(prof_vol / tot, 3) if tot else 0,
            "wallets_profiled": sum(1 for k in profiles if k[0] == pid),
        }
        self.windows[pid].wallet_flow = flow
        rows = []
        for t in sorted((t for t in trades if t["p"] == pid and t["u"] >= config.PULSE_WALLET_MIN_USD), key=lambda t: -t["t"])[:25]:
            pr = profiles.get((pid, t["w"])) or {}
            rows.append({"t": t["t"], "s": t["s"], "u": round(t["u"], 2), "w": t["w"], "short": pr.get("short") or (t["w"][:6] + "…" + t["w"][-4:]),
                         "persona": pr.get("persona"), "persona_label": pr.get("persona_label"), "skill": pr.get("skill"),
                         "copy_worthy": pr.get("copy_worthy", False), "insider": pr.get("insider")})
        self.broadcast("wallets", {"p": pid, "flow": flow, "trades": rows, "at": int(now)})

    # ---------- scoring ----------
    async def scorer(self, pid):
        while True:
            role = self.pools[pid]["role"]
            interval = (config.PULSE_MIN_INTERVAL_MS if role == "focus" else config.PULSE_WATCH_INTERVAL_MS) / 1000
            since = time.time() - self.last_scored[pid]
            if since < interval or not (self.dirty[pid] or since > QUIET_RESCORE_S):
                await asyncio.sleep(0.1)
                continue
            self.dirty[pid] = False
            self.last_scored[pid] = time.time()
            now_ms = int(time.time() * 1000)
            meta = self.pools[pid]
            label = f"{meta.get('symbol') or ''} ({meta.get('name') or pid[:8]})"
            state = build_state(self.windows[pid], now_ms, label)
            try:
                r, ms, toks = await self.hub.jev.ask(state, QUESTIONS, retries=0)
            except Exception as e:
                self.broadcast("jev_error", {"p": pid, "error": type(e).__name__})
                await asyncio.sleep(1)
                continue
            self.jev_times.append((time.time(), toks))
            a = answers_to_dict(r, CRITERIA_SIZES)
            self.emit_score(pid, now_ms, a, ms, toks, state if role == "focus" else None)

    def emit_score(self, pid, now_ms, a, ms, toks, state):
        pump, dump = a["pump"]["value"], a["dump"]["value"]
        prev = self.ema.get(pid)
        al = config.PULSE_EMA_ALPHA
        ema = {"pump": pump, "dump": dump} if not prev else {
            "pump": round(al * pump + (1 - al) * prev["pump"], 1),
            "dump": round(al * dump + (1 - al) * prev["dump"], 1),
        }
        self.ema[pid] = ema
        self.broadcast("score", {
            "p": pid, "t": now_ms, "pump": ema["pump"], "dump": ema["dump"], "pump_raw": pump, "dump_raw": dump,
            "pump_conf": a["pump"]["confidence"], "dump_conf": a["dump"]["confidence"],
            "phase": a["phase"]["choice"], "phase_conf": a["phase"]["confidence"], "exhaustion": a["exhaustion"]["value"],
            "latency_ms": ms, "tokens": toks, "state": state,
        })
        for side, v in (("dump", dump), ("pump", pump)):
            conf = a[side]["confidence"]
            key = (pid, side)
            if v >= MARKER_THRESHOLD and conf >= MARKER_CONF and time.time() - self.last_marker.get(key, 0) >= MARKER_DEBOUNCE_S:
                self.last_marker[key] = time.time()
                self.broadcast("marker", {"p": pid, "t": now_ms, "side": side, "value": v, "confidence": conf})

    async def status_loop(self):
        while True:
            await asyncio.sleep(1)
            now = time.time()
            msgs10 = sum(1 for t in self.msg_times if now - t <= 10)
            jev60 = [(t, k) for t, k in self.jev_times if now - t <= 60]
            u = self.hub.jev.usage.snapshot()
            tok_per_s = sum(k for _, k in jev60) / 60 if jev60 else 0
            self.hub.broadcast("status", {
                "ws": self.stream.status,
                "ws_msgs": self.stream.messages,
                "ws_msgs_per_s": round(msgs10 / 10, 1),
                "cg_ws_credits": round(self.stream.messages * 0.1, 1),
                "jev_calls_per_s": round(len(jev60) / 60, 2),
                "jev_p50_ms": u["p50_ms"],
                "jev_cost_per_hr": round(tok_per_s * 3600 / 1e6 * config.JEV_PRICE_PER_MTOK, 3),
                "uptime_s": round(now - self.started),
            })
            if now - self.last_command > config.PULSE_IDLE_STOP_S:
                mins = round(config.PULSE_IDLE_STOP_S / 60)
                asyncio.create_task(self.hub.stop_session(f"idle {mins} min, paused to save credits"))
                return


class PulseHub:
    def __init__(self, cg, jev):
        self.cg, self.jev = cg, jev
        self.profiler = None
        self.clients: set[Client] = set()
        self.session: Session | None = None
        self._lock = asyncio.Lock()
        self._no_client_since: float | None = None
        self.caps = {"analyst": True, "websocket": True, "upgrade_url": "https://www.coingecko.com/en/api/pricing"}

    def broadcast(self, ev, data):
        for c in list(self.clients):
            c.send(ev, data)

    async def stop_session(self, reason="stopped"):
        if self.session:
            s, self.session = self.session, None
            await s.stop(reason)

    async def start_session(self, chain, focus, watch):
        async with self._lock:
            await self.stop_session("restarted")
            pools = [{"id": focus, "role": "focus"}] + [{"id": w, "role": "watch"} for w in watch if w != focus]
            pools = pools[: config.PULSE_MAX_POOLS]
            self.session = Session(self, chain, pools)
            self.broadcast("starting", {"chain": chain, "pools": [p["id"] for p in pools]})
            await self.session.start()

    async def handle(self, ws: WebSocket, replay: str | None = None, speed: float = 1.0):
        await ws.accept()
        client = Client(ws)
        if replay:
            try:
                async for ev, data in recorder.replay(replay, speed):
                    client.send(ev, data if ev != "session" else {**data, "live": False})
                client.send("replay_done", {})
                while True:
                    await ws.receive_text()
            except (WebSocketDisconnect, Exception):
                client.task.cancel()
            return
        if not self.caps["websocket"]:
            client.send("locked", {
                "message": "Pump Pulse needs the CoinGecko WebSocket, which requires a paid plan (Basic tier or above).",
                "upgrade_url": self.caps["upgrade_url"],
            })
            await ws.close(code=4403)
            return
        self.clients.add(client)
        if self.session:
            client.send("session", self.session.snapshot())
        try:
            while True:
                msg = await ws.receive_json()
                cmd = msg.get("cmd")
                if self.session:
                    self.session.last_command = time.time()
                if cmd == "start":
                    chain = msg.get("chain")
                    if chain not in config.CHAINS or not msg.get("focus"):
                        client.send("error", {"error": "bad start"})
                        continue
                    asyncio.create_task(self.start_session(chain, msg["focus"], msg.get("watch", [])))
                elif cmd == "focus" and self.session and msg.get("pool") in self.session.pools:
                    for pid, p in self.session.pools.items():
                        p["role"] = "focus" if pid == msg["pool"] else "watch"
                    self.session.broadcast("roles", {pid: p["role"] for pid, p in self.session.pools.items()})
                elif cmd == "stop":
                    await self.stop_session("stopped by user")
        except (WebSocketDisconnect, Exception):
            pass
        finally:
            self.clients.discard(client)
            client.task.cancel()
            if not self.clients:
                asyncio.create_task(self._stop_if_still_empty())

    async def _stop_if_still_empty(self):
        await asyncio.sleep(60)
        if not self.clients:
            await self.stop_session("no viewers")

    async def shutdown(self):
        await self.stop_session("server shutdown")
