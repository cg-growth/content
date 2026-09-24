"""JSONL record/replay. Each line: {"t": ms since start, "ev": name, "data": payload}."""
import asyncio
import json
import re
import time
from datetime import datetime
from pathlib import Path

from . import config

SAFE = re.compile(r"^[a-z0-9_-]+\.jsonl$")


class Recorder:
    def __init__(self, demo: str, tag: str):
        config.FIXTURES_DIR.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.name = f"{demo}-{tag}-{stamp}.jsonl"
        self.path = config.FIXTURES_DIR / self.name
        self._fh = self.path.open("w")
        self._t0 = time.perf_counter()

    def write(self, ev: str, data):
        self._fh.write(json.dumps({"t": round((time.perf_counter() - self._t0) * 1000), "ev": ev, "data": data}) + "\n")
        self._fh.flush()

    def close(self):
        self._fh.close()


def fixture_path(name: str) -> Path:
    if not SAFE.match(name):
        raise ValueError("bad fixture name")
    p = config.FIXTURES_DIR / name
    if not p.exists():
        raise FileNotFoundError(name)
    return p


def read_all(name: str) -> list[dict]:
    with fixture_path(name).open() as fh:
        return [json.loads(line) for line in fh if line.strip()]


async def replay(name: str, speed: float = 1.0, skip: tuple = ()):
    last = 0
    for rec in read_all(name):
        if rec["ev"] in skip:
            continue
        gap = (rec["t"] - last) / 1000 / max(speed, 0.01)
        if gap > 0:
            await asyncio.sleep(min(gap, 5))
        last = rec["t"]
        yield rec["ev"], rec["data"]


def list_fixtures(demo: str) -> list[dict]:
    if not config.FIXTURES_DIR.exists():
        return []
    out = []
    for p in sorted(config.FIXTURES_DIR.glob(f"{demo}-*.jsonl"), reverse=True):
        out.append({"name": p.name, "bytes": p.stat().st_size})
    return out
