import json
import logging
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, WebSocket
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import config, recorder
from .cg_rest import PRICING_URL, CGRest
from .jev import Jev
from .labels.feed import load_feed
from .labels.run import run_labels

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


class RedactKeys(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        if "x_cg_pro_api_key" in msg or "Authorization" in msg:
            record.msg, record.args = "[redacted log line]", ()
        return True


for name in ("uvicorn.access", "httpx2", "websockets"):
    logging.getLogger(name).addFilter(RedactKeys())

state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not config.CG_KEY:
        raise RuntimeError(
            "COINGECKO_PRO_API_KEY is not set. This app always requires a CoinGecko API key "
            "(a free Demo-tier key is enough to run some demos) — it never runs keyless. "
            "Get one at https://www.coingecko.com/en/api, then see README.md."
        )
    state["cg"] = CGRest()
    state["jev"] = Jev()
    state["caps"] = await state["cg"].probe_capabilities()
    from .pulse.hub import PulseHub
    from .fng.run import FngService

    state["pulse"] = PulseHub(state["cg"], state["jev"])
    state["pulse"].caps = state["caps"]
    state["fng"] = FngService(state["cg"], state["jev"], concurrency=12)
    from .xray.profiler import WalletProfiler
    from .xray.service import XrayService

    state["profiler"] = WalletProfiler(state["cg"], state["jev"])
    state["xray"] = XrayService(state["cg"], state["jev"], state["profiler"])
    state["pulse"].profiler = state["profiler"]
    from .wallet.service import WalletService

    state["wallet"] = WalletService(state["cg"], state["jev"], state["profiler"])
    state["radar_batches"] = {}
    yield
    await state["pulse"].shutdown()
    await state["jev"].close()
    await state["cg"].close()


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def no_cache_static(request, call_next):
    resp = await call_next(request)
    if not request.url.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-cache, must-revalidate"
    return resp


def sse(gen, rec: recorder.Recorder | None = None, public_error: str | None = None):
    async def stream():
        try:
            async for ev, data in gen:
                if rec:
                    rec.write(ev, data)
                yield f"event: {ev}\ndata: {json.dumps(data)}\n\n"
        except Exception as e:
            msg = public_error or f"{type(e).__name__}: {str(e)[:200]}"
            yield f"event: fail\ndata: {json.dumps({'error': msg})}\n\n"
        finally:
            if rec:
                rec.close()

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


def _chain(chain: str) -> str:
    if chain not in config.CHAINS:
        raise HTTPException(400, "unknown chain")
    return chain


@app.get("/api/config")
async def api_config():
    return {
        "chains": {k: v["label"] for k, v in config.CHAINS.items()},
        "wallet_chains": config.WALLET_CHAINS,
        "wallet_caps": {k: config.wallet_caps(k) for k in config.WALLET_CHAINS},
    }


@app.get("/api/capabilities")
async def api_capabilities():
    return state.get("caps") or {"analyst": True, "websocket": True, "reason": None, "upgrade_url": PRICING_URL}


def _locked(feature: str):
    return {
        "locked": True,
        "feature": feature,
        "message": f"{feature} needs a CoinGecko API Analyst plan or higher.",
        "upgrade_url": PRICING_URL,
    }


def _wallet_addr_ok(chain: str, address: str) -> bool:
    pattern = config.WALLET_ADDR_PATTERNS.get(chain, config.DEFAULT_WALLET_ADDR_PATTERN)
    return bool(re.match(pattern, address))


@app.get("/api/chains")
async def api_chains():
    if state.get("chain_meta"):
        return state["chain_meta"]
    want = {**{k: v["label"] for k, v in config.CHAINS.items()}, **config.WALLET_CHAINS}
    img = {}
    try:
        nets = []
        for page in (1, 2, 3):
            nets += (await state["cg"].get("/onchain/networks", {"page": page}, ttl=86400)).get("data", [])
        plat = {n["id"]: n["attributes"].get("coingecko_asset_platform_id") for n in nets if n["id"] in want}
        ap = {a["id"]: (a.get("image") or {}) for a in await state["cg"].get("/asset_platforms", ttl=86400)}
        img = {k: (ap.get(v) or {}).get("small") for k, v in plat.items()}
    except Exception:
        pass
    meta = {k: {"label": v, "image": img.get(k), "wallet": k in config.WALLET_CHAINS} for k, v in want.items()}
    if img:
        state["chain_meta"] = meta
    return meta


@app.get("/api/stats")
async def api_stats():
    return {"cg_calls": state["cg"].calls, "jev": state["jev"].usage.snapshot()}


@app.get("/api/fixtures")
async def api_fixtures(demo: str = Query(..., pattern="^(labels|pulse|fng|xray|wallet|radar)$")):
    return recorder.list_fixtures(demo)


# ---------- Demo 1: Jev Labels ----------
@app.get("/api/labels/feed")
async def labels_feed(chain: str = "solana", window: str = Query("1h", pattern="^(5m|1h|6h|24h)$"), n: int = Query(50, ge=5, le=100)):
    return await load_feed(state["cg"], _chain(chain), window, n)


@app.get("/api/labels/run")
async def labels_run(chain: str = "solana", ids: str = ""):
    pool_ids = [i for i in ids.split(",") if i][:100]
    if not pool_ids:
        raise HTTPException(400, "ids required")
    rec = recorder.Recorder("labels", _chain(chain))
    return sse(run_labels(state["cg"], state["jev"], chain, pool_ids), rec)


@app.get("/api/labels/replay")
async def labels_replay(name: str, speed: float = 1.0):
    try:
        recorder.fixture_path(name)
    except (ValueError, FileNotFoundError):
        raise HTTPException(404, "fixture not found")
    return sse(recorder.replay(name, speed))


@app.get("/api/labels/snapshot")
async def labels_snapshot(name: str):
    try:
        recs = recorder.read_all(name)
    except (ValueError, FileNotFoundError):
        raise HTTPException(404, "fixture not found")
    rows = [r["data"] for r in recs if r["ev"] == "row" and "row" in r["data"]]
    rows.sort(key=lambda d: d.get("index", 0))
    return [d["row"] for d in rows]


# ---------- Demo 2: Pump Pulse ----------
@app.get("/api/pulse/pools")
async def pulse_pools(chain: str = "solana"):
    from .labels.feed import build_row

    pools, included = await state["cg"].trending_pools(_chain(chain), "5m", 40)
    rows = [build_row(p, included) for p in pools]
    rows.sort(key=lambda r: -((r["txns"].get("m5") or {}).get("buys", 0) + (r["txns"].get("m5") or {}).get("sells", 0)))
    return rows[:20]


@app.get("/api/pulse/search")
async def pulse_search(chain: str = "solana", q: str = Query(..., min_length=2, max_length=120)):
    from .labels.feed import build_row

    d = await state["cg"].get(
        "/onchain/search/pools", {"query": q.strip(), "network": _chain(chain), "include": "base_token,dex"}, ttl=30
    )
    included = {i["id"]: i for i in d.get("included", [])}
    rows = []
    for p in d.get("data", []):
        row = build_row(p, included)
        dex = included.get((p["relationships"].get("dex") or {}).get("data", {}).get("id", ""), {})
        row["dex"] = (dex.get("attributes") or {}).get("name")
        rows.append(row)
    return rows[:20]


PULSE_INTERVALS = {"1s": ("second", 1), "15s": ("second", 15), "1m": ("minute", 1), "5m": ("minute", 5), "15m": ("minute", 15), "1h": ("hour", 1)}


@app.get("/api/pulse/ohlcv")
async def pulse_ohlcv(chain: str, pool: str = Query(..., min_length=10, max_length=100), interval: str = "1m"):
    if interval not in PULSE_INTERVALS:
        raise HTTPException(400, "bad interval")
    tf, agg = PULSE_INTERVALS[interval]
    rows = await state["cg"].pool_ohlcv(_chain(chain), pool, tf, agg, 1000)
    return sorted(rows)


@app.websocket("/api/pulse/ws")
async def pulse_ws(ws: WebSocket, replay: str | None = None, speed: float = 1.0):
    if replay:
        try:
            recorder.fixture_path(replay)
        except (ValueError, FileNotFoundError):
            await ws.close(code=4404)
            return
    await state["pulse"].handle(ws, replay, speed)


# ---------- Demo 3: Coin Fear & Greed ----------
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,99}$")


