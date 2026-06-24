"""
Crypto Dollar-Cost Averaging (DCA) Bot - Paper Trading
======================================================
This script demonstrates a simple, educational DCA bot that:
1) Fetches real-time prices from CoinGecko
2) Calculates fixed-amount buys on a schedule
3) Logs transactions to SQLite
4) (Optional) Adjusts buy size using a simple moving average

Disclaimer: This is for educational purposes only and not financial advice.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Load environment variables from .env if present
load_dotenv()

# =============================================================================
# Configuration
# =============================================================================
DEMO_KEYS = [
    os.getenv("CG_DEMO_API_KEY"),
    os.getenv("COINGECKO_DEMO_API_KEY"),
]
PRO_KEYS = [
    os.getenv("CG_PRO_API_KEY"),
    os.getenv("COINGECKO_PRO_API_KEY"),
]

DEMO_API_KEY = next((k for k in DEMO_KEYS if k), None)
PRO_API_KEY = next((k for k in PRO_KEYS if k), None)

USE_PRO = PRO_API_KEY is not None
API_KEY = PRO_API_KEY if USE_PRO else DEMO_API_KEY

if not API_KEY:
    raise SystemExit(
        "Missing API key. Set CG_DEMO_API_KEY or CG_PRO_API_KEY in .env."
    )

BASE_URL = (
    "https://pro-api.coingecko.com/api/v3"
    if USE_PRO
    else "https://api.coingecko.com/api/v3"
)
API_HEADER_NAME = "x-cg-pro-api-key" if USE_PRO else "x-cg-demo-api-key"

HEADERS = {
    "accept": "application/json",
    API_HEADER_NAME: API_KEY,
}

# DCA Parameters
INVESTMENT_AMOUNT_USD = 50.0
VS_CURRENCY = "usd"

# Use top 10 by market cap (recommended). Falls back to TARGET_COINS if needed.
USE_TOP_MARKET_COINS = True
REQUIRED_COINS = ["bitcoin", "ethereum", "cardano"]
EXCLUDE_STABLECOINS = True
EXCLUDE_DERIVATIVES = True
MIN_24H_VOLUME_USD = 10_000_000
STABLECOIN_IDS = {
    "tether",
    "usd-coin",
    "dai",
    "trueusd",
    "pax-dollar",
    "paxos-standard",
    "gemini-dollar",
    "binance-usd",
    "frax",
    "first-digital-usd",
    "paypal-usd",
    "usdd",
    "usdp",
    "usds",
    "binance-bridged-usdt-bnb-smart-chain",
    "binance-bridged-usdc-bnb-smart-chain",
    "tether-eurt",
    "euro-coin",
}
DERIVATIVE_IDS = {
    "staked-ether",
    "lido-staked-ether",
    "wrapped-bitcoin",
    "weth",
    "wbtc",
    "rocket-pool-eth",
    "binance-wrapped-btc",
    "wrapped-steth",
    "wrapped-beacon-eth",
    "wrapped-eeth",
}
MANUAL_EXCLUDE_IDS = {
    "figure-heloc",
    "whitebit",
}
TARGET_COINS = [
    "bitcoin",
    "ethereum",
    "cardano",
    "solana",
    "ripple",
    "tether",
    "usd-coin",
    "binancecoin",
    "dogecoin",
    "tron",
]

# Scheduler defaults (24h clock)
DAILY_HOUR = 9
DAILY_MINUTE = 0
WEEKLY_DAY = "mon"

# Smart DCA (optional)
SMART_DCA_ENABLED = False
SMART_DCA_DAYS = 30
SMART_DCA_WINDOW = 7
SMART_DCA_DIP_PCT = 0.05
SMART_DCA_BOOST = 1.5

# SQLite database
DB_PATH = Path(__file__).with_name("dca.db")
REPORT_PATH = Path(__file__).with_name("dca_report.html")


# =============================================================================
# API Helpers
# =============================================================================
def cg_request(endpoint: str, params: Optional[Dict] = None) -> Dict:
    """Make a GET request to CoinGecko with basic retry handling."""
    url = f"{BASE_URL}{endpoint}"
    retries = 3
    last_error: Optional[Exception] = None

    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, params=params, timeout=20)

            if response.status_code == 429:
                sleep_time = 2 ** attempt
                print(f"Rate limited. Sleeping {sleep_time}s and retrying...")
                time.sleep(sleep_time)
                continue

            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            if attempt == retries - 1:
                last_error = exc
                break
            time.sleep(1 + attempt)
            last_error = exc

    if last_error:
        raise RuntimeError(f"API request failed after {retries} retries: {last_error}")
    raise RuntimeError(f"API request failed after {retries} retries due to rate limiting.")


def get_coin_list() -> List[Dict]:
    """Fetch the full coin list for symbol -> ID mapping."""
    return cg_request("/coins/list")


def resolve_coin_ids(targets: List[str]) -> List[str]:
    """
    Resolve coin symbols/ids into CoinGecko coin IDs.

    If a target already matches an ID, it is kept. Otherwise, we map symbols
    using /coins/list and take the first match.
    """
    if not targets:
        return []

    coin_list = get_coin_list()
    id_set = {coin["id"] for coin in coin_list}
    symbol_map: Dict[str, List[str]] = {}

    for coin in coin_list:
        symbol = coin.get("symbol", "").lower()
        if symbol:
            symbol_map.setdefault(symbol, []).append(coin["id"])

    resolved = []
    for target in targets:
        t = target.lower().strip()
        if t in id_set:
            resolved.append(t)
        elif t in symbol_map:
            resolved.append(symbol_map[t][0])
        else:
            print(f"Warning: Could not resolve coin '{target}'. Skipping.")

    return resolved


def get_prices(coin_ids: List[str], vs_currency: str = "usd") -> Dict:
    """Fetch current prices for multiple coins in one call."""
    if not coin_ids:
        return {}

    params = {
        "ids": ",".join(coin_ids),
        "vs_currencies": vs_currency,
        "include_24hr_change": "true",
    }
    return cg_request("/simple/price", params=params)


def get_top_market_coins(
    limit: int = 10,
    vs_currency: str = "usd",
    exclude_ids: Optional[set] = None,
) -> List[str]:
    """Fetch top coins by market cap using /coins/markets."""
    params = {
        "vs_currency": vs_currency,
        "order": "market_cap_desc",
        "per_page": max(limit * 5, 50),
        "page": 1,
        "sparkline": "false",
    }
    data = cg_request("/coins/markets", params=params)
    exclude_ids = exclude_ids or set()

    ranked = [
        coin
        for coin in data
        if coin.get("id")
        and coin.get("market_cap_rank") is not None
        and coin.get("id") not in exclude_ids
        and (coin.get("total_volume") or 0) >= MIN_24H_VOLUME_USD
    ]
    ranked.sort(key=lambda c: c.get("market_cap_rank"))

    filtered = [coin.get("id") for coin in ranked]
    return filtered[:limit]


def merge_required_coins(
    top_ids: List[str], required_ids: List[str], limit: int
) -> List[str]:
    """Ensure required coin IDs are included while keeping the list size."""
    merged = list(top_ids)
    for coin_id in required_ids:
        if coin_id and coin_id not in merged:
            merged.append(coin_id)

    while len(merged) > limit:
        # Remove the last non-required coin to keep size stable.
        removed = False
        for i in range(len(merged) - 1, -1, -1):
            if merged[i] not in required_ids:
                merged.pop(i)
                removed = True
                break
        if not removed:
            # All remaining coins are required; stop trimming.
            break

    return merged[:limit]


def get_market_chart(coin_id: str, vs_currency: str = "usd", days: int = 30) -> Dict:
    """Fetch historical market chart data for a coin."""
    params = {"vs_currency": vs_currency, "days": str(days)}
    return cg_request(f"/coins/{coin_id}/market_chart", params=params)


# =============================================================================
# SQLite Helpers
# =============================================================================
def init_db(db_path: Path) -> None:
    """Initialize the transactions table if it doesn't exist."""
    conn = sqlite3.connect(db_path)
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                coin_id TEXT NOT NULL,
                price REAL NOT NULL,
                units REAL NOT NULL,
                amount_usd REAL NOT NULL
            )
            """
        )
    conn.close()


def log_transaction(
    db_path: Path,
    coin_id: str,
    price: float,
    units: float,
    amount_usd: float,
    timestamp: Optional[str] = None,
) -> None:
    """Insert a transaction record into SQLite."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()

    conn = sqlite3.connect(db_path)
    with conn:
        conn.execute(
            """
            INSERT INTO transactions (timestamp, coin_id, price, units, amount_usd)
            VALUES (?, ?, ?, ?, ?)
            """,
            (timestamp, coin_id, price, units, amount_usd),
        )
    conn.close()


