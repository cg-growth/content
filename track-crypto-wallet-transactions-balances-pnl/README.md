> Read the full article: [How to Track Crypto Wallet Transactions, Balances, & Profit & Loss](https://www.coingecko.com/learn/track-crypto-wallet-transactions-balances-pnl)

# CoinGecko Wallet Balances, Trades, Transfers & PnL Toolkit

A Python starter client for fetching a crypto wallet's token balances, trade history, token transfers, and realized/unrealized PnL across multiple networks using CoinGecko's Onchain Wallet endpoints, then merging trades and transfers into a single chronological activity feed.

## What You Can Do

- Fetch a wallet's token balances across multiple networks in one call, valued in USD
- Fetch a wallet's trade history (buy/sell) on a single network, with USD pricing on both sides of the swap
- Fetch a wallet's token transfers (deposits, sends, airdrops) on a single network
- Merge trades and transfers into one chronological, labeled activity feed
- Fetch a wallet's realized and unrealized PnL across multiple networks, with a per-network breakdown

## Quick Start

```bash
git clone https://github.com/cg-growth/content.git
cd content/track-crypto-wallet-transactions-balances-pnl
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp example.env .env
```

Set your API key in `.env`:

```ini
COINGECKO_PRO_API_KEY=CG-your_api_key_here
```

## Scripts

```bash
python wallet_client.py     # Shared API client: get_balances, get_trades, get_transfers, get_pnl
python activity_feed.py     # Prints portfolio value, merged trade/transfer feed, and PnL summary
```

Every REST endpoint can also be called with CoinGecko's official [Python SDK](https://docs.coingecko.com/docs/sdk-python) (`pip install coingecko-sdk`) instead of raw `requests` calls — see the commented `SDK equivalent:` line in `wallet_client.py`.
