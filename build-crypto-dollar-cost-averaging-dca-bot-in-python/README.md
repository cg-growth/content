> Read the full article: [How to Build a Crypto Dollar Cost Averaging (DCA) Bot in Python](https://www.coingecko.com/learn/build-crypto-dollar-cost-averaging-dca-bot-in-python)

# Crypto Dollar-Cost Averaging (DCA) Bot

A simple, educational DCA bot in Python that fetches real-time prices from CoinGecko, simulates buy orders, and logs transactions to SQLite.

> ⚠️ **Disclaimer:** This is for educational purposes only and not financial advice. This bot performs paper trading (simulated buys) and does not execute real trades.

## Features

- Fetches real-time crypto prices from CoinGecko API
- Simulates fixed-amount DCA buys on a schedule (daily/weekly)
- Logs all transactions to SQLite database
- Calculates portfolio summary with unrealized PnL
- Optional "smart DCA" using moving average dip detection
- Generates HTML reports with portfolio visualization

## Prerequisites

- Python 3.10+
- A CoinGecko API key (free Demo tier works)

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/rollendxavier/crypto_dollar_cost.git
   cd crypto_dollar_cost
   ```

2. **Install dependencies:**
   ```bash
   pip install requests apscheduler python-dotenv
   ```

3. **Set up your API key:**
   
   Create a `.env` file in the project root:
   ```
   CG_DEMO_API_KEY=your_coingecko_demo_api_key
   ```
   
   Or for Pro users:
   ```
   CG_PRO_API_KEY=your_coingecko_pro_api_key
   ```

## Usage

### Run once (single DCA execution):
```bash
python dca_bot.py --once
```

### Run with HTML report generation:
```bash
python dca_bot.py --once --report
```

### Run on a daily schedule:
```bash
python dca_bot.py --schedule daily
```

### Run on a weekly schedule (Mondays at 9 AM):
```bash
python dca_bot.py --schedule weekly
```

## Example Output

```
============================================================
CRYPTO DCA BOT (PAPER TRADING)
============================================================
Disclaimer: Educational only. Not financial advice.

Executing DCA buy...
  BUY bitcoin: $50.00 at $42500.1234 -> 0.001176 units
  BUY ethereum: $50.00 at $2300.5678 -> 0.021734 units

Portfolio Summary
------------------------------------------------------------
bitcoin:
  Total invested: $50.00
  Total units:    0.001176
  Avg cost:       $42500.1234
  Current price:  $42500.1234
  Unrealized PnL: $0.00
```

## Configuration

Edit the following constants in `dca_bot.py` to customize:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `INVESTMENT_AMOUNT_USD` | 50.0 | Amount to invest per coin per interval |
| `VS_CURRENCY` | "usd" | Target currency for prices |
| `USE_TOP_MARKET_COINS` | True | Use top coins by market cap |
| `REQUIRED_COINS` | ["bitcoin", "ethereum", "cardano"] | Coins to always include |

## Files

- `dca_bot.py` - Main bot script
- `dca.db` - SQLite database (created on first run)
- `dca_report.html` - Generated HTML report (with `--report` flag)

## License

MIT

## Related

- [CoinGecko API Documentation](https://docs.coingecko.com/)
- [Full Tutorial Blog Post](https://github.com/rollendxavier/crypto_dollar_cost)