def _fng_scope(n: int, category: str | None, ids: str | None):
    id_list = [i for i in (ids or "").split(",") if i][:50]
    if category and not SAFE_ID.match(category):
        raise HTTPException(400, "bad category")
    if any(not SAFE_ID.match(i) for i in id_list):
        raise HTTPException(400, "bad coin id")
    if id_list:
        return None, id_list, "custom", {"kind": "custom", "ids": id_list}
    if category:
        return category, None, "cat-" + re.sub(r"[^a-z0-9-]", "-", category)[:40], {"kind": "category", "id": category}
    return None, None, f"top{n}", {"kind": "top", "n": n}


@app.get("/api/fng/categories")
async def fng_categories():
    cats = await state["cg"].categories()
    seen = {c["id"] for c in cats}
    out = [
        {"id": c["id"], "name": c["name"], "market_cap": c.get("market_cap"), "change_24h": c.get("market_cap_change_24h"),
         "volume_24h": c.get("volume_24h"), "top_3_coins": c.get("top_3_coins") or []}
        for c in cats
    ]
    try:
        for c in await state["cg"].categories_list():
            if c["category_id"] not in seen:
                out.append({"id": c["category_id"], "name": c["name"], "market_cap": None, "change_24h": None, "volume_24h": None, "top_3_coins": []})
    except Exception:
        pass
    return out


