"""Wallet profiling shared by Wallet X-ray, Pump Pulse, Wallet Profile and Radar.

Global profile per wallet (cached): multi-chain PnL + multi-chain balances + recent trades on the primary chain.
Token context adds trades in the token and, for holders that never bought, where their tokens came from.
"""
import asyncio
import time

from .. import config
from ..cg_rest import CGRest
from ..jev import Jev, Usage, answers_to_dict
from ..util import short
from .features import (
    activity_features, funding_features, is_protocol_holder, pnl_features, portfolio_features, token_features, top_traded_tokens,
)
from .questions import PERSONA_LABEL, PROFILE_QUESTIONS, PROFILE_SIZES, TAG_LABEL, TAGS, WALLET_QUESTIONS, WALLET_SIZES

ALL_NETS = ",".join(config.WALLET_CHAINS)
# Some chains aren't supported by every wallet endpoint (see config.WALLET_CHAIN_CAPS). Scoping the
# `networks` filter per endpoint keeps one unsupported chain from failing the whole multi-chain call.
PNL_NETS = ",".join(c for c in config.WALLET_CHAINS if config.wallet_caps(c).get("pnl", True))
BALANCES_NETS = ",".join(c for c in config.WALLET_CHAINS if config.wallet_caps(c).get("balances", True))
ZERO = "0x0000000000000000000000000000000000000000"


def copy_worthy(persona: str, a: dict, g: dict) -> bool:
    """Explainable rule over Jev's typed answers: proven, skilled, not insider-like, recently active."""
    days = (g.get("recent_activity") or {}).get("days_since_last_trade")
    insider = (a.get("insider") or {}).get("value", 0)
    return persona == "proven_trader" and a["skill"]["value"] >= 70 and insider < 0.5 and days is not None and days <= 30


def code_tags(g: dict) -> list[str]:
    L, P, R = g.get("lifetime") or {}, g.get("portfolio") or {}, g.get("recent_activity") or {}
    tags = []
    if (R.get("recent_trades_per_day") or 0) >= 200 or (R.get("median_seconds_between_trades") is not None and R["median_seconds_between_trades"] <= 10 and R.get("recent_trades", 0) >= 20):
        tags.append("high_frequency")
    if len(L.get("active_networks") or []) >= 3:
        tags.append("multi_chain")
    if (P.get("portfolio_value_usd") or 0) >= 1_000_000:
        tags.append("whale_sized")
    if (P.get("stablecoin_share") or 0) >= 0.5 and (P.get("portfolio_value_usd") or 0) >= 1000:
        tags.append("stablecoin_heavy")
    if R.get("days_since_last_trade") is None or R["days_since_last_trade"] > 30:
        tags.append("dormant")
    return tags


