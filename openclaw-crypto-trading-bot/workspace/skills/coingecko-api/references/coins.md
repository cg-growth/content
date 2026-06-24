# CoinGecko API — Coins Reference

Covers coin market data, metadata, tickers, and discovery endpoints. Load this file when
the user is asking about coin prices, market cap, volume, coin details, tickers, recently
added coins, or top gainers/losers. For historical charts or OHLC data, see `references/coin-history.md`.
For supply charts, see `references/coin-supply.md`. For contract address lookups, see `references/contract.md`.

---

## `GET /simple/price` — Coin Price by IDs

| Field | Value |
|---|---|
| Description | Query prices of one or more coins by CoinGecko coin ID |
| Path | `GET /simple/price` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `vs_currencies` | string | Yes | Target currency (comma-separated for multiple). Refer to `references/utils.md` → `GET /simple/supported_vs_currencies` |
| `ids` | string | No | Coin IDs (comma-separated). Priority: `ids` > `names` > `symbols` |
| `names` | string | No | Coin names (comma-separated). URL-encode spaces (e.g. `Binance%20Coin`) |
| `symbols` | string | No | Coin symbols (comma-separated) |
| `include_tokens` | string | No | For `symbols` lookup: `top` (default, by market cap/volume) or `all` (all matches, max 50 symbols) |
| `include_market_cap` | boolean | No | Include market cap. Default: `false` |
| `include_24hr_vol` | boolean | No | Include 24hr volume. Default: `false` |
| `include_24hr_change` | boolean | No | Include 24hr price change percentage. Default: `false` |
| `include_last_updated_at` | boolean | No | Include last updated timestamp in UNIX. Default: `false` |
| `precision` | string | No | Decimal places: `full` or `0`–`18` |

### Notes
- At least one of `ids`, `names`, or `symbols` is required.
- To check for stale prices, use `include_last_updated_at=true` or check if `include_24hr_change` returns `null`.

### Example Response
```json
{
  "bitcoin": {
    "usd": 67187.33,
    "usd_market_cap": 1317802988326.25,
    "usd_24h_vol": 31260929299.52,
    "usd_24h_change": 3.637,
    "last_updated_at": 1711356300
  }
}
```

### Response Fields

| Field | Description |
|---|---|
| `{coin_id}.{currency}` | Price in the requested currency |
| `{coin_id}.{currency}_market_cap` | Market cap. Present when `include_market_cap=true` |
| `{coin_id}.{currency}_24h_vol` | 24hr volume. Present when `include_24hr_vol=true` |
| `{coin_id}.{currency}_24h_change` | 24hr price change %. Present when `include_24hr_change=true` |
| `{coin_id}.last_updated_at` | Last updated UNIX timestamp. Present when `include_last_updated_at=true` |

---

## `GET /coins/list` — Coins List (ID Map)

| Field | Value |
|---|---|
| Description | Query all supported coins with ID, name, and symbol |
| Path | `GET /coins/list` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `include_platform` | boolean | No | Include asset platform and contract addresses. Default: `false` |
| `status` | string | No | Filter by coin status: `active` (default) or `inactive` |

### Notes
- No pagination — returns the full list in one response.
- Use this endpoint to resolve coin IDs for use in other endpoints.
- Inactive coin IDs can be used with select historical data endpoints.

### Example Response
```json
[
  {
    "id": "bitcoin",
    "symbol": "btc",
    "name": "Bitcoin",
    "platforms": {
      "ethereum": "0xb9ef770b6a5e12e45983c5d80545258aa38f3b78"
    }
  }
]
```

### Response Fields

| Field | Description |
|---|---|
| `id` | CoinGecko coin ID |
| `symbol` | Coin symbol |
| `name` | Coin name |
| `platforms` | Map of asset platform to contract address. Present when `include_platform=true` |

---

## `GET /coins/markets` — Coins List with Market Data

