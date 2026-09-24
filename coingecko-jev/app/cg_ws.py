"""CoinGecko WebSocket manager: one socket, G2 trades + G3 candles, auto-reconnect."""
import asyncio
import json
import logging
import random

import websockets

from . import config

log = logging.getLogger("cg_ws")


def _msg(command: str, channel: str, data: dict | None = None) -> str:
    m = {"command": command, "identifier": json.dumps({"channel": channel})}
    if data is not None:
        m["data"] = json.dumps(data)
    return json.dumps(m)


class CGStream:
    """Call set_pools() any time; the socket (re)subscribes to match. Empty lists are never sent (server 4008s them)."""

    def __init__(self, on_event, key: str | None = None, ohlcv_interval: str = "1s"):
        self.on_event = on_event
        self.key = key or config.CG_PRO_KEY
        self.interval = ohlcv_interval
        self.trade_pools: list[str] = []
        self.ohlcv_pools: list[str] = []
        self.status = "idle"
        self.messages = 0
        self._ws = None
        self._task: asyncio.Task | None = None
        self._stop = False

    def start(self):
        if not self._task or self._task.done():
            self._stop = False
            self._task = asyncio.create_task(self._run())

    async def stop(self):
        self._stop = True
        if self._ws:
            await self._ws.close()
        if self._task:
            self._task.cancel()
        self.status = "idle"

    async def set_pools(self, trade_pools: list[str], ohlcv_pools: list[str]):
        self.trade_pools, self.ohlcv_pools = trade_pools, ohlcv_pools
        if self._ws and self.status == "live":
            await self._send_subscriptions(self._ws)

    async def _send_subscriptions(self, ws):
        if self.trade_pools:
            await ws.send(_msg("subscribe", "OnchainTrade"))
            await ws.send(_msg("message", "OnchainTrade", {"network_id:pool_addresses": self.trade_pools, "action": "set_pools"}))
        if self.ohlcv_pools:
            await ws.send(_msg("subscribe", "OnchainOHLCV"))
            await ws.send(
                _msg(
                    "message",
                    "OnchainOHLCV",
                    {"network_id:pool_addresses": self.ohlcv_pools, "interval": self.interval, "token": "base", "action": "set_pools"},
                )
            )

    async def _run(self):
        backoff = 1.0
        while not self._stop:
            try:
                self.status = "connecting"
                async with websockets.connect(
                    config.CG_WS_URL.format(key=self.key), ping_interval=None, max_size=2**22
                ) as ws:
                    self._ws = ws
                    self.status = "live"
                    backoff = 1.0
                    await self._send_subscriptions(ws)
                    async for raw in ws:
                        m = json.loads(raw)
                        if m.get("type") == "ping":
                            continue
                        if isinstance(m.get("code"), int) and m["code"] >= 4000:
                            log.warning("cg ws error %s %s", m.get("code"), m.get("message"))
                            continue
                        ch = m.get("ch") or m.get("c")
                        if ch in ("G2", "G3"):
                            self.messages += 1
                            self.on_event(ch, m)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.warning("cg ws disconnected: %s", type(e).__name__)
            self._ws = None
            if self._stop:
                break
            self.status = "reconnecting"
            await asyncio.sleep(backoff + random.random())
            backoff = min(backoff * 2, 30)
        self.status = "idle"
