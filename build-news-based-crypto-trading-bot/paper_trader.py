import sqlite3
from datetime import datetime, timedelta, timezone
from config import (STARTING_CASH_USD, POSITION_PCT, COOLDOWN_HOURS,
                    FEE_PCT, SLIPPAGE_PCT)

class PaperPortfolio:
    def __init__(self, db_path="portfolio.db"):
        self.conn = sqlite3.connect(db_path)
        self._setup()

    def _setup(self):
        # signal_log records every scored headline, not only executed ones.
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS positions (
                coin_id TEXT PRIMARY KEY, qty REAL, entry_price REAL, opened_at TEXT);
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY, coin_id TEXT, side TEXT, qty REAL,
                price REAL, headline TEXT, score REAL, executed_at TEXT);
            CREATE TABLE IF NOT EXISTS signal_log (
                id INTEGER PRIMARY KEY, coin_id TEXT, headline TEXT, score REAL,
                confidence REAL, executed INTEGER, reason TEXT, logged_at TEXT);
            CREATE TABLE IF NOT EXISTS cash (balance REAL);
        """)
        if not self.conn.execute("SELECT 1 FROM cash").fetchone():
            self.conn.execute("INSERT INTO cash VALUES (?)", (STARTING_CASH_USD,))
        self.conn.commit()

    def in_cooldown(self, coin_id):
        """Stop one news cycle from opening five positions in the same coin."""
        row = self.conn.execute(
            "SELECT executed_at FROM trades WHERE coin_id=? ORDER BY id DESC LIMIT 1",
            (coin_id,)).fetchone()
        if not row:
            return False
        last = datetime.fromisoformat(row[0])
        return datetime.now(timezone.utc) - last < timedelta(hours=COOLDOWN_HOURS)

    def buy(self, coin_id, fill_price, headline, score):
        balance = self.conn.execute("SELECT balance FROM cash").fetchone()[0]
        notional = balance * POSITION_PCT

        # Assume an adverse fill and pay the fee. Optimistic fills are the
        # fastest way to build a strategy that only works on paper
        effective_price = fill_price * (1 + SLIPPAGE_PCT)
        cost = notional * (1 + FEE_PCT)
        if cost > balance:
            return None

        qty = notional / effective_price
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute("UPDATE cash SET balance = balance - ?", (cost,))
        self.conn.execute("INSERT OR REPLACE INTO positions VALUES (?,?,?,?)",
                          (coin_id, qty, effective_price, now))
        self.conn.execute(
            "INSERT INTO trades (coin_id, side, qty, price, headline, score, executed_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (coin_id, "BUY", qty, effective_price, headline, score, now))
        self.conn.commit()
        return qty

    def sell(self, coin_id, fill_price, headline, score):
        """Close an open position at the given fill price."""
        row = self.conn.execute(
            "SELECT qty, entry_price FROM positions WHERE coin_id=?", (coin_id,)).fetchone()
        if not row:
            return None
        qty, entry_price = row

        # Selling into a move works against you the same way buying does,
        # so slippage and fees are applied on the way out too
        effective_price = fill_price * (1 - SLIPPAGE_PCT)
        proceeds = qty * effective_price * (1 - FEE_PCT)
        now = datetime.now(timezone.utc).isoformat()

        self.conn.execute("UPDATE cash SET balance = balance + ?", (proceeds,))
        self.conn.execute("DELETE FROM positions WHERE coin_id=?", (coin_id,))
        self.conn.execute(
            "INSERT INTO trades (coin_id, side, qty, price, headline, score, executed_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (coin_id, "SELL", qty, effective_price, headline, score, now))
        self.conn.commit()
        return qty

    def has_position(self, coin_id):
        return self.conn.execute(
            "SELECT 1 FROM positions WHERE coin_id=?", (coin_id,)).fetchone() is not None

    def log_signal(self, coin_id, headline, score, confidence, executed, reason):
        """Record every scored headline; skipping this call leaves the false-signal report empty."""
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO signal_log (coin_id, headline, score, confidence,"
            " executed, reason, logged_at) VALUES (?,?,?,?,?,?,?)",
            (coin_id, headline, score, confidence, int(executed), reason, now))
        self.conn.commit()
