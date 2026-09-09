> Read the full article: [RWA Data API Guide: How to Find, Compare & Analyze Real-World Assets](https://www.coingecko.com/learn/tokenized-rwa-data-api-guide)

# CoinGecko RWA Data API Guide

A Python starter toolkit for discovering, verifying, and comparing tokenized real-world assets (stocks, ETFs, commodities, and pre-IPO shares) using CoinGecko's RWA API.

## What You Can Do

- Discover every tokenized RWA CoinGecko tracks, with live price, market cap, and volume
- Find tokenized pre-IPO stocks (OpenAI, SpaceX, Anthropic, and more) across every issuing platform
- Trace a token to its issuer and see everything else that issuer has tokenized
- Compare liquidity for an RWA across CEX and DEX venues
- Check whether a tokenized commodity trades at a premium or discount to its real-world spot price
- Pull historical price, market cap, and volume for an RWA
- Build a repeatable watchlist across multiple tokenized assets

## Quick Start

```bash
git clone https://github.com/cg-growth/content.git
cd content/tokenized-rwa-data-api-guide
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Set your API key in `.env`:

```ini
COINGECKO_API_KEY=CG-your_api_key_here
```

By default, `config.py` targets the free Demo API. Uncomment the Pro base URL line in `config.py` (and swap the header) once you're on a paid plan — `compare_liquidity.py` and `rwa_market_history.py` require Basic or above.

## Scripts

```bash
python find_rwas.py            # List every tracked RWA; screen a sample by ID
python find_pre_ipo.py         # Find tokenized pre-IPO stocks + aggregate view
python analyze_rwa.py          # Trace a token to its issuer's full portfolio
python compare_liquidity.py    # Compare CEX/DEX liquidity for an RWA (Basic+)
python premium_discount.py     # Tokenized commodity premium/discount vs spot
python rwa_market_history.py   # Historical price/market cap/volume (Basic+)
python build_watchlist.py      # Multi-asset watchlist snapshot
```

## Endpoints Used

- `GET /rwas/list`
- `GET /rwas/markets`
- `GET /rwas/{id}`
- `GET /rwas/issuers/{id}`
- `GET /rwas/{id}/tickers` (Basic+)
- `GET /rwas/{id}/market_chart` (Basic+)
- `GET /coins/markets` (category: `tokenized-pre-ipo-stocks`)
- `GET /exchange_rates`
