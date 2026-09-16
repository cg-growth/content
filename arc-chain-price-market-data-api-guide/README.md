# How to Get Arc Chain Token Prices and Market Data With an API

Companion script for the CoinGecko Learn article. Looks up a token on Arc Chain
by contract address across CoinGecko's curated database and GeckoTerminal's
onchain indexing, then fetches price, market cap, historical data, and pool
liquidity.

## Setup

```bash
pip install -r requirements.txt
export COINGECKO_DEMO_API_KEY=your-demo-key-here
python3 token_lookup.py
```

Tested live against Arc Chain on 2026-09-17 — Circle Wrapped BTC (cirBTC) is
listed on CoinGecko's curated database, price ~$75.6k, with active liquidity
pools against USDC.
