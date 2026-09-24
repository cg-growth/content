import sqlite3
import time

from .. import config

SCHEMA = """CREATE TABLE IF NOT EXISTS fng (
  ts INTEGER NOT NULL, coin_id TEXT NOT NULL, idx REAL, market REAL, news REAL, holistic REAL,
  momentum REAL, volatility REAL, volume REAL, range_pos REAL, headlines INTEGER, insights REAL
);
CREATE INDEX IF NOT EXISTS fng_coin_ts ON fng(coin_id, ts);"""

COLUMNS = ("ts", "coin_id", "idx", "market", "news", "holistic", "momentum", "volatility", "volume", "range_pos", "headlines", "insights")


def _db():
    config.DATA_DIR.mkdir(exist_ok=True)
    con = sqlite3.connect(config.DATA_DIR / "fng.sqlite")
    con.executescript(SCHEMA)
    have = {r[1] for r in con.execute("PRAGMA table_info(fng)")}
    if "insights" not in have:
        con.execute("ALTER TABLE fng ADD COLUMN insights REAL")
    return con


def save(rows: list[dict]):
    ts = int(time.time() * 1000)
    with _db() as con:
        con.executemany(
            f"INSERT INTO fng ({','.join(COLUMNS)}) VALUES ({','.join('?' * len(COLUMNS))})",
            [
                (ts, r["coin"]["id"], r["fng"], r["market_score"], r["news_score"], r["components"].get("holistic"),
                 r["components"].get("momentum"), r["components"].get("volatility"), r["components"].get("volume"),
                 r["components"].get("range"), r["relevant_headlines"], r.get("insights_score"))
                for r in rows
            ],
        )


def history(coin_id: str, limit: int = 500) -> list[dict]:
    with _db() as con:
        cur = con.execute("SELECT ts, idx FROM fng WHERE coin_id=? ORDER BY ts DESC LIMIT ?", (coin_id, limit))
        return [{"t": ts, "index": v} for ts, v in reversed(cur.fetchall())]
