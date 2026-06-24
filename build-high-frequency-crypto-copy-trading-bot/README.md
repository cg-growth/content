> Read the full article: [How to Build a High-Frequency Crypto Copy Trading Bot](https://www.coingecko.com/learn/build-high-frequency-crypto-copy-trading-bot)

# High-Frequency Crypto Copy Trading Bot

A Python bot that identifies profitable on-chain wallets and copies their trades in real time, with a lightweight Node.js dashboard for monitoring.

## What's inside

| File | Purpose |
|------|---------|
| `copy_trading_bot.py` | Core bot — scouts tokens via CoinGecko Megafilter/Trending, scores wallet profitability, copies trades via WebSocket |
| `server.js` | Express server that serves the monitoring dashboard |
| `public/app.jsx` | React dashboard for viewing bot activity |

## How it works

1. Uses CoinGecko's on-chain API to find trending pools and high-volume tokens
2. Analyzes wallet trade history to score profitability using Blockscout
3. Monitors profitable wallets via WebSocket for real-time trade detection
4. Copies trades automatically when a target wallet executes a swap

Supports both CoinGecko Pro and Demo API keys — Pro unlocks advanced on-chain filtering endpoints.

## Requirements

- Python 3.8+
- Node.js 18+
- CoinGecko API key ([get one here](https://www.coingecko.com/en/api))

## Getting started

**Python bot:**

```bash
pip install requests pandas python-dotenv
cp .env.example .env   # add your CG_PRO_API_KEY or CG_DEMO_API_KEY
python copy_trading_bot.py
```

**Dashboard:**

```bash
npm install
npm start
# open http://localhost:3000
```

> This project is for educational purposes only and is not financial advice.