def get_portfolio_summary(db_path: Path) -> Dict[str, Dict[str, float]]:
    """Return total invested, units, and average cost for each coin."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT coin_id, SUM(amount_usd) AS total_invested, SUM(units) AS total_units
        FROM transactions
        GROUP BY coin_id
        """
    )
    rows = cursor.fetchall()
    conn.close()

    summary = {}
    for coin_id, total_invested, total_units in rows:
        if total_units and total_units > 0:
            avg_cost = total_invested / total_units
        else:
            avg_cost = 0.0
        summary[coin_id] = {
            "total_invested": total_invested or 0.0,
            "total_units": total_units or 0.0,
            "avg_cost": avg_cost,
        }
    return summary


def get_transactions(db_path: Path, limit: int = 200) -> List[Dict[str, float]]:
    """Fetch recent transactions for reporting."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT timestamp, coin_id, price, units, amount_usd
        FROM transactions
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()

    transactions = []
    for ts, coin_id, price, units, amount_usd in rows:
        transactions.append(
            {
                "timestamp": ts,
                "coin_id": coin_id,
                "price": price,
                "units": units,
                "amount_usd": amount_usd,
            }
        )
    return transactions


def generate_report(db_path: Path, output_path: Path, vs_currency: str = "usd") -> None:
    """Generate a simple HTML report for screenshots or quick review."""
    summary = get_portfolio_summary(db_path)
    transactions = get_transactions(db_path)
    prices = get_prices(list(summary.keys()), vs_currency=vs_currency) if summary else {}

    summary_rows = []
    for coin_id, stats in summary.items():
        current_price = prices.get(coin_id, {}).get(vs_currency, 0.0)
        market_value = current_price * stats["total_units"]
        unrealized_pnl = market_value - stats["total_invested"]
        summary_rows.append(
            f"<tr><td>{coin_id}</td><td>${stats['total_invested']:,.2f}</td>"
            f"<td>{stats['total_units']:,.6f}</td><td>${stats['avg_cost']:,.4f}</td>"
            f"<td>${current_price:,.4f}</td><td>${unrealized_pnl:,.2f}</td></tr>"
        )

    tx_rows = []
    for tx in transactions:
        tx_rows.append(
            f"<tr><td>{tx['timestamp']}</td><td>{tx['coin_id']}</td>"
            f"<td>${tx['price']:,.4f}</td><td>{tx['units']:,.6f}</td>"
            f"<td>${tx['amount_usd']:,.2f}</td></tr>"
        )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>DCA Bot Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #f6f7fb; color: #111; }}
    .card {{ background: #fff; padding: 16px 20px; border-radius: 12px; box-shadow: 0 6px 24px rgba(0,0,0,0.06); margin-bottom: 20px; }}
    h1 {{ margin: 0 0 6px; font-size: 22px; }}
    h2 {{ margin: 0 0 12px; font-size: 16px; color: #333; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ padding: 8px 10px; border-bottom: 1px solid #e6e9ef; text-align: left; }}
    th {{ background: #f0f2f7; font-weight: 600; }}
    .muted {{ color: #666; font-size: 12px; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Crypto DCA Bot Report</h1>
    <div class="muted">Generated: {datetime.now(timezone.utc).isoformat()}</div>
  </div>

  <div class="card">
    <h2>Portfolio Summary</h2>
    <table>
      <thead>
        <tr>
          <th>Coin</th>
          <th>Total Invested</th>
          <th>Total Units</th>
          <th>Avg Cost</th>
          <th>Current Price</th>
          <th>Unrealized PnL</th>
        </tr>
      </thead>
      <tbody>
        {''.join(summary_rows) if summary_rows else '<tr><td colspan="6">No data yet.</td></tr>'}
      </tbody>
    </table>
  </div>

  <div class="card">
    <h2>Recent Transactions</h2>
    <table>
      <thead>
        <tr>
          <th>Timestamp (UTC)</th>
          <th>Coin</th>
          <th>Price</th>
          <th>Units</th>
          <th>Amount (USD)</th>
        </tr>
      </thead>
      <tbody>
        {''.join(tx_rows) if tx_rows else '<tr><td colspan="5">No transactions yet.</td></tr>'}
      </tbody>
    </table>
  </div>
</body>
</html>
"""

    output_path.write_text(html, encoding="utf-8")
    print(f"Report written to: {output_path}")


