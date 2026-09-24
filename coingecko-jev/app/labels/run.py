import asyncio
import time

from ..cg_rest import CGRest
from ..jev import Jev, Usage, answers_to_dict
from .feed import attach_info, load_rows_for_labelling
from .labeler import COMPOSITE_FORMULA, summarize
from .questions import CRITERIA_SIZES, QUESTIONS
from .state import build_state


async def run_labels(cg: CGRest, jev: Jev, chain: str, pool_ids: list[str]):
    """Async generator of (event, payload) tuples."""
    t0 = time.perf_counter()
    usage = Usage()
    cg_calls0 = cg.calls
    rows = await load_rows_for_labelling(cg, chain, pool_ids)
    await attach_info(cg, chain, rows)
    yield "start", {"total": len(rows), "formula": COMPOSITE_FORMULA, "prep_ms": round((time.perf_counter() - t0) * 1000)}

    queue: asyncio.Queue = asyncio.Queue()

    async def one(idx, row):
        state = build_state(row, chain)
        try:
            r, ms, toks = await jev.ask(state, QUESTIONS, usage)
            answers = answers_to_dict(r, CRITERIA_SIZES)
            await queue.put({"id": row["id"], "index": idx, "row": row_public(row), "state": state, "answers": answers,
                             **summarize(answers), "latency_ms": ms, "input_tokens": toks})
        except Exception as e:
            await queue.put({"id": row["id"], "index": idx, "row": row_public(row),
                             "error": f"{type(e).__name__}: {str(e)[:160]}", "state": state})

    tasks = [asyncio.create_task(one(i, r)) for i, r in enumerate(rows)]
    for i in range(len(rows)):
        item = await queue.get()
        yield "row", item
        yield "progress", {"done": i + 1, "total": len(rows), "elapsed_ms": round((time.perf_counter() - t0) * 1000),
                           **usage.snapshot()}
    await asyncio.gather(*tasks)
    yield "done", {"elapsed_ms": round((time.perf_counter() - t0) * 1000), "cg_calls": cg.calls - cg_calls0, **usage.snapshot()}


def row_public(row: dict) -> dict:
    return {k: v for k, v in row.items() if k not in ("info",)}