@app.get("/api/fng/search")
async def fng_search(q: str = Query(..., min_length=2, max_length=80)):
    d = await state["cg"].search(q.strip())
    return {
        "coins": [{"id": c["id"], "name": c["name"], "symbol": c.get("symbol"), "rank": c.get("market_cap_rank"), "image": c.get("large") or c.get("thumb")}
                  for c in d.get("coins", [])[:12]],
        "categories": [{"id": c["id"], "name": c["name"]} for c in d.get("categories", [])[:8]],
    }


@app.get("/api/fng/universe")
async def fng_universe(n: int = Query(100, ge=5, le=250), stables: bool = False, category: str | None = None, ids: str | None = None):
    from .fng.run import coin_public
    from .fng.universe import load_universe

    cat, id_list, _, _ = _fng_scope(n, category, ids)
    return [coin_public(c) for c in await load_universe(state["cg"], n, stables, cat, id_list)]


@app.get("/api/fng/run")
async def fng_run(n: int = Query(100, ge=5, le=250), stables: bool = False, category: str | None = None, ids: str | None = None, label: str = ""):
    cat, id_list, tag, scope = _fng_scope(n, category, ids)
    scope["label"] = label[:80]
    rec = recorder.Recorder("fng", tag)
    return sse(state["fng"].run(n, stables, cat, id_list, scope), rec)


@app.get("/api/fng/replay")
async def fng_replay(name: str, speed: float = 1.0):
    try:
        recorder.fixture_path(name)
    except (ValueError, FileNotFoundError):
        raise HTTPException(404, "fixture not found")
    return sse(recorder.replay(name, speed))


@app.get("/api/fng/snapshot")
async def fng_snapshot(name: str):
    try:
        recs = recorder.read_all(name)
    except (ValueError, FileNotFoundError):
        raise HTTPException(404, "fixture not found")
    start = next((r["data"] for r in recs if r["ev"] == "start"), None)
    return {"coins": start["coins"], "scope": start.get("scope") or {"kind": "top"}} if start else {"coins": [], "scope": {"kind": "top"}}


# ---------- Wallet X-ray ----------
XRAY_ERR = "Couldn't load wallet data for this token."
ADDR = re.compile(r"^[A-Za-z0-9]{20,90}$")


@app.get("/api/xray/run")
async def xray_run(chain: str, token: str, pool: str | None = None):
    if chain not in config.WALLET_CHAINS or not ADDR.match(token) or (pool and not ADDR.match(pool)):
        raise HTTPException(404, XRAY_ERR)
    if not state["caps"]["analyst"]:
        async def locked_gen():
            yield "fail", {"error": "X-ray needs a CoinGecko API Analyst plan or higher (top holders & top traders). Upgrade: " + PRICING_URL}
        return sse(locked_gen())
    rec = recorder.Recorder("xray", chain)
    return sse(state["xray"].run(chain, token, pool), rec, public_error=XRAY_ERR)


@app.get("/api/xray/replay")
async def xray_replay(name: str, speed: float = 1.0):
    try:
        recorder.fixture_path(name)
    except (ValueError, FileNotFoundError):
        raise HTTPException(404, "fixture not found")
    return sse(recorder.replay(name, speed))


@app.get("/api/xray/snapshot")
async def xray_snapshot(name: str):
    try:
        recs = recorder.read_all(name)
    except (ValueError, FileNotFoundError):
        raise HTTPException(404, "fixture not found")
    start = next((r["data"] for r in recs if r["ev"] == "start"), None)
    if not start:
        raise HTTPException(404, "fixture not found")
    return start


@app.get("/api/xray/token")
async def xray_token(chain: str, token: str, pool: str | None = None):
    if chain not in config.WALLET_CHAINS or not ADDR.match(token):
        raise HTTPException(404, XRAY_ERR)
    try:
        return await state["xray"].token_context(chain, token, pool)
    except Exception:
        raise HTTPException(404, XRAY_ERR)


@app.get("/api/xray/trending")
async def xray_trending(chain: str):
    if chain not in config.WALLET_CHAINS:
        raise HTTPException(404, XRAY_ERR)
    from .labels.feed import build_row

    try:
        pools, included = await state["cg"].trending_pools(chain, "1h", 20)
    except Exception:
        return []
    seen, rows = set(), []
    for p in pools:
        r = build_row(p, included)
        if r["token"]["address"] in seen:
            continue
        seen.add(r["token"]["address"])
        rows.append(r)
    return rows[:10]