def print_unrealized_pnl(db_path: Path, vs_currency: str = "usd") -> None:
    """Calculate and print unrealized PnL per coin using current price."""
    summary = get_portfolio_summary(db_path)
    if not summary:
        print("No transactions yet.")
        return

    coin_ids = list(summary.keys())
    prices = get_prices(coin_ids, vs_currency=vs_currency)

    print("\nPortfolio Summary")
    print("-" * 60)
    for coin_id, stats in summary.items():
        current_price = prices.get(coin_id, {}).get(vs_currency, 0.0)
        avg_cost = stats["avg_cost"]
        units = stats["total_units"]
        total_invested = stats["total_invested"]
        market_value = current_price * units
        unrealized_pnl = market_value - total_invested

        print(f"{coin_id}:")
        print(f"  Total invested: ${total_invested:,.2f}")
        print(f"  Total units:    {units:,.6f}")
        print(f"  Avg cost:       ${avg_cost:,.4f}")
        print(f"  Current price:  ${current_price:,.4f}")
        print(f"  Unrealized PnL: ${unrealized_pnl:,.2f}")
        print()


# =============================================================================
# DCA Logic
# =============================================================================
def calculate_sma(prices: List[float], window: int) -> Optional[float]:
    """Calculate a simple moving average."""
    if len(prices) < window:
        return None
    return sum(prices[-window:]) / window


