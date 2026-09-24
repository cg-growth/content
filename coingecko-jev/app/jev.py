import asyncio
import time
from dataclasses import dataclass, field

from typesafe_sdk import AsyncTypeSafeClient

from . import config


def norm_score(score: float, n_criteria: int) -> float:
    if n_criteria < 2:
        return 0.0
    return max(0.0, min(100.0, score / (n_criteria - 1) * 100.0))


@dataclass
class Usage:
    calls: int = 0
    input_tokens: int = 0
    latencies: list = field(default_factory=list)

    @property
    def cost_usd(self) -> float:
        return self.input_tokens / 1_000_000 * config.JEV_PRICE_PER_MTOK

    def snapshot(self):
        lat = sorted(self.latencies[-200:])
        return {
            "calls": self.calls,
            "input_tokens": self.input_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "p50_ms": lat[len(lat) // 2] if lat else None,
        }


class Jev:
    def __init__(self):
        self._client = AsyncTypeSafeClient(timeout=30.0)
        self._sem = asyncio.Semaphore(config.JEV_CONCURRENCY)
        self.usage = Usage()

    async def close(self):
        await self._client.aclose()

    async def ask(self, state, questions: dict, usage: Usage | None = None, retries: int = 2):
        for attempt in range(retries + 1):
            try:
                async with self._sem:
                    t = time.perf_counter()
                    r = await self._client.system_one(state=state, questions=questions)
                    ms = (time.perf_counter() - t) * 1000
                break
            except Exception:
                if attempt == retries:
                    raise
                await asyncio.sleep(1.0 * (attempt + 1))
        toks = r.usage.input_tokens if r.usage else 0
        for u in filter(None, (self.usage, usage)):
            u.calls += 1
            u.input_tokens += toks
            u.latencies.append(round(ms))
        return r, round(ms), toks


def answers_to_dict(r, criteria_sizes: dict[str, int]) -> dict:
    out = {}
    for qid, a in (r.choices or {}).items():
        out[qid] = {
            "type": "choice",
            "choice": a.choice,
            "confidence": round(a.confidence, 3),
            "probabilities": {k: round(v, 3) for k, v in (a.probabilities or {}).items()},
        }
    for qid, a in (r.scores or {}).items():
        out[qid] = {
            "type": "score",
            "raw": round(a.score, 3),
            "value": round(norm_score(a.score, criteria_sizes.get(qid, 3)), 1),
            "confidence": round(a.confidence, 3),
        }
    for qid, a in (r.nouls or {}).items():
        out[qid] = {"type": "noul", "value": round(a.noul, 3)}
    return out
