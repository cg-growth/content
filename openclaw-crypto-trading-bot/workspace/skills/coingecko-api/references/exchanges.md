# CoinGecko API — Exchanges Reference

Covers exchange discovery, exchange data, tickers, and volume charts. Load this file
when the user asks about exchanges, trading pairs, tickers, exchange volume, or needs
to resolve an exchange ID.

Exchange IDs are also required by `references/derivatives.md` volume chart endpoints.

Note: For derivatives exchanges (e.g. `bitmex`, `binance_futures`), exchange data and
ticker endpoints are in `references/derivatives.md`. However, exchange IDs for
derivatives exchanges are resolved here via `GET /exchanges/list`, and volume chart
endpoints in this file also accept derivatives exchange IDs.

---

## `GET /exchanges/list` — Exchanges List (ID Map)

| Field | Value |
|---|---|
| Description | Query all exchange IDs and names, including derivatives exchanges |
| Path | `GET /exchanges/list` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `status` | string | No | Filter by exchange status. Default: `active`. Options: `active`, `inactive` |

### Notes
- Covers both spot and derivatives exchanges. Use `id` values from this endpoint across all exchange and derivatives exchange endpoints.
- No pagination required.

### Example Response
```json
[
  { "id": "binance", "name": "Binance" },
  { "id": "binance_futures", "name": "Binance Futures" }
]
```

### Response Fields

| Field | Description |
|---|---|
| `id` | Exchange ID — use in all exchange and derivatives exchange endpoints |
| `name` | Exchange name |

---

## `GET /exchanges` — Exchanges List with Data

| Field | Value |
|---|---|
| Description | Query all active exchanges with metadata and 24hr BTC volume |
| Path | `GET /exchanges` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `per_page` | number | No | Results per page. Default: `100`. Max: `250` |
| `page` | number | No | Page number. Default: `1` |

### Notes
- Only exchanges with active trading volume are included.
- Volume is denominated in BTC (see `references/core.md` → BTC-denominated values).

### Example Response
```json
[
  {
    "id": "bybit_spot",
    "name": "Bybit",
    "year_established": 2018,
    "country": "British Virgin Islands",
    "description": "...",
    "url": "https://www.bybit.com",
    "image": "https://assets.coingecko.com/markets/images/698/small/bybit_spot.png",
    "has_trading_incentive": false,
    "trust_score": 10,
    "trust_score_rank": 1,
    "trade_volume_24h_btc": 51075.63
  }
]
```

### Response Fields

| Field | Description |
|---|---|
| `id` | Exchange ID |
| `name` | Exchange name |
| `year_established` | Year the exchange was established |
| `country` | Country of incorporation |
| `description` | Exchange description |
| `url` | Exchange website URL |
| `image` | Exchange logo URL |
| `has_trading_incentive` | Whether the exchange offers trading incentives |
| `trust_score` | CoinGecko trust score |
| `trust_score_rank` | Trust score rank across all exchanges |
| `trade_volume_24h_btc` | 24hr trading volume in BTC |

---

## `GET /exchanges/{id}` — Exchange Data by ID

| Field | Value |
|---|---|
| Description | Query a single exchange's metadata, 24hr BTC volume, and top 100 tickers |
| Path | `GET /exchanges/{id}` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes (path) | Exchange ID. Refer to `GET /exchanges/list` above |
| `dex_pair_format` | string | No | DEX pair display format. Default: `contract_address`. Use `symbol` to show symbols instead |

### Notes
- Tickers are capped at 100. For more tickers, use `GET /exchanges/{id}/tickers` below.
- For derivatives exchanges, use `references/derivatives.md` → `GET /derivatives/exchanges/{id}` instead.
- Volume is denominated in BTC (see `references/core.md` → BTC-denominated values).

### Example Response
```json
{
  "name": "Binance",
  "year_established": 2017,
  "country": "Cayman Islands",
  "url": "https://www.binance.com/",
  "image": "https://assets.coingecko.com/markets/images/52/small/binance.jpg",
  "centralized": true,
  "trust_score": 9,
  "trust_score_rank": 6,
  "trade_volume_24h_btc": 207319.13,
  "coins": 384,
  "pairs": 1281,
  "tickers": [...]
}
```

### Response Fields

| Field | Description |
|---|---|
| `name` | Exchange name |
| `year_established` | Year established |
| `country` | Country of incorporation |
| `description` | Exchange description |
| `url` | Website URL |
| `image` | Logo URL |
| `facebook_url`, `reddit_url`, `telegram_url`, `slack_url`, `other_url_1`, `other_url_2` | Social and other URLs |
| `twitter_handle` | Twitter/X handle |
| `has_trading_incentive` | Whether trading incentives are offered |
| `centralized` | `true` for CEX, `false` for DEX |
| `public_notice` | Public notice text |
| `alert_notice` | Alert notice text |
| `trust_score` | CoinGecko trust score |
| `trust_score_rank` | Trust score rank |
| `trade_volume_24h_btc` | 24hr trading volume in BTC |
| `coins` | Number of coins listed |
| `pairs` | Number of trading pairs |
| `tickers` | Top 100 tickers. See ticker fields below |

