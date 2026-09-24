import asyncio
import re
import time
from typing import Any

import httpx2 as httpx

from . import config

PRICING_URL = "https://www.coingecko.com/en/api/pricing"
_PLAN_HINTS = re.compile(r"exceed|plan|upgrad|enterprise|subscri|not available", re.I)


class CoinGeckoError(Exception):
    def __init__(self, status: int, body: str):
        super().__init__(f"CoinGecko HTTP {status}: {body[:200]}")
        self.status = status


class PlanRestrictedError(CoinGeckoError):
    """The API key's plan doesn't cover this endpoint (e.g. a Demo/free key hitting an Analyst+ one)."""


class TTLCache:
    def __init__(self):
        self._d: dict[str, tuple[float, Any]] = {}

    def get(self, key: str, ttl: float):
        hit = self._d.get(key)
        if hit and time.monotonic() - hit[0] < ttl:
            return hit[1]
        return None

    def put(self, key: str, value: Any):
        self._d[key] = (time.monotonic(), value)


class CGRest:
    def __init__(self, key: str | None = None):
        self._client = httpx.AsyncClient(
            base_url=config.CG_BASE,
            headers={config.CG_KEY_HEADER: key or config.CG_KEY, "accept": "application/json"},
            timeout=30,
        )
        self._sem = asyncio.Semaphore(config.CG_CONCURRENCY)
        self.cache = TTLCache()
        self.calls = 0

    async def close(self):
        await self._client.aclose()

    async def get(self, path: str, params: dict | None = None, ttl: float = 0):
        key = path + "?" + "&".join(f"{k}={v}" for k, v in sorted((params or {}).items()))
        if ttl:
            hit = self.cache.get(key, ttl)
            if hit is not None:
                return hit
        async with self._sem:
            for attempt in range(4):
                r = await self._client.get(path, params=params)
                self.calls += 1
                if r.status_code == 429 and attempt < 3:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                break
        if r.status_code != 200:
            if r.status_code in (400, 401, 403) and _PLAN_HINTS.search(r.text):
                raise PlanRestrictedError(r.status_code, r.text)
            raise CoinGeckoError(r.status_code, r.text)
        data = r.json()
        if ttl:
            self.cache.put(key, data)
        return data

    async def probe_capabilities(self) -> dict:
        """Cheap one-shot check of what this API key's plan covers, run once at startup.

        /key is itself Analyst+-gated, so a Demo/Basic key fails it the same way it would fail
        the wallet/top-traders/top-holders/news endpoints. WebSocket access needs a paid (Basic+)
        plan, so we fold it into the same "analyst" flag rather than probing it separately.
        """
        try:
            await self.get("/key")
            return {"analyst": True, "websocket": True, "reason": None, "upgrade_url": PRICING_URL}
        except PlanRestrictedError as e:
            return {"analyst": False, "websocket": False, "reason": str(e), "upgrade_url": PRICING_URL}
        except Exception:
            # Network hiccup, not a plan issue — don't block the whole app on it.
            return {"analyst": True, "websocket": True, "reason": None, "upgrade_url": PRICING_URL}

    # on-chain
    async def trending_pools(self, network: str, duration: str = "1h", n: int = 50):
        pools, included = [], {}
        page = 1
        while len(pools) < n and page <= 10:
            d = await self.get(
                f"/onchain/networks/{network}/trending_pools",
                {"include": "base_token", "duration": duration, "page": page},
                ttl=config.TRENDING_TTL_S,
            )
            batch = d.get("data", [])
            for inc in d.get("included", []):
                included[inc["id"]] = inc
            if not batch:
                break
            pools += batch
            page += 1
        return pools[:n], included

    async def pools_multi(self, network: str, addresses: list[str]):
        out, included = [], {}
        for i in range(0, len(addresses), 50):
            chunk = addresses[i : i + 50]
            d = await self.get(
                f"/onchain/networks/{network}/pools/multi/{','.join(chunk)}",
                {"include": "base_token"},
                ttl=config.TRENDING_TTL_S,
            )
            out += d.get("data", [])
            for inc in d.get("included", []):
                included[inc["id"]] = inc
        return out, included

    async def tokens_multi(self, network: str, addresses: list[str]) -> dict:
        out = {}
        for i in range(0, len(addresses), 50):
            chunk = addresses[i : i + 50]
            d = await self.get(f"/onchain/networks/{network}/tokens/multi/{','.join(chunk)}", ttl=config.TRENDING_TTL_S)
            for t in d.get("data", []):
                out[t["attributes"]["address"].lower()] = t["attributes"]
        return out

    async def token_info(self, network: str, address: str):
        d = await self.get(f"/onchain/networks/{network}/tokens/{address}/info", ttl=config.INFO_TTL_S)
        return d["data"]["attributes"]

    async def pool(self, network: str, address: str):
        d = await self.get(f"/onchain/networks/{network}/pools/{address}", {"include": "base_token"}, ttl=30)
        return d

    async def pool_ohlcv(self, network: str, address: str, timeframe: str, aggregate: int = 1, limit: int = 1000):
        d = await self.get(
            f"/onchain/networks/{network}/pools/{address}/ohlcv/{timeframe}",
            {"aggregate": aggregate, "limit": limit, "currency": "usd", "token": "base"},
        )
        return d["data"]["attributes"]["ohlcv_list"]

    async def pool_trades(self, network: str, address: str):
        d = await self.get(f"/onchain/networks/{network}/pools/{address}/trades", {"token": "base"})
        return [t["attributes"] for t in d.get("data", [])]

    # aggregated
    async def coins_markets(self, n: int = 250, category: str | None = None, ids: list[str] | None = None):
        params = {"vs_currency": "usd", "per_page": min(n, 250), "page": 1, "price_change_percentage": "24h,7d,30d", "sparkline": "true"}
        if category:
            params["category"] = category
        if ids:
            params["ids"] = ",".join(ids)
        return await self.get("/coins/markets", params, ttl=config.STABLE_TTL_S if category == "stablecoins" else 60)

    async def categories(self):
        return await self.get("/coins/categories", {"order": "market_cap_desc"}, ttl=600)

    async def categories_list(self):
        return await self.get("/coins/categories/list", ttl=config.STABLE_TTL_S)

    async def search(self, q: str):
        return await self.get("/search", {"query": q}, ttl=60)

    async def market_chart(self, coin_id: str, days: int = 90):
        return await self.get(
            f"/coins/{coin_id}/market_chart",
            {"vs_currency": "usd", "days": days, "interval": "daily"},
            ttl=config.MARKET_CHART_TTL_S,
        )

    async def insights(self, coin_id: str, per_page: int = 5):
        d = await self.get("/insights", {"coin_id": coin_id, "per_page": per_page}, ttl=config.NEWS_TTL_S)
        return d if isinstance(d, list) else d.get("data", [])

    async def news(self, coin_id: str, per_page: int = 20):
        return await self.get("/news", {"coin_id": coin_id, "per_page": per_page, "type": "news"}, ttl=config.NEWS_TTL_S)