class WalletProfiler:
    def __init__(self, cg: CGRest, jev: Jev):
        self.cg, self.jev = cg, jev
        self._global: dict[str, tuple[float, dict]] = {}
        self._results: dict[str, tuple[float, dict]] = {}
        self._inflight: dict[str, asyncio.Task] = {}
        self._sem = asyncio.Semaphore(config.XRAY_CONCURRENCY)

    async def global_profile(self, chain: str, addr: str) -> dict:
        key = f"{chain}:{addr.lower()}"
        hit = self._global.get(key)
        if hit and time.time() - hit[0] < config.WALLET_CACHE_TTL_S:
            return hit[1]

        async def get(path, params):
            try:
                return await self.cg.get(path, params)
            except Exception:
                return None

        pnl, bal, trd = await asyncio.gather(
            get(f"/onchain/wallets/{addr}/pnl", {"networks": PNL_NETS, "per_page": 200, "sort": "total_buy_usd_desc"}),
            get(f"/onchain/wallets/{addr}/balances", {"networks": BALANCES_NETS, "per_page": 50, "value_usd_min": 1}),
            get(f"/onchain/networks/{chain}/wallets/{addr}/trades", {"per_page": 100}),
        )
        pnl_attrs = ((pnl or {}).get("data") or {}).get("attributes")
        bal_attrs = ((bal or {}).get("data") or {}).get("attributes")
        trades = [t["attributes"] for t in (trd or {}).get("data", [])]
        g = {
            "lifetime": pnl_features(pnl_attrs),
            "portfolio": portfolio_features(bal_attrs),
            "recent_activity": activity_features(trades),
            "top_traded_tokens": top_traded_tokens(pnl_attrs),
            "_raw": {"token_stats": (pnl_attrs or {}).get("token_stats") or [], "networks": (pnl_attrs or {}).get("networks") or [],
                     "balances": (bal_attrs or {}).get("balances") or [], "trades": trades},
        }
        g["code_tags"] = code_tags(g)
        self._global[key] = (time.time(), g)
        return g

    @staticmethod
    def jev_view(g: dict) -> dict:
        return {k: v for k, v in g.items() if not k.startswith("_") and k != "code_tags"}

    # ----- token context (X-ray, Pump Pulse) -----
    async def profile(self, chain: str, token: str, row: dict, ctx: dict, usage: Usage | None = None) -> dict:
        addr = row["address"]
        key = f"{chain}:{token.lower()}:{addr.lower()}"
        hit = self._results.get(key)
        if hit and time.time() - hit[0] < config.WALLET_CACHE_TTL_S:
            return hit[1]
        if key in self._inflight:
            return await self._inflight[key]
        task = asyncio.create_task(self._profile(chain, token, row, ctx, usage))
        self._inflight[key] = task
        try:
            res = await task
            self._results[key] = (time.time(), res)
            return res
        finally:
            self._inflight.pop(key, None)

    async def _profile(self, chain, token, row, ctx, usage):
        base = {"address": row["address"], "short": short(row["address"]), "source": row.get("_source"),
                "label": row.get("label") or row.get("name"), "explorer_url": row.get("explorer_url"), "chain": chain}
        if is_protocol_holder(row):
            return {**base, "persona": "protocol", "persona_label": PERSONA_LABEL["protocol"], "scored": False, "token": token_features(row, [], ctx)}
        async with self._sem:
            g = await self.global_profile(chain, row["address"])
            token_trades, funding = [], None
            try:
                d = await self.cg.get(f"/onchain/networks/{chain}/wallets/{row['address']}/trades", {"token": token, "per_page": 100})
                token_trades = [t["attributes"] for t in d.get("data", [])]
            except Exception:
                pass
            if not row.get("total_buy_count") and not token_trades and "holder" in (row.get("_source") or ""):
                try:
                    d = await self.cg.get(f"/onchain/networks/{chain}/wallets/{row['address']}/transfers", {"token": token, "direction": "in", "per_page": 20})
                    funding = funding_features([t.get("attributes", t) for t in d.get("data", [])], ctx.get("holder_addrs") or set(), {ZERO, token.lower()})
                except Exception:
                    funding = None
        tf = token_features(row, token_trades, ctx)
        if funding:
            tf["how_tokens_arrived"] = funding
        state = {"token": ctx.get("symbol"), "wallet_on_this_token": tf, **self.jev_view(g), "derived_tags": g["code_tags"]}
        r, ms, toks = await self.jev.ask(state, WALLET_QUESTIONS, usage)
        a = answers_to_dict(r, WALLET_SIZES)
        persona = a["persona"]["choice"]
        return {
            **base, "scored": True, "persona": persona, "persona_label": PERSONA_LABEL.get(persona, persona),
            "persona_confidence": a["persona"]["confidence"], "skill": a["skill"]["value"], "skill_confidence": a["skill"]["confidence"],
            "insider": a["insider"]["value"], "copyable": a["copyable"]["value"], "stance": a["stance"]["choice"],
            "copy_worthy": copy_worthy(persona, a, g), "tags": [TAG_LABEL[t] for t in g["code_tags"]],
            "token": tf, "lifetime": g["lifetime"], "recent_activity": g["recent_activity"], "portfolio": {k: v for k, v in g["portfolio"].items() if k != "top_holdings"},
            "answers": a, "latency_ms": ms, "input_tokens": toks,
        }

    # ----- wallet-first (Profile page, Radar) -----
    async def profile_wallet(self, chain: str, addr: str, usage: Usage | None = None, hint: dict | None = None) -> dict:
        key = f"wallet:{chain}:{addr.lower()}"
        hit = self._results.get(key)
        if hit and time.time() - hit[0] < config.WALLET_CACHE_TTL_S:
            return hit[1]
        async with self._sem:
            g = await self.global_profile(chain, addr)
        state = {**self.jev_view(g), "derived_tags": g["code_tags"]}
        if hint:
            state["seen_as_top_trader_in"] = hint
        r, ms, toks = await self.jev.ask(state, PROFILE_QUESTIONS, usage)
        a = answers_to_dict(r, PROFILE_SIZES)
        persona = a["persona"]["choice"]
        jev_tags = [TAG_LABEL[k] for k in TAGS if (a.get(f"tag_{k}") or {}).get("value", 0) >= 0.6]
        res = {
            "address": addr, "short": short(addr), "chain": chain, "scored": True,
            "persona": persona, "persona_label": PERSONA_LABEL.get(persona, persona), "persona_confidence": a["persona"]["confidence"],
            "skill": a["skill"]["value"], "skill_confidence": a["skill"]["confidence"], "copyable": a["copyable"]["value"],
            "style": a["style"]["choice"], "style_confidence": a["style"]["confidence"],
            "copy_worthy": copy_worthy(persona, a, g),
            "tags": jev_tags + [TAG_LABEL[t] for t in g["code_tags"]], "jev_tags": jev_tags,
            "lifetime": g["lifetime"], "portfolio": g["portfolio"], "recent_activity": g["recent_activity"], "top_traded_tokens": g["top_traded_tokens"],
            "answers": a, "latency_ms": ms, "input_tokens": toks,
        }
        self._results[key] = (time.time(), res)
        return res
