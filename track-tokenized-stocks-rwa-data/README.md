> Read the full article: [How to Track Tokenized Stocks & Real World Assets (RWAs) Across Solana, Ethereum, Robinhood & 200+ Chains](https://www.coingecko.com/learn/track-tokenized-stocks-rwa-data)

# CoinGecko Tokenized Stocks & RWA Python Toolkit

A Python starter toolkit for discovering, pricing, and monitoring tokenized stocks (xStocks, Ondo, bStocks, Robinhood chain stocks) across Solana, Ethereum, and 200+ other chains using the CoinGecko API and GeckoTerminal onchain endpoints.

## What You Can Do

- Discover tokenized stock categories and resolve each token's cross-chain contract addresses
- Fetch aggregated price, market cap, and volume with `/simple/price`
- Map onchain liquidity across every chain a tokenized stock trades on
- Snapshot and rank token holders, and pull recent onchain trades
- Retrieve historical price and OHLCV candle data
- Stream real-time price, OHLCV, and trade updates via CoinGecko's WebSocket

## Quick Start

```bash
git clone https://github.com/cg-growth/content.git
cd content/track-tokenized-stocks-rwa-data
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp example.env .env
```

Set your API key in `.env`:

```ini
COINGECKO_API_KEY=CG-your_api_key_here
COINGECKO_PLAN=demo
```

## Scripts

```bash
python discover_tokens.py      # Find tokenized stock categories + contract addresses
python track_price.py          # Aggregated price, market cap, 24h volume
python track_liquidity.py       # Onchain liquidity pools across every chain
python holders_snapshot.py     # Holder count + concentration snapshot
python holders_ranked.py       # Top holders, holder growth chart, recent trades (Analyst+)
python historical_price.py     # Historical price via /coins/{id}/market_chart
python historical_ohlcv.py     # Pool OHLCV candles for charting
python stream_data.py          # Real-time price/OHLCV/trade stream via WebSocket (Analyst+)
```

Every REST endpoint can also be called with CoinGecko's official [Python SDK](https://docs.coingecko.com/docs/sdk-python) (`pip install coingecko-sdk`) instead of raw `requests` calls — see the commented `SDK equivalent:` line above each function.
