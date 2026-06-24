# CoinGecko API — Coin Historical Data Reference

Covers historical price, market cap, volume, and OHLC data by coin ID. Load this file
when the user is asking about historical charts, time-series prices, OHLC candlesticks,
or data over a specific date range. For current market data, see `references/coins.md`.
For supply charts, see `references/coin-supply.md`.

---

## `GET /coins/{id}/history` — Coin Historical Data by ID

| Field | Value |
|---|---|
| Description | Query historical price, market cap, and 24hr volume for a coin at a specific date |
| Path | `GET /coins/{id}/history` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes (path) | CoinGecko coin ID |
| `date` | string | Yes | Date snapshot in `DD-MM-YYYY` format |
| `localization` | boolean | No | Include localized coin names. Default: `true` |

### Notes
- Data is returned at `00:00:00 UTC` for the given date.

### Example Response
```json
{
  "id": "bitcoin",
  "symbol": "btc",
  "name": "Bitcoin",
  "image": {
    "thumb": "https://assets.coingecko.com/coins/images/1/thumb/bitcoin.png",
    "small": "https://assets.coingecko.com/coins/images/1/small/bitcoin.png"
  },
  "market_data": {
    "current_price": { "usd": 42074.71 },
    "market_cap": { "usd": 822933961870.54 },
    "total_volume": { "usd": 24832397519.05 }
  }
}
```

### Response Fields

| Field | Description |
|---|---|
| `id` | Coin ID |
| `symbol` | Coin symbol |
| `name` | Coin name |
| `localization` | Coin name in all languages. Present when `localization=true` |
| `image.thumb` | Thumbnail image URL |
| `image.small` | Small image URL |
| `market_data.current_price` | Price in all supported currencies at the given date |
| `market_data.market_cap` | Market cap in all supported currencies |
| `market_data.total_volume` | 24hr volume in all supported currencies |
| `community_data` | Community stats (Facebook likes, Reddit metrics) |
| `developer_data` | GitHub repo stats (forks, stars, commits, issues) |
| `public_interest_stats` | Alexa rank and Bing matches |

---

## `GET /coins/{id}/market_chart` — Coin Historical Chart Data by ID

| Field | Value |
|---|---|
| Description | Query historical price, market cap, and 24hr volume time-series up to N days ago |
| Path | `GET /coins/{id}/market_chart` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes (path) | CoinGecko coin ID |
| `vs_currency` | string | Yes | Target currency. Refer to `references/utils.md` → `GET /simple/supported_vs_currencies` |
| `days` | string | Yes | Number of days ago (`1`, `7`, `14`, `30`, `90`, `180`, `365`, or `max`) |
| `interval` | string | No | Explicit granularity override — omit for auto (recommended). Options: `daily`, `5m`, `hourly`. See `references/core.md` → Auto-granularity |
| `precision` | string | No | Decimal places: `full` or `0`–`18` |

### Notes
- Leave `interval` empty for automatic granularity (see `references/core.md`).

### Response

Returns `prices`, `market_caps`, and `total_volumes` — each an array of `[UNIX timestamp (ms), value]` pairs. See example under `market_chart/range` below.

---

## `GET /coins/{id}/market_chart/range` — Coin Historical Chart Data within Time Range by ID

| Field | Value |
|---|---|
| Description | Query historical price, market cap, and 24hr volume within a specific date range |
| Path | `GET /coins/{id}/market_chart/range` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes (path) | CoinGecko coin ID |
| `vs_currency` | string | Yes | Target currency. Refer to `references/utils.md` → `GET /simple/supported_vs_currencies` |
| `from` | string | Yes | Start date — ISO string (`YYYY-MM-DD`) recommended, or UNIX timestamp |
| `to` | string | Yes | End date — ISO string (`YYYY-MM-DD`) recommended, or UNIX timestamp |
| `interval` | string | No | Explicit granularity override — omit for auto (recommended). Options: `daily`, `5m`, `hourly`. See `references/core.md` → Auto-granularity |
| `precision` | string | No | Decimal places: `full` or `0`–`18` |

### Notes
- Leave `interval` empty for automatic granularity (see `references/core.md`).

### Example Response
```json
{
  "prices": [
    [1704067241331, 42261.04],
    [1704070847420, 42493.28]
  ],
  "market_caps": [
    [1704067241331, 827596236151.20],
    [1704070847420, 831531023621.41]
  ],
  "total_volumes": [
    [1704067241331, 14305769170.95],
    [1704070847420, 14130205376.17]
  ]
}
```

### Response Fields

| Field | Description |
|---|---|
| `prices` | Array of `[UNIX timestamp (ms), price]` pairs |
| `market_caps` | Array of `[UNIX timestamp (ms), market cap]` pairs |
| `total_volumes` | Array of `[UNIX timestamp (ms), 24hr volume]` pairs |

---

## OHLC Endpoints

Both OHLC endpoints return the same response format: an array of 5-element arrays.

### OHLC Response Format

```json
[
  [1709395200000, 61942, 62211, 61721, 61845],
  [1709409600000, 61828, 62139, 61726, 62139]
]
```

| Index | Description |
|---|---|
| `[0]` | UNIX timestamp in milliseconds (close time of the candle) |
| `[1]` | Open price |
| `[2]` | High price |
| `[3]` | Low price |
| `[4]` | Close price |

---

## `GET /coins/{id}/ohlc` — Coin OHLC Chart by ID

| Field | Value |
|---|---|
| Description | Query OHLC candlestick data for a coin up to N days ago |
| Path | `GET /coins/{id}/ohlc` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes (path) | CoinGecko coin ID |
| `vs_currency` | string | Yes | Target currency. Refer to `references/utils.md` → `GET /simple/supported_vs_currencies` |
| `days` | string | Yes | Number of days ago: `1`, `7`, `14`, `30`, `90`, `180`, `365`, or `max` |
| `interval` | string | No | Candle interval: `daily` or `hourly`. Leave empty for auto granularity |
| `precision` | string | No | Decimal places: `full` or `0`–`18` |

### Notes
- Leaving `interval` empty uses auto granularity:
  - 1–2 days → 30-minute candles
  - 3–30 days → 4-hour candles
  - 31 days and above → 4-day candles

---

## `GET /coins/{id}/ohlc/range` — Coin OHLC Chart within Time Range by ID

| Field | Value |
|---|---|
| Description | Query OHLC candlestick data for a coin within a specific date range |
| Path | `GET /coins/{id}/ohlc/range` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes (path) | CoinGecko coin ID |
| `vs_currency` | string | Yes | Target currency. Refer to `references/utils.md` → `GET /simple/supported_vs_currencies` |
| `from` | string | Yes | Start date — ISO string (`YYYY-MM-DD`) recommended, or UNIX timestamp |
| `to` | string | Yes | End date — ISO string (`YYYY-MM-DD`) recommended, or UNIX timestamp |
| `interval` | string | Yes | Candle interval: `daily` (max 180 days / 180 candles) or `hourly` (max 31 days / 744 candles) |

### Notes
- Data available from 9 February 2018 onwards.