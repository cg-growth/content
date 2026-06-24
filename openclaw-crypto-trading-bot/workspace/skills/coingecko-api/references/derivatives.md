# CoinGecko API — Derivatives Reference

Covers derivatives tickers, derivatives exchange discovery, and derivatives exchange
data. Load this file when the user asks about futures, perpetuals, derivatives
exchanges, open interest, funding rates, or derivatives tickers.

Derivatives exchange IDs (e.g. `binance_futures`, `bybit`) are best resolved via
`GET /derivatives/exchanges/list` in this file — it returns only derivatives exchanges.
`GET /exchanges/list` in `references/exchanges.md` also includes derivatives exchange IDs.

For BTC-denominated volume conversion, see `references/core.md` → BTC-denominated values.

---

## `GET /derivatives` — Derivatives Tickers List

| Field | Value |
|---|---|
| Description | Query all derivative tickers across all derivatives exchanges |
| Path | `GET /derivatives` |

### Parameters

None.

### Notes
- `open_interest` and `volume_24h` are denominated in USD.

### Example Response
```json
[
  {
    "market": "Deepcoin (Derivatives)",
    "symbol": "ETHUSDT",
    "index_id": "ETH",
    "price": "3395.91",
    "price_percentage_change_24h": 1.527,
    "contract_type": "perpetual",
    "index": 3393.53,
    "basis": -0.052,
    "spread": 0.01,
    "funding_rate": -0.007182,
    "open_interest": 9327998764.66,
    "volume_24h": 392642535.23,
    "last_traded_at": 1712467658,
    "expired_at": null
  }
]
```

### Response Fields

| Field | Description |
|---|---|
| `market` | Derivatives exchange name |
| `symbol` | Ticker symbol |
| `index_id` | Underlying asset symbol |
| `price` | Last price (string) |
| `price_percentage_change_24h` | 24hr price change percentage |
| `contract_type` | Contract type (e.g. `perpetual`, `futures`) |
| `index` | Underlying index price |
| `basis` | Difference between derivative price and index price |
| `spread` | Bid-ask spread |
| `funding_rate` | Current funding rate |
| `open_interest` | Open interest in USD |
| `volume_24h` | 24hr volume in USD |
| `last_traded_at` | Last trade UNIX timestamp |
| `expired_at` | Expiry timestamp for futures; `null` for perpetuals |

---

## `GET /derivatives/exchanges/list` — Derivatives Exchanges List (ID Map)

| Field | Value |
|---|---|
| Description | Query all derivatives exchange IDs and names |
| Path | `GET /derivatives/exchanges/list` |

### Parameters

None.

### Example Response
```json
[
  { "id": "binance_futures", "name": "Binance (Futures)" },
  { "id": "bybit", "name": "Bybit (Futures)" }
]
```

### Response Fields

| Field | Description |
|---|---|
| `id` | Derivatives exchange ID |
| `name` | Derivatives exchange name |

---

## `GET /derivatives/exchanges` — Derivatives Exchanges List with Data

| Field | Value |
|---|---|
| Description | Query all derivatives exchanges with metadata and market stats |
| Path | `GET /derivatives/exchanges` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `order` | string | No | Sort order. Default: `open_interest_btc_desc`. Options: `name_asc`, `name_desc`, `open_interest_btc_asc`, `open_interest_btc_desc`, `trade_volume_24h_btc_asc`, `trade_volume_24h_btc_desc` |
| `per_page` | number | No | Results per page |
| `page` | number | No | Page number. Default: `1` |

### Example Response
```json
[
  {
    "name": "Binance (Futures)",
    "id": "binance_futures",
    "open_interest_btc": 279958.61,
    "trade_volume_24h_btc": "574366.94",
    "number_of_perpetual_pairs": 330,
    "number_of_futures_pairs": 44,
    "image": "https://assets.coingecko.com/markets/images/466/small/binance_futures.jpg",
    "year_established": 2019,
    "country": null,
    "description": "",
    "url": "https://www.binance.com/"
  }
]
```

### Response Fields