def apply_smart_dca(
    coin_id: str,
    base_amount: float,
    current_price: float,
    vs_currency: str = "usd",
    days: int = 30,
    window: int = 7,
    dip_pct: float = 0.05,
    boost: float = 1.5,
) -> float:
    """
    If price is below SMA by dip_pct, increase buy size by boost.
    Otherwise, use the base amount.
    """
    chart = get_market_chart(coin_id, vs_currency=vs_currency, days=days)
    prices = [p[1] for p in chart.get("prices", [])]
    sma = calculate_sma(prices, window)

    if sma is None:
        return base_amount

    if current_price < sma * (1 - dip_pct):
        return base_amount * boost

    return base_amount


def execute_dca_buy(
    coin_ids: List[str],
    investment_amount_usd: float,
    vs_currency: str = "usd",
    smart: bool = False,
    report: bool = False,
) -> None:
    """Execute a paper DCA buy for each coin and log the transaction."""
    prices = get_prices(coin_ids, vs_currency=vs_currency)
    timestamp = datetime.now(timezone.utc).isoformat()

    print("\nExecuting DCA buy...")
    for coin_id in coin_ids:
        price = prices.get(coin_id, {}).get(vs_currency)
        if not price:
            print(f"  Skipping {coin_id}: no price available.")
            continue

        amount = investment_amount_usd
        if smart:
            amount = apply_smart_dca(
                coin_id=coin_id,
                base_amount=investment_amount_usd,
                current_price=price,
                vs_currency=vs_currency,
                days=SMART_DCA_DAYS,
                window=SMART_DCA_WINDOW,
                dip_pct=SMART_DCA_DIP_PCT,
                boost=SMART_DCA_BOOST,
            )

        units = amount / price

        print(f"  BUY {coin_id}: ${amount:.2f} at ${price:.4f} -> {units:.6f} units")

        log_transaction(
            db_path=DB_PATH,
            coin_id=coin_id,
            price=price,
            units=units,
            amount_usd=amount,
            timestamp=timestamp,
        )

    print_unrealized_pnl(DB_PATH, vs_currency=vs_currency)
    if report:
        generate_report(DB_PATH, REPORT_PATH, vs_currency=vs_currency)