| Field | Value |
|---|---|
| Description | Query all supported coins with price, market cap, volume, and market data |
| Path | `GET /coins/markets` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `vs_currency` | string | Yes | Target currency. Refer to `references/utils.md` → `GET /simple/supported_vs_currencies` |
| `ids` | string | No | Filter by coin IDs (comma-separated) |
| `names` | string | No | Filter by coin names. URL-encode spaces |
| `symbols` | string | No | Filter by coin symbols (comma-separated) |
| `include_tokens` | string | No | For `symbols` lookup: `top` (default) or `all` (max 50 symbols) |
| `category` | string | No | Filter by category. Refer to `references/categories.md` → `GET /coins/categories/list`. Highest priority when combined with other lookup params |
| `order` | string | No | Sort order: `market_cap_desc` (default), `market_cap_asc`, `volume_desc`, `volume_asc`, `id_asc`, `id_desc` |
| `per_page` | number | No | Results per page: 1–250. Default: `100` |
| `page` | number | No | Page number. Default: `1` |
| `sparkline` | boolean | No | Include 7-day sparkline data. Default: `false` |
| `price_change_percentage` | string | No | Include price change % for timeframes (comma-separated): `1h`, `24h`, `7d`, `14d`, `30d`, `200d`, `1y` |
| `locale` | string | No | Response language. Default: `en` |
| `precision` | string | No | Decimal places: `full` or `0`–`18` |
| `include_rehypothecated` | boolean | No | Include rehypothecated tokens. Default: `false` |

### Notes
- Lookup param priority: `category` > `ids` > `names` > `symbols`.

### Example Response
```json
[
  {
    "id": "bitcoin",
    "symbol": "btc",
    "name": "Bitcoin",
    "current_price": 70187,
    "market_cap": 1381651251183,
    "market_cap_rank": 1,
    "total_volume": 20154184933,
    "high_24h": 70215,
    "low_24h": 68060,
    "price_change_24h": 2126.88,
    "price_change_percentage_24h": 3.125,
    "circulating_supply": 19675987,
    "total_supply": 21000000,
    "max_supply": 21000000,
    "ath": 73738,
    "atl": 67.81,
    "last_updated": "2024-04-07T16:49:31.736Z"
  }
]
```

### Response Fields

| Field | Description |
|---|---|
| `id` | Coin ID |
| `symbol` | Coin symbol |
| `name` | Coin name |
| `image` | Coin image URL |
| `current_price` | Current price in target currency |
| `market_cap` | Market cap in target currency |
| `market_cap_rank` | Rank by market cap |
| `market_cap_rank_with_rehypothecated` | Rank including rehypothecated tokens. Present when `include_rehypothecated=true` |
| `fully_diluted_valuation` | Fully diluted valuation (FDV) |
| `total_volume` | 24hr trading volume |
| `high_24h` | 24hr price high |
| `low_24h` | 24hr price low |
| `price_change_24h` | 24hr price change in currency |
| `price_change_percentage_24h` | 24hr price change % |
| `market_cap_change_24h` | 24hr market cap change |
| `market_cap_change_percentage_24h` | 24hr market cap change % |
| `circulating_supply` | Circulating supply |
| `total_supply` | Total supply |
| `max_supply` | Max supply |
| `ath` | All-time high price |
| `ath_change_percentage` | % change from ATH |
| `ath_date` | ATH date (ISO 8601) |
| `atl` | All-time low price |
| `atl_change_percentage` | % change from ATL |
| `atl_date` | ATL date (ISO 8601) |
| `roi` | Return on investment data (nullable) |
| `last_updated` | Last updated timestamp (ISO 8601) |
| `price_change_percentage_{timeframe}_in_currency` | Price change % for requested timeframe. Present when `price_change_percentage` param is used |
| `sparkline_in_7d` | 7-day sparkline price data. Present when `sparkline=true` |

---

## `GET /coins/{id}` — Coin Data by ID

| Field | Value |
|---|---|
| Description | Query full metadata and market data for a coin by its CoinGecko ID |
| Path | `GET /coins/{id}` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes (path) | CoinGecko coin ID |
| `localization` | boolean | No | Include all localized language names. Default: `true` |
| `tickers` | boolean | No | Include exchange ticker data (limited to 100). Default: `true` |
| `market_data` | boolean | No | Include market data. Default: `true` |
| `community_data` | boolean | No | Include community data. Default: `true` |
| `developer_data` | boolean | No | Include developer/repo data. Default: `true` |
| `sparkline` | boolean | No | Include 7-day sparkline data. Default: `false` |
| `include_categories_details` | boolean | No | Include detailed category objects (id + name). Default: `false` |
| `dex_pair_format` | string | No | DEX pair format: `contract_address` (default) or `symbol` |

### Notes
- Tickers are limited to 100 items. Use `GET /coins/{id}/tickers` for full paginated tickers.
- `market_data` contains prices, ATH, ATL, supply, and more across all supported currencies.
- Coin descriptions may contain `\r\n` newline escape sequences.