| Field | Description |
|---|---|
| `id` | Derivatives exchange ID |
| `name` | Exchange name |
| `open_interest_btc` | Total open interest in BTC |
| `trade_volume_24h_btc` | 24hr trading volume in BTC (string) |
| `number_of_perpetual_pairs` | Number of perpetual contract pairs |
| `number_of_futures_pairs` | Number of futures contract pairs |
| `image` | Exchange logo URL |
| `year_established` | Year established (nullable) |
| `country` | Country of incorporation (nullable) |
| `description` | Exchange description |
| `url` | Exchange website URL |

---

## `GET /derivatives/exchanges/{id}` — Derivatives Exchange Data by ID

| Field | Value |
|---|---|
| Description | Query a single derivatives exchange's metadata, market stats, and optionally its tickers |
| Path | `GET /derivatives/exchanges/{id}` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes (path) | Derivatives exchange ID. Refer to `GET /derivatives/exchanges/list` above |
| `include_tickers` | string | No | Include tickers in response. Options: `all` (all tickers), `unexpired` (active tickers only). Omit to exclude tickers |

### Example Response
```json
{
  "name": "Binance (Futures)",
  "open_interest_btc": 350139.89,
  "trade_volume_24h_btc": 689202.84,
  "number_of_perpetual_pairs": 587,
  "number_of_futures_pairs": 38,
  "image": "https://coin-images.coingecko.com/markets/images/466/small/binance_futures.jpg",
  "year_established": 2019,
  "country": null,
  "description": "",
  "url": "https://www.binance.com/",
  "tickers": [
    {
      "symbol": "ASTERUSDT",
      "base": "ASTER",
      "target": "USDT",
      "coin_id": "aster-2",
      "target_coin_id": "tether",
      "trade_url": "https://www.binance.com/en/futures/ASTERUSDT",
      "contract_type": "perpetual",
      "last": 1.873,
      "h24_percentage_change": -5.246,
      "index": 1.872,
      "index_basis_percentage": -0.035,
      "bid_ask_spread": 0.000153,
      "funding_rate": 0.009,
      "open_interest_usd": 212983050.43,
      "h24_volume": 664881040,
      "converted_volume": { "btc": "10920.64", "eth": "296686.50", "usd": "1245690448.46" },
      "converted_last": { "btc": "0.0000164", "eth": "0.000446", "usd": "1.873" },
      "last_traded": 1759214622,
      "expired_at": null
    }
  ]
}
```

### Response Fields

| Field | Description |
|---|---|
| `name` | Exchange name |
| `open_interest_btc` | Total open interest in BTC |
| `trade_volume_24h_btc` | 24hr trading volume in BTC |
| `number_of_perpetual_pairs` | Number of perpetual contract pairs |
| `number_of_futures_pairs` | Number of futures contract pairs |
| `image` | Exchange logo URL |
| `year_established` | Year established (nullable) |
| `country` | Country of incorporation (nullable) |
| `description` | Exchange description |
| `url` | Exchange website URL |
| `tickers` | Ticker list. Present when `include_tickers=all` or `include_tickers=unexpired` |
| `tickers[].symbol` | Ticker symbol |
| `tickers[].base` | Base asset symbol |
| `tickers[].target` | Target/quote asset symbol |
| `tickers[].coin_id` | CoinGecko coin ID for the base asset |
| `tickers[].target_coin_id` | CoinGecko coin ID for the target asset |
| `tickers[].trade_url` | Direct trade URL |
| `tickers[].contract_type` | Contract type (`perpetual` or `futures`) |
| `tickers[].last` | Last traded price |
| `tickers[].h24_percentage_change` | 24hr price change percentage |
| `tickers[].index` | Underlying index price |
| `tickers[].index_basis_percentage` | Basis: difference between last price and index as a percentage |
| `tickers[].bid_ask_spread` | Bid-ask spread |
| `tickers[].funding_rate` | Current funding rate |
| `tickers[].open_interest_usd` | Open interest in USD |
| `tickers[].h24_volume` | 24hr volume (native units) |
| `tickers[].converted_volume` | 24hr volume in BTC, ETH, and USD (strings) |
| `tickers[].converted_last` | Last price in BTC, ETH, and USD (strings) |
| `tickers[].last_traded` | Last trade UNIX timestamp |
| `tickers[].expired_at` | Expiry timestamp; `null` for perpetuals |