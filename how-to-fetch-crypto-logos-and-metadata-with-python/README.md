> Read the full article: [How to Fetch Crypto Logos and Metadata with Python](https://www.coingecko.com/learn/how-to-fetch-crypto-logos-and-metadata-with-python)

# Fetch Crypto Logos and Metadata with Python (CoinGecko API)

Python companion repo for building logo-complete crypto UIs:
- market-cap watchlist/feed logos (`/coins/markets`)
- rich coin profile metadata (`/coins/{id}`)
- token-by-contract metadata (`/coins/{platform}/contract/{address}`)
- bulk on-chain discovery from GeckoTerminal paths

## Requirements

- Python 3.10+
- CoinGecko Demo or Pro API key

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill `.env` with your key and mode:

```env
CG_API_MODE=demo
COINGECKO_DEMO_API_KEY=...
COINGECKO_PRO_API_KEY=
```

Scripts auto-load `.env` from repo root.

## Quick Start

### 1) Dynamic Top-N Watchlist Logos (Default Feed Demo)

```bash
python scripts/03_get_bulk_logos_markets.py --top-n 20
open output/charts/watchlist_demo.html
```

Outputs:
- `output/json/bulk_logos_map.json`
- `output/csv/bulk_logos_markets.csv`
- `output/charts/watchlist_demo.html`

### 2) Rich Metadata for One Coin

```bash
python scripts/02_get_coin_metadata.py --coin-id bitcoin
```

Output:
- `output/json/coin_metadata_bitcoin.json`

### 3) Metadata by Contract Address

```bash
python scripts/04_get_token_metadata_by_contract.py \
  --platform ethereum \
  --contract-address 0x514910771af9ca656af840dff83e8264ecf986ca
```

Output:
- `output/json/contract_metadata_ethereum_0x51491077.json`

## On-Chain Bulk Discovery (GeckoTerminal)

### Trending pools -> included tokens (recommended default)

```bash
python scripts/06_get_onchain_tokens_multi.py --mode trending-pools --network eth --limit 20
```

### Other discovery modes

```bash
python scripts/06_get_onchain_tokens_multi.py --mode top-pools --network eth --limit 20
python scripts/06_get_onchain_tokens_multi.py --mode new-pools --network eth --limit 20
python scripts/06_get_onchain_tokens_multi.py --mode recently-updated --network eth --limit 20
```

### Explicit address mode

```bash
python scripts/06_get_onchain_tokens_multi.py \
  --mode addresses \
  --network eth \
  --addresses 0x514910771af9ca656af840dff83e8264ecf986ca
```

Outputs:
- `output/json/onchain_tokens_<network>_<mode>.json`
- `output/csv/onchain_tokens_<network>_<mode>.csv`

## Other Scripts

```bash
python scripts/01_build_coin_lookup.py --symbol btc
python scripts/05_download_logos.py --from-json output/json/coin_metadata_bitcoin.json --image-field small_url
python scripts/07_get_trending_logos.py
python scripts/07_get_trending_logos.py --show-max
python scripts/smoke_test.py
```

## Notes

- Use `--coin-ids ...` in script 03 only when you intentionally want a fixed custom watchlist.
- For live feed demos on Demo plan, add delay between repeated runs to reduce 429 risk.
- `CG_DEBUG=true` and `CG_SAVE_RAW=true` can be enabled in `.env` when debugging API payloads.