@app.get("/api/xray/search")
async def xray_search(chain: str, q: str = Query(..., min_length=2, max_length=120)):
    if chain not in config.WALLET_CHAINS:
        raise HTTPException(404, XRAY_ERR)
    from .labels.feed import build_row

    d = await state["cg"].get("/onchain/search/pools", {"query": q.strip(), "network": chain, "include": "base_token,dex"}, ttl=30)
    included = {i["id"]: i for i in d.get("included", [])}
    rows = []
    for p in d.get("data", []):
        row = build_row(p, included)
        dex = included.get((p["relationships"].get("dex") or {}).get("data", {}).get("id", ""), {})
        row["dex"] = (dex.get("attributes") or {}).get("name")
        rows.append(row)
    return rows[:20]


# ---------- Wallet Profile & Radar ----------
WALLET_ERR = "Couldn't load data for this wallet."


@app.get("/api/wallet/profile")
async def wallet_profile(address: str, chain: str = "auto"):
    if chain != "auto" and chain not in config.WALLET_CHAINS:
        raise HTTPException(404, WALLET_ERR)
    if chain != "auto" and not _wallet_addr_ok(chain, address):
        raise HTTPException(404, WALLET_ERR)
    if chain == "auto" and not (_wallet_addr_ok("solana", address) or _wallet_addr_ok("eth", address)):
        raise HTTPException(404, WALLET_ERR)
    if not state["caps"]["analyst"]:
        return _locked("Wallet Profile")
    try:
        data = await state["wallet"].profile_page(address, None if chain == "auto" else chain)
    except Exception:
        raise HTTPException(404, WALLET_ERR)
    caps = config.wallet_caps(data["chain"])
    data["caps"] = caps
    if not caps.get("balances"):
        data["holdings"] = None
    if not caps.get("transfers"):
        data["transfers"] = None
    rec = recorder.Recorder("wallet", data["chain"])
    rec.write("profile", data)
    rec.close()
    return data


@app.get("/api/wallet/snapshot")
async def wallet_snapshot(name: str):
    try:
        recs = recorder.read_all(name)
    except (ValueError, FileNotFoundError):
        raise HTTPException(404, "fixture not found")
    return next(r["data"] for r in recs if r["ev"] == "profile")


@app.get("/api/radar/candidates")
async def radar_candidates(chain: str, source: str = Query("trending_1h", pattern="^(trending_1h|trending_24h|new)$"), tokens: int = Query(10, ge=3, le=20)):
    if chain not in config.WALLET_CHAINS:
        raise HTTPException(404, WALLET_ERR)
    if not state["caps"]["analyst"]:
        return _locked("Smart Money Radar")
    try:
        res = await state["wallet"].candidates(chain, source, tokens)
    except Exception:
        raise HTTPException(404, WALLET_ERR)
    import secrets

    bid = secrets.token_hex(6)
    state["radar_batches"][bid] = res
    if len(state["radar_batches"]) > 50:
        state["radar_batches"].pop(next(iter(state["radar_batches"])))
    return {**res, "batch": bid}


@app.get("/api/radar/run")
async def radar_run(batch: str, ids: str):
    res = state["radar_batches"].get(batch)
    if not res:
        raise HTTPException(404, "batch expired, find candidates again")
    if not state["caps"]["analyst"]:
        async def locked_gen():
            yield "fail", {"error": "Smart Money Radar needs a CoinGecko API Analyst plan or higher. Upgrade: " + PRICING_URL}
        return sse(locked_gen())
    chain = res["chain"]
    want = {i.lower() for i in ids.split(",") if _wallet_addr_ok(chain, i)}
    cands = [c for c in res["candidates"] if c["address"].lower() in want][:80]
    rec = recorder.Recorder("radar", res["chain"])
    return sse(state["wallet"].run_radar(res["chain"], cands), rec, public_error=WALLET_ERR)


@app.get("/api/radar/replay")
async def radar_replay(name: str, speed: float = 1.0):
    try:
        recorder.fixture_path(name)
    except (ValueError, FileNotFoundError):
        raise HTTPException(404, "fixture not found")
    return sse(recorder.replay(name, speed))


@app.get("/api/radar/snapshot")
async def radar_snapshot(name: str):
    try:
        recs = recorder.read_all(name)
    except (ValueError, FileNotFoundError):
        raise HTTPException(404, "fixture not found")
    return next(r["data"] for r in recs if r["ev"] == "start")


# ---------- pages ----------
@app.get("/")
async def index():
    return FileResponse(config.WEB_DIR / "index.html")


app.mount("/", StaticFiles(directory=config.WEB_DIR, html=True), name="web")
