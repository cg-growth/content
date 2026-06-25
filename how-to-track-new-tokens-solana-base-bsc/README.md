# How to Track New Tokens on Solana, Base, BSC, and 250+ Chains

Companion code for the CoinGecko API Learn article:
[How to Track New Tokens on Solana, Base, BSC, and 250+ Chains](https://www.coingecko.com/learn/) (link TBD).

Demonstrates fetching newly created tokens / liquidity pools across 250+ chains via the CoinGecko API onchain endpoints, applying quality filters via Pools Megafilter, and building a polling-based alert loop.

## Files

| File | Purpose |
|---|---|
| `requirements.txt` | Python dependencies (`requests`, `python-dotenv`) |
| `.env.example` | Template env vars (copy to `.env` and add your CoinGecko API key) |
| `cg_client.py` | Shared HTTP client + authentication + sideload indexer |
| `list_networks.py` | List the first 5 supported networks (sanity check) |
| `fetch_new_pools.py` | Fetch newest pools across one or all chains |
| `megafilter.py` | Server-side quality filtering via Pools Megafilter (Analyst+ plan) |
| `alert_loop.py` | Polling-based alert pipeline with dedupe state |

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env to add your CoinGecko API key
```

Get a free Demo API key: https://support.coingecko.com/hc/en-us/articles/21880397454233

## Run

```bash
python list_networks.py             # sanity check
python fetch_new_pools.py           # cross-chain feed
python fetch_new_pools.py solana    # solana-only
python megafilter.py                # quality-filtered (Analyst+ plan)
python alert_loop.py                # polling-based alert loop
```

## Endpoints used

- [`/onchain/networks/new_pools`](https://docs.coingecko.com/reference/latest-pools-list) — Latest pools across all networks
- [`/onchain/networks/{network}/new_pools`](https://docs.coingecko.com/reference/latest-pools-network) — Latest pools for one chain
- [`/onchain/pools/megafilter`](https://docs.coingecko.com/reference/pools-megafilter) — Server-side filtering (Analyst+ plan)

## Public gist (for article embed)

The same code is mirrored to a public gist to power the article's `<script>` embeds with line numbers and syntax highlighting.
