# CoinGecko API — Common Use Cases

A jumping-off point for exploratory queries. Load this file when the user asks what
they can build, wants project ideas, or needs inspiration for how to use crypto market
data — rather than asking about a specific endpoint.

Each use case includes a brief description and pointers to the reference file(s) where
the relevant endpoints are documented. Load those files to proceed with implementation.

---

## Price & Market Data

### Live price tracker
Display current prices, market cap, 24hr volume, and price change for one or more coins.
→ `references/coins.md` — `GET /simple/price`, `GET /coins/markets`

### Token price by contract address
Look up prices using a token's contract address instead of a CoinGecko coin ID — useful
when integrating with wallet or DeFi apps that only have the on-chain address.
→ `references/contract.md` — `GET /simple/token_price/{id}`

### Historical price charts
Build time-series charts for price, market cap, or volume over custom date ranges.
→ `references/coin-history.md` — `GET /coins/{id}/market_chart`, `GET /coins/{id}/market_chart/range`

### OHLC candlestick charts
Render candlestick/trading-view style charts for any coin.
→ `references/coin-history.md` — `GET /coins/{id}/ohlc`, `GET /coins/{id}/ohlc/range`

### Stale price detection
Check whether a coin's price data is still fresh or has gone stale.
→ `references/coins.md` — `GET /simple/price` with `include_last_updated_at=true`

---

## Portfolio & Watchlist Tools

### Portfolio dashboard
Combine current prices, sparklines, ATH/ATL, market cap rank, and watchlist counts
into a portfolio view.
→ `references/coins.md` — `GET /coins/{id}`, `GET /coins/markets` (with `sparkline=true`)

### BTC exchange rate converter
Convert BTC-denominated values to fiat or other crypto in real time.
→ `references/utils.md` — `GET /exchange_rates`

---

## Discovery & Trends

### Trending coins & NFTs
Surface the hottest coins, NFTs, and categories based on CoinGecko user searches.
→ `references/utils.md` — `GET /search/trending`

### Top gainers & losers
Show the biggest movers over 1h, 24h, 7d, or longer windows.
→ `references/coins.md` — `GET /coins/top_gainers_losers`

### New coin listing alerts
Build a Telegram bot or alert system for the latest coins added to CoinGecko.
→ `references/coins.md` — `GET /coins/list/new`

### Category / ecosystem rankings
Compare market cap and volume across sectors (Layer 1, DeFi, Memecoins, etc.).
→ `references/categories.md` — `GET /coins/categories`

### Search across coins, exchanges, NFTs, and categories
Resolve names and symbols to IDs, or let users search freely.
→ `references/utils.md` — `GET /search`

---

## Global & Macro

### Bitcoin dominance (BTC.D)
Track Bitcoin's share of total crypto market cap alongside global volume.
→ `references/global.md` — `GET /global`

### DeFi market overview
Get total DeFi market cap, ETH ratio, and the leading DeFi protocol.
→ `references/global.md` — `GET /global/decentralized_finance_defi`

### Global market cap chart
Plot historical total crypto market cap and volume over time.
→ `references/global.md` — `GET /global/market_cap_chart`

### Corporate Bitcoin treasuries
Track public companies' and governments' crypto holdings and transactions.
→ `references/treasury.md` — `GET /companies/public_treasury/{coin_id}`, `GET /public_treasury/{entity_id}`

---

## Exchange Analytics

### Exchange comparison
Rank exchanges by trust score, volume, and trading pairs.
→ `references/exchanges.md` — `GET /exchanges`, `GET /exchanges/{id}`

### Identify DEX vs CEX
Check the `centralized` field to classify any exchange.
→ `references/exchanges.md` — `GET /exchanges/{id}`

### Exchange volume charts
Plot historical trading volume for any exchange (spot or derivatives).
→ `references/exchanges.md` — `GET /exchanges/{id}/volume_chart`

### Derivatives & funding rates
Monitor open interest, funding rates, and perpetual/futures tickers.
→ `references/derivatives.md` — `GET /derivatives`, `GET /derivatives/exchanges/{id}`

---

## NFTs

### NFT floor price & market cap tracker
Track floor prices, volume, and market cap for NFT collections.
→ `references/nfts.md` — `GET /nfts/{id}`, `GET /nfts/markets`

### NFT marketplace comparison
Compare floor prices across marketplaces (OpenSea, Blur, etc.) for a collection.
→ `references/nfts.md` — `GET /nfts/{id}/tickers`

### NFT historical charts
Plot floor price, volume, and market cap over time for a collection.
→ `references/nfts.md` — `GET /nfts/{id}/market_chart`

---

## On-Chain / DEX Analytics (GeckoTerminal)

### On-chain token price lookup
Get real-time prices for any token by contract address — including long-tail tokens
not listed on CoinGecko.
→ `references/onchain-tokens.md` — `GET /onchain/simple/networks/{network}/token_price/{addresses}`

### Trending & new pools
Discover what's hot on-chain right now, or catch newly created pools within 48 hours.
→ `references/onchain-pools.md` — trending pools, new pools endpoints

### Pool-level analytics
Inspect a specific pool's liquidity, volume, buy/sell ratio, and fee tier.
→ `references/onchain-pools.md` — `GET /onchain/networks/{network}/pools/{address}`

### Pool screener (megafilter)
Build a custom screener with filters on FDV, liquidity, volume, pool age, buy/sell
tax, honeypot checks, and more.
→ `references/onchain-pools.md` — `GET /onchain/pools/megafilter`

### On-chain OHLCV charts
Render candlestick charts sourced directly from DEX swap data.
→ `references/onchain-ohlcv-trades.md` — pool and token OHLCV endpoints

### Trade history
Fetch recent individual swap transactions for a pool or token.
→ `references/onchain-ohlcv-trades.md` — pool and token trades endpoints

### Token security & GT Score
Check a token's GeckoTerminal score, honeypot status, holder distribution, and
mint/freeze authority.
→ `references/onchain-tokens.md` — `GET /onchain/networks/{network}/tokens/{address}/info`

### Top holders & traders
Analyze whale concentration and top trader PnL for a token.
→ `references/onchain-tokens.md` — `top_holders`, `top_traders` endpoints

### Launchpad / Pump.fun monitoring
Track the latest bonding-curve token launches by filtering megafilter by DEX and
sorting by creation time.
→ `references/onchain-pools.md` — `GET /onchain/pools/megafilter` with `sort=pool_created_at_desc`

### Inactive token data recovery
Retrieve the last known price and data for tokens with no recent swaps using
`include_inactive_source=true`.
→ `references/onchain-tokens.md` — supported on token data, token price, token OHLCV, and top pools endpoints

---

## Infrastructure & Utilities

### Supported blockchain networks
List all networks (asset platforms) on CoinGecko and GeckoTerminal, and map between
the two ID systems.
→ `references/asset-platforms.md` — `GET /asset_platforms`
→ `references/onchain-networks.md` — `GET /onchain/networks`

### Token lists per chain
Get the full verified token list for a blockchain in the Ethereum token list standard.
→ `references/asset-platforms.md` — `GET /token_lists/{asset_platform_id}/all.json`

### Coin ID resolution
Find the CoinGecko coin ID for any coin by name or symbol.
→ `references/utils.md` — `GET /search`
→ `references/coins.md` — `GET /coins/list`

### API health & usage monitoring
Check server status and monitor your API key's rate limits and remaining credits.
→ `references/utils.md` — `GET /ping`, `GET /key`