### Example Response
```json
{
  "id": "bitcoin",
  "symbol": "btc",
  "name": "Bitcoin",
  "asset_platform_id": null,
  "platforms": { "": "" },
  "categories": ["Layer 1 (L1)"],
  "market_cap_rank": 1,
  "last_updated": "2024-04-08T04:03:00+00:00",
  "market_data": {
    "current_price": { "usd": 69840 },
    "ath": { "usd": 73738 },
    "atl": { "usd": 67.81 },
    "market_cap": { "usd": 1374413833490 },
    "total_volume": { "usd": 20154184933 },
    "circulating_supply": 19675987,
    "total_supply": 21000000,
    "max_supply": 21000000
  }
}
```

### Response Fields

| Field | Description |
|---|---|
| `id` | Coin ID |
| `symbol` | Coin symbol |
| `name` | Coin name |
| `web_slug` | CoinGecko page slug |
| `asset_platform_id` | Asset platform ID (null for native coins) |
| `platforms` | Map of platform to contract address |
| `detail_platforms` | Map of platform to contract address with decimal places |
| `block_time_in_minutes` | Average block time |
| `hashing_algorithm` | Blockchain hashing algorithm |
| `categories` | Coin category names |
| `categories_details` | Detailed category objects with id and name. Present when `include_categories_details=true` |
| `localization` | Coin name in all languages. Present when `localization=true` |
| `description` | Coin description by language |
| `links` | Homepage, whitepaper, block explorers, socials, and repo URLs |
| `image` | Coin image URLs (thumb, small, large) |
| `genesis_date` | Launch date |
| `sentiment_votes_up_percentage` | Bullish sentiment % |
| `sentiment_votes_down_percentage` | Bearish sentiment % |
| `watchlist_portfolio_users` | Number of users tracking this coin |
| `market_cap_rank` | Rank by market cap |
| `market_cap_rank_with_rehypothecated` | Rank including rehypothecated tokens |
| `market_data` | Full market data object (prices, ATH, ATL, supply, volume across all currencies). Present when `market_data=true` |
| `community_data` | Telegram member counts. Present when `community_data=true` |
| `developer_data` | GitHub/Bitbucket repo stats. Present when `developer_data=true` |
| `tickers` | Exchange tickers (max 100). Present when `tickers=true` |
| `last_updated` | Last updated timestamp |

---

## `GET /coins/{id}/tickers` — Coin Tickers by ID

| Field | Value |
|---|---|
| Description | Query CEX and DEX tickers for a coin by ID, paginated |
| Path | `GET /coins/{id}/tickers` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes (path) | CoinGecko coin ID |
| `exchange_ids` | string | No | Filter by specific exchange ID. Refer to `references/exchanges.md` → `GET /exchanges/list` |
| `include_exchange_logo` | boolean | No | Include exchange logo URL. Default: `false` |
| `page` | number | No | Page number (100 tickers per page) |
| `order` | string | No | Sort: `trust_score_desc` (default), `trust_score_asc`, `volume_desc`, `volume_asc`. When sorting by `volume`, `converted_volume` is used |
| `depth` | boolean | No | Include 2% order book depth (`cost_to_move_up_usd`, `cost_to_move_down_usd`). Default: `false` |
| `dex_pair_format` | string | No | DEX pair format: `contract_address` (default) or `symbol` |

### Notes
- Tickers are paginated at 100 per page.

### Example Response
```json
{
  "name": "Bitcoin",
  "tickers": [
    {
      "base": "BTC",
      "target": "USDT",
      "market": {
        "name": "Binance",
        "identifier": "binance",
        "has_trading_incentive": false
      },
      "last": 69476,
      "volume": 20242.03,
      "converted_last": { "usd": 69498 },
      "converted_volume": { "usd": 1406996874 },
      "trust_score": null,
      "bid_ask_spread_percentage": 0.010014,
      "is_anomaly": false,
      "is_stale": false,
      "trade_url": "https://www.binance.com/en/trade/BTC_USDT",
      "timestamp": "2024-04-08T04:02:01+00:00"
    }
  ]
}
```

### Response Fields

