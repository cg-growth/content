"""Wallet-first surfaces: single Wallet Profile and the Smart Money Radar (candidates -> batch profiling)."""
import asyncio
import time

from .. import config
from ..cg_rest import CGRest
from ..jev import Jev, Usage
from ..util import f, short
from ..xray.features import likely_bot_row
from ..xray.profiler import ALL_NETS, WalletProfiler


class WalletService:
    def __init__(self, cg: CGRest, jev: Jev, profiler: WalletProfiler):
        self.cg, self.jev, self.profiler = cg, jev, profiler

    async def token_images(self, pairs: set[tuple[str, str]], coin_ids: set[str]) -> dict:
        """(network, address) -> image url via onchain tokens/multi; coin ids -> image via coins/markets."""
        cache = self.__dict__.setdefault("_img", {})
        out, by_net = {}, {}
        for net, addr in pairs:
            k = f"{net}:{addr.lower()}"
            if k in cache:
                out[k] = cache[k]
            elif net in config.WALLET_CHAINS and addr and not addr.lower().startswith("0xeeeeeeee"):
                by_net.setdefault(net, []).append(addr)

        async def fetch(net, addrs):
            for i in range(0, len(addrs), 30):
                try:
                    d = await self.cg.get(f"/onchain/networks/{net}/tokens/multi/{','.join(addrs[i:i + 30])}", ttl=3600)
                    for tkn in d.get("data", []):
                        a = tkn["attributes"]
                        url = a.get("image_url") if a.get("image_url") not in (None, "missing.png") else None
                        cache[f"{net}:{a['address'].lower()}"] = url
                except Exception:
                    pass

        await asyncio.gather(*(fetch(n, list(dict.fromkeys(a))[:90]) for n, a in by_net.items()))
        for net, addr in pairs:
            k = f"{net}:{addr.lower()}"
            out[k] = cache.get(k)
        if coin_ids:
            try:
                for c in await self.cg.coins_markets(len(coin_ids), ids=sorted(coin_ids)[:100]):
                    out[f"coin:{c['id']}"] = c.get("image")
            except Exception:
                pass
        return out

    async def primary_chain(self, addr: str) -> str:
        try:
            d = await self.cg.get(f"/onchain/wallets/{addr}/pnl", {"networks": ALL_NETS, "per_page": 1}, ttl=300)
            nets = d["data"]["attributes"].get("networks") or []
            nets = [n for n in nets if n.get("network") in config.WALLET_CHAINS and (n.get("tokens") or 0) > 0]
            if nets:
                return max(nets, key=lambda n: n.get("tokens") or 0)["network"]
        except Exception:
            pass
        return "base"

    async def profile_page(self, addr: str, chain: str | None):
        t0 = time.perf_counter()
        chain = chain if chain in config.WALLET_CHAINS else await self.primary_chain(addr)
        prof = await self.profiler.profile_wallet(chain, addr)
        g = await self.profiler.global_profile(chain, addr)
        raw = g["_raw"]
        transfers = []
        try:
            d = await self.cg.get(f"/onchain/networks/{chain}/wallets/{addr}/transfers", {"per_page": 50})
            transfers = [t.get("attributes", t) for t in d.get("data", [])]
        except Exception:
            pass
        sym = {(s.get("address") or "").lower(): s.get("symbol") for s in raw["token_stats"]}
        sym.update({(b.get("address") or "").lower(): b.get("symbol") for b in raw["balances"]})
        trades = []
        for t in raw["trades"][:100]:
            trades.append({
                "t": t.get("block_timestamp"), "kind": t.get("kind"), "usd": f(t.get("volume_in_usd")), "dex": t.get("pool_dex"),
                "pool": t.get("pool_address"), "tx": t.get("tx_hash"),
                "from_symbol": sym.get((t.get("from_token_address") or "").lower()) or short(t.get("from_token_address")),
                "to_symbol": sym.get((t.get("to_token_address") or "").lower()) or short(t.get("to_token_address")),
                "from_token": t.get("from_token_address"), "to_token": t.get("to_token_address"),
            })
        perf = sorted(
            ({"network": s.get("network"), "address": s.get("address"), "symbol": s.get("symbol"), "name": s.get("name"),
              "realized": f(s.get("realized_pnl_usd")), "unrealized": f(s.get("unrealized_pnl_usd")), "balance": f(s.get("token_balance")),
              "buys": s.get("total_buy_count"), "sells": s.get("total_sell_count"), "bought_usd": f(s.get("total_buy_usd")), "sold_usd": f(s.get("total_sell_usd")),
              "avg_buy": f(s.get("average_buy_price_usd")), "avg_sell": f(s.get("average_sell_price_usd"))} for s in raw["token_stats"]),
            key=lambda x: -abs((x["realized"] or 0) + (x["unrealized"] or 0)),
        )
        holdings = [{"network": b.get("network"), "address": b.get("address"), "symbol": b.get("symbol"), "name": b.get("name"),
                     "balance": f(b.get("balance")), "price": f(b.get("price_usd")), "value": f(b.get("value_usd")),
                     "change_24h": f(b.get("h24_price_change_percentage")), "coingecko_coin_id": b.get("coingecko_coin_id"), "native": b.get("token_type") == "native"}
                    for b in raw["balances"]]
        pairs = {(h["network"], h["address"]) for h in holdings if h.get("address")} | {(x["network"], x["address"]) for x in perf[:90] if x.get("address")}
        pairs |= {(chain, x["from_token"]) for x in trades if x.get("from_token")} | {(chain, x["to_token"]) for x in trades if x.get("to_token")}
        imgs = await self.token_images(pairs, {h["coingecko_coin_id"] for h in holdings if h.get("native") and h.get("coingecko_coin_id")})
        for h in holdings:
            h["image"] = imgs.get(f"coin:{h['coingecko_coin_id']}") if h.get("native") else imgs.get(f"{h['network']}:{(h['address'] or '').lower()}")
        for x in perf:
            x["image"] = imgs.get(f"{x['network']}:{(x['address'] or '').lower()}")
        for x in trades:
            x["from_image"] = imgs.get(f"{chain}:{(x['from_token'] or '').lower()}")
            x["to_image"] = imgs.get(f"{chain}:{(x['to_token'] or '').lower()}")
        return {
            "profile": prof, "chain": chain, "chain_label": config.WALLET_CHAINS.get(chain, chain), "holdings": holdings, "performance": perf,
            "networks": raw["networks"], "trades": trades,
            "transfers": [{"t": x.get("block_timestamp"), "direction": x.get("direction"), "symbol": x.get("symbol"), "amount": f(x.get("amount")),
                           "counterparty": x.get("from_address") if x.get("direction") == "in" else x.get("to_address"), "token": x.get("token_address"), "tx": x.get("tx_hash")}
                          for x in transfers],
            "elapsed_ms": round((time.perf_counter() - t0) * 1000),
        }

    # ----- Radar -----
    async def candidates(self, chain: str, source: str, n_tokens: int):
        if source == "new":
            d = await self.cg.get(f"/onchain/networks/{chain}/new_pools", {"include": "base_token", "page": 1}, ttl=60)
            pools, included = d.get("data", []), {i["id"]: i for i in d.get("included", [])}
        else:
            pools, included = await self.cg.trending_pools(chain, "24h" if source == "trending_24h" else "1h", 40)
        tokens, seen_tok = [], set()
        for p in pools:
            tid = p["relationships"]["base_token"]["data"]["id"]
            addr = tid.split("_", 1)[1]
            if addr.lower() in seen_tok:
                continue
            seen_tok.add(addr.lower())
            tok = included.get(tid, {}).get("attributes", {})
            tokens.append({"address": addr, "symbol": tok.get("symbol") or p["attributes"].get("name", "").split(" / ")[0],
                           "image_url": tok.get("image_url") if tok.get("image_url") not in (None, "missing.png") else None, "pool": p["attributes"]["address"]})
            if len(tokens) >= n_tokens:
                break

        async def top(tok):
            try:
                d = await self.cg.get(f"/onchain/networks/{chain}/tokens/{tok['address']}/top_traders", {"traders": 25, "include_address_label": "true"}, ttl=120)
                return tok, d["data"]["attributes"]["traders"]
            except Exception:
                return tok, []

        by: dict[str, dict] = {}
        for tok, traders in await asyncio.gather(*(top(t) for t in tokens)):
            for t in traders:
                k = t["address"].lower()
                c = by.setdefault(k, {"address": t["address"], "short": short(t["address"]), "label": t.get("label") or t.get("name"), "label_type": t.get("type"),
                                      "seen_in": [], "realized_seen_usd": 0.0, "bought_seen_usd": 0.0, "trades_seen": 0, "likely_bot": False})
                c["seen_in"].append({"symbol": tok["symbol"], "address": tok["address"], "image_url": tok["image_url"], "realized": round(f(t.get("realized_pnl_usd"), 0))})
                c["realized_seen_usd"] += f(t.get("realized_pnl_usd"), 0)
                c["bought_seen_usd"] += f(t.get("total_buy_usd"), 0)
                c["trades_seen"] += (t.get("total_buy_count") or 0) + (t.get("total_sell_count") or 0)
                c["likely_bot"] = c["likely_bot"] or likely_bot_row(t)
        cands = sorted(by.values(), key=lambda c: (c["likely_bot"], c["trades_seen"] / len(c["seen_in"]) > 300, -len(c["seen_in"]), -c["realized_seen_usd"]))
        for c in cands:
            c["realized_seen_usd"] = round(c["realized_seen_usd"])
            c["bought_seen_usd"] = round(c["bought_seen_usd"])
        return {"chain": chain, "source": source, "tokens": tokens, "candidates": cands[:150]}

    async def run_radar(self, chain: str, cands: list[dict]):
        t0 = time.perf_counter()
        cg0 = self.cg.calls
        usage = Usage()
        yield "start", {"chain": chain, "total": len(cands), "candidates": cands}
        q: asyncio.Queue = asyncio.Queue()

        async def one(c):
            try:
                hint = [{"token": s["symbol"], "realized_usd": s["realized"]} for s in c.get("seen_in", [])][:8]
                p = await self.profiler.profile_wallet(chain, c["address"], usage, hint={"tokens": hint} if hint else None)
                await q.put({**p, "candidate": c})
            except Exception as e:
                await q.put({"address": c["address"], "error": type(e).__name__, "candidate": c})

        tasks = [asyncio.create_task(one(c)) for c in cands]
        for k in range(len(cands)):
            yield "wallet", await q.get()
            yield "progress", {"done": k + 1, "total": len(cands), "elapsed_ms": round((time.perf_counter() - t0) * 1000), **usage.snapshot()}
        await asyncio.gather(*tasks)
        yield "done", {"elapsed_ms": round((time.perf_counter() - t0) * 1000), "cg_calls": self.cg.calls - cg0, **usage.snapshot()}
