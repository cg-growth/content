# Anthropic Pre-IPO Data API Guide

Companion code for the CoinGecko Learn article [How to Get Anthropic Pre-IPO Data With the CoinGecko API](https://www.coingecko.com/learn/anthropic-pre-ipo-data-api-guide).

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export COINGECKO_PRO_API_KEY=your_pro_api_key_here
python3 anthropic_pre_ipo_data.py
```

Requires a CoinGecko API **Pro key with Analyst-tier access** — `top_holders`, `top_traders`, and `holders_chart` are Analyst Plan and above; everything else in this script needs Basic Plan and above.

## Files

- **`anthropic_pre_ipo_data.py`** — the full workflow from the article: resolves the Anthropic RWA ID, pulls its tokenized market snapshot and issuer profile, live tickers, 30-day price history, and top holder/trader activity.
- **`test_websocket_stream.py`** — streams live price updates for Anthropic's tokenized PreStocks token via CoinGecko's WebSocket (`OnchainSimpleTokenPrice` channel). Run with `python3 test_websocket_stream.py`, stop with `Ctrl+C`.

## Official SDK

Every CoinGecko call in `anthropic_pre_ipo_data.py` has its [official Python SDK](https://docs.coingecko.com/docs/sdk-python) equivalent noted in a comment directly below the REST call it replaces.