| Field | Description |
|---|---|
| `name` | Coin name |
| `tickers[].base` | Base coin of the trading pair |
| `tickers[].target` | Target coin of the trading pair |
| `tickers[].market.name` | Exchange name |
| `tickers[].market.identifier` | Exchange ID |
| `tickers[].market.has_trading_incentive` | Whether the exchange offers trading incentives |
| `tickers[].market.logo` | Exchange logo URL. Present when `include_exchange_logo=true` |
| `tickers[].last` | Last traded price |
| `tickers[].volume` | Trading volume |
| `tickers[].cost_to_move_up_usd` | Cost to move price up 2% in USD. Present when `depth=true` |
| `tickers[].cost_to_move_down_usd` | Cost to move price down 2% in USD. Present when `depth=true` |
| `tickers[].converted_last` | Last price converted to BTC, ETH, USD |
| `tickers[].converted_volume` | Volume converted to BTC, ETH, USD |
| `tickers[].trust_score` | Ticker trust score (nullable) |
| `tickers[].bid_ask_spread_percentage` | Bid-ask spread percentage |
| `tickers[].timestamp` | Ticker timestamp |
| `tickers[].last_traded_at` | Last trade timestamp |
| `tickers[].last_fetch_at` | Last data fetch timestamp |
| `tickers[].is_anomaly` | Whether the ticker is flagged as anomalous |
| `tickers[].is_stale` | Whether the ticker data is stale |
| `tickers[].trade_url` | Direct trade URL on the exchange |
| `tickers[].token_info_url` | Token info URL (DEX only; `null` for CEX) |
| `tickers[].coin_id` | CoinGecko coin ID for the base currency |
| `tickers[].target_coin_id` | CoinGecko coin ID for the target currency |

---

## `GET /coins/top_gainers_losers` — Top Gainers & Losers

| Field | Value |
|---|---|
| Description | Query the top 30 coins with largest price gain and loss by time duration |
| Path | `GET /coins/top_gainers_losers` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `vs_currency` | string | Yes | Target currency. Refer to `references/utils.md` → `GET /simple/supported_vs_currencies` |
| `duration` | string | No | Time range: `1h`, `24h` (default), `7d`, `14d`, `30d`, `60d`, `1y` |
| `price_change_percentage` | string | No | Include additional price change % timeframes (comma-separated): `1h`, `24h`, `7d`, `14d`, `30d`, `200d`, `1y` |
| `top_coins` | string | No | Filter by market cap ranking: `300`, `500`, `1000` (default), or `all` (includes coins without market cap) |

### Notes
- Only includes coins with a 24hr trading volume of at least $50,000.
- Returns exactly 30 coins each for `top_gainers` and `top_losers`.

### Example Response
```json
{
  "top_gainers": [
    {
      "id": "hemi",
      "symbol": "hemi",
      "name": "Hemi",
      "image": "https://coin-images.coingecko.com/...",
      "market_cap_rank": 504,
      "usd": 0.1118,
      "usd_24h_vol": 37605963.65,
      "usd_24h_change": 97.507
    }
  ],
  "top_losers": [
    {
      "id": "alchemist-ai",
      "symbol": "alch",
      "name": "Alchemist AI",
      "usd": 0.0704,
      "usd_24h_vol": 27971580.84,
      "usd_24h_change": -17.226
    }
  ]
}
```

### Response Fields

| Field | Description |
|---|---|
| `top_gainers` | Array of top gaining coins |
| `top_losers` | Array of top losing coins |
| `[].id` | Coin ID |
| `[].symbol` | Coin symbol |
| `[].name` | Coin name |
| `[].image` | Coin image URL |
| `[].market_cap_rank` | Rank by market cap |
| `[].usd` | Current price in USD |
| `[].usd_24h_vol` | 24hr volume in USD |
| `[].usd_24h_change` | 24hr price change % in USD |
| `[].usd_1h_change` | 1hr price change %. Present when `price_change_percentage` includes `1h` |
| `[].usd_7d_change` | 7d price change %. Present when `price_change_percentage` includes `7d` |
| `[].usd_14d_change` | 14d price change %. Present when `price_change_percentage` includes `14d` |
| `[].usd_30d_change` | 30d price change %. Present when `price_change_percentage` includes `30d` |
| `[].usd_200d_change` | 200d price change %. Present when `price_change_percentage` includes `200d` |
| `[].usd_1y_change` | 1yr price change %. Present when `price_change_percentage` includes `1y` |

---

## `GET /coins/list/new` — Recently Added Coins

| Field | Value |
|---|---|
| Description | Query the latest coins recently listed on CoinGecko |
| Path | `GET /coins/list/new` |

### Parameters

No parameters.

### Example Response
```json
[
  {
    "id": "long-johnson",
    "symbol": "olong",
    "name": "Long Johnson",
    "activated_at": 1712562430
  }
]
```

### Response Fields

| Field | Description |
|---|---|
| `id` | Coin ID |
| `symbol` | Coin symbol |
| `name` | Coin name |
| `activated_at` | UNIX timestamp when the coin was listed on CoinGecko |