---

## `GET /exchanges/{id}/tickers` — Exchange Tickers by ID

| Field | Value |
|---|---|
| Description | Query all tickers for an exchange, paginated at 100 per page |
| Path | `GET /exchanges/{id}/tickers` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes (path) | Exchange ID. Refer to `GET /exchanges/list` above |
| `coin_ids` | string | No | Filter by CoinGecko coin IDs, comma-separated |
| `include_exchange_logo` | boolean | No | Include exchange logo URL. Default: `false` |
| `page` | number | No | Page number for pagination |
| `depth` | boolean | No | Include 2% order book depth (`cost_to_move_up_usd`, `cost_to_move_down_usd`). Default: `false` |
| `order` | string | No | Sort order. Default: `trust_score_desc`. Options: `trust_score_desc`, `trust_score_asc`, `volume_desc`, `volume_asc`, `market_cap_asc`, `market_cap_desc`, `base_target` |
| `dex_pair_format` | string | No | DEX pair display format. Default: `contract_address`. Use `symbol` for readable symbols |

### Notes
- Results are paginated at 100 tickers per page.
- Use `order=base_target` for stable pagination — sorts by base then target symbol lexicographically.

### Example Response
```json
{
  "name": "Binance",
  "tickers": [
    {
      "base": "BTC",
      "target": "USDT",
      "market": {
        "name": "Binance",
        "identifier": "binance",
        "has_trading_incentive": false,
        "logo": "https://assets.coingecko.com/markets/images/52/small/binance.jpg"
      },
      "last": 69476,
      "volume": 20242.04,
      "cost_to_move_up_usd": 19320706.40,
      "cost_to_move_down_usd": 16360235.37,
      "converted_last": { "btc": 1.000205, "eth": 20.29, "usd": 69498 },
      "converted_volume": { "btc": 20249, "eth": 410802, "usd": 1406996874 },
      "trust_score": null,
      "bid_ask_spread_percentage": 0.010014,
      "timestamp": "2024-04-08T04:02:01+00:00",
      "last_traded_at": "2024-04-08T04:02:01+00:00",
      "last_fetch_at": "2024-04-08T04:03:00+00:00",
      "is_anomaly": false,
      "is_stale": false,
      "trade_url": "https://www.binance.com/en/trade/BTC_USDT",
      "token_info_url": null,
      "coin_id": "bitcoin",
      "target_coin_id": "tether",
      "coin_mcap_usd": 230926944910.51
    }
  ]
}
```

### Response Fields

| Field | Description |
|---|---|
| `name` | Exchange name |
| `tickers[].base` | Base currency symbol or contract address (DEX) |
| `tickers[].target` | Target currency symbol or contract address (DEX) |
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
| `tickers[].coin_mcap_usd` | Market cap of the base coin in USD |

---

## Volume Chart Endpoints

Both volume chart endpoints return the same response format and accept derivatives
exchange IDs (e.g. `binance_futures`). Volume is denominated in BTC (see
`references/core.md` → BTC-denominated values).

### Volume Chart Response Format

```json
[
  [1711792200000, "306800.05"],
  [1711795800000, "302561.82"]
]
```

| Index | Description |
|---|---|
| `[0]` | UNIX timestamp in milliseconds |
| `[1]` | Trading volume in BTC (string) |

---

## `GET /exchanges/{id}/volume_chart` — Exchange Volume Chart by ID

| Field | Value |
|---|---|
| Description | Query historical trading volume time-series in BTC for an exchange |
| Path | `GET /exchanges/{id}/volume_chart` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes (path) | Exchange ID or derivatives exchange ID |
| `days` | string | Yes | Number of days ago: `1`, `7`, `14`, `30`, `90`, `180`, or `365` |

### Notes
- Granularity is automatic: 1 day → 10-minutely, 7/14 days → hourly, 30 days and above → daily.

---

## `GET /exchanges/{id}/volume_chart/range` — Exchange Volume Chart within Time Range by ID

| Field | Value |
|---|---|
| Description | Query historical trading volume in BTC for an exchange within a specific date range |
| Path | `GET /exchanges/{id}/volume_chart/range` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes (path) | Exchange ID or derivatives exchange ID |
| `from` | number | Yes | Start date as UNIX timestamp |
| `to` | number | Yes | End date as UNIX timestamp |

### Notes
- Date range between `from` and `to` must be within **31 days**.
- Data interval is fixed at **daily**.