# =============================================================================
# Scheduling
# =============================================================================
def start_scheduler(
    coin_ids: List[str],
    investment_amount_usd: float,
    schedule: str,
    smart: bool = False,
) -> None:
    """Start a blocking scheduler to run the DCA job."""
    scheduler = BlockingScheduler()

    if schedule == "daily":
        trigger = CronTrigger(hour=DAILY_HOUR, minute=DAILY_MINUTE)
    elif schedule == "weekly":
        trigger = CronTrigger(day_of_week=WEEKLY_DAY, hour=DAILY_HOUR, minute=DAILY_MINUTE)
    else:
        raise ValueError("Schedule must be 'daily' or 'weekly'.")

    scheduler.add_job(
        execute_dca_buy,
        trigger=trigger,
        args=[coin_ids, investment_amount_usd, VS_CURRENCY, smart],
        id="dca_job",
        replace_existing=True,
    )

    print(f"Scheduler started ({schedule}). Press Ctrl+C to stop.")
    scheduler.start()


# =============================================================================
# CLI
# =============================================================================
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crypto DCA Bot (Paper Trading)")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single DCA buy immediately and exit.",
    )
    parser.add_argument(
        "--schedule",
        choices=["daily", "weekly"],
        help="Run on a schedule (daily or weekly).",
    )
    parser.add_argument(
        "--smart",
        action="store_true",
        help="Enable smart DCA sizing based on a moving average.",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate a simple HTML report after running.",
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Run immediately once before starting the schedule.",
    )
    return parser.parse_args()


def main() -> None:
    print("=" * 60)
    print("CRYPTO DCA BOT (PAPER TRADING)")
    print("=" * 60)
    print("Disclaimer: Educational only. Not financial advice.\n")

    init_db(DB_PATH)

    if USE_TOP_MARKET_COINS:
        try:
            exclude_ids = set()
            if EXCLUDE_STABLECOINS:
                exclude_ids |= STABLECOIN_IDS
            if EXCLUDE_DERIVATIVES:
                exclude_ids |= DERIVATIVE_IDS
            exclude_ids |= MANUAL_EXCLUDE_IDS
            top_ids = get_top_market_coins(
                limit=10,
                vs_currency=VS_CURRENCY,
                exclude_ids=exclude_ids,
            )
            required_ids = resolve_coin_ids(REQUIRED_COINS)
            coin_ids = merge_required_coins(top_ids, required_ids, limit=10)
        except Exception as exc:
            print(f"Warning: failed to fetch top coins ({exc}). Using fallback list.")
            coin_ids = resolve_coin_ids(TARGET_COINS)
    else:
        coin_ids = resolve_coin_ids(TARGET_COINS)

    if not coin_ids:
        raise SystemExit("No valid coin IDs found. Check TARGET_COINS.")

    args = parse_args()
    smart = args.smart or SMART_DCA_ENABLED
    report = args.report

    if args.schedule:
        if args.run_now:
            execute_dca_buy(
                coin_ids=coin_ids,
                investment_amount_usd=INVESTMENT_AMOUNT_USD,
                vs_currency=VS_CURRENCY,
                smart=smart,
                report=report,
            )
        start_scheduler(
            coin_ids=coin_ids,
            investment_amount_usd=INVESTMENT_AMOUNT_USD,
            schedule=args.schedule,
            smart=smart,
        )
        return

    execute_dca_buy(
        coin_ids=coin_ids,
        investment_amount_usd=INVESTMENT_AMOUNT_USD,
        vs_currency=VS_CURRENCY,
        smart=smart,
        report=report,
    )


if __name__ == "__main__":
    main()
