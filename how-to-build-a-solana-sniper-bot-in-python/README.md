> Read the full article: [How to Build a Solana Sniper Bot in Python](https://www.coingecko.com/learn/how-to-build-a-solana-sniper-bot-in-python)

# Solana Sniper Bot

A paper trading bot for Solana tokens that monitors pools and executes trades based on price targets and stop losses.

## ⚠️ Important

**This is paper trading only** - no real funds are traded. All orders and trades are stored locally for simulation purposes.

## Setup

### Prerequisites
- Python 3.11+
- CoinGecko Pro API key

### Installation

1. Clone/download the project
2. Create virtual environment:
   ```bash
   python -m venv env
   env\Scripts\activate  # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create `.env` file in project root:
   ```
   CG_API_KEY=your_api_key_here
   ```

## Usage

Run the bot:
```bash
python main.py
```

The bot will:
1. Scan for new Solana pools
2. Filter pools based on criteria (age, liquidity, volume)
3. Buy filtered pools (paper trading)
4. Monitor prices via WebSocket
5. Execute sells when TP/SL conditions are met

## Configuration

Edit parameters in `main.py` -> `do_buy()`:
- `min_pool_age_minutes`: Minimum pool age
- `max_pool_age_minutes`: Maximum pool age
- `min_liquidity_usd`: Minimum USD liquidity
- `amount_usdc`: Trade size per order
- `tp`: Take profit percentage
- `sl`: Stop loss percentage

## Project Structure

```
├── main.py                 # Main bot logic
├── services/
│   ├── coingecko.py       # CoinGecko API client
│   └── trade_service.py   # Trading logic
├── models/                 # Data models
│   ├── order.py
│   ├── trade.py
│   └── pool.py
├── data/                   # Local data storage
│   ├── orders.json
│   └── trades.json
└── utils/
    └── load_env.py        # Environment variables
```

## Missing/TODO

- [ ] Config file for parameters (currently hardcoded in main.py)
- [ ] Database instead of JSON files
- [ ] Real trading integration
- [ ] Logging to file
- [ ] Web dashboard
- [ ] Multiple token support per pool

## Data

Orders and trades are stored in `data/` as JSON files for inspection.
