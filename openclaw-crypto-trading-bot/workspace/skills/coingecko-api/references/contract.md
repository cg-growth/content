# CoinGecko API — Contract Address Reference

Covers endpoints that identify coins and fetch data by asset platform + token contract
address rather than CoinGecko coin ID. Load this file when the user has a contract
address (e.g. `0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48`) instead of a coin ID, or
when they ask for token price, coin data, or historical charts by contract address.

Asset platform IDs can be resolved via `references/asset-platforms.md` →
`GET /asset_platforms`. Supported currencies via `references/utils.md` →
`GET /simple/supported_vs_currencies`.

---

## `GET /simple/token_price/{id}` — Coin Price by Token Addresses

| Field | Value |
|---|---|
| Description | Query current price(s) for one or more tokens by contract address |
| Path | `GET /simple/token_price/{id}` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes (path) | Asset platform ID. Refer to `references/asset-platforms.md` → `GET /asset_platforms` |
| `contract_addresses` | string | Yes | One or more token contract addresses, comma-separated |
| `vs_currencies` | string | Yes | One or more target currencies, comma-separated. Refer to `references/utils.md` → `GET /simple/supported_vs_currencies` |
| `include_market_cap` | boolean | No | Include market cap. Default: `false` |
| `include_24hr_vol` | boolean | No | Include 24hr volume. Default: `false` |
| `include_24hr_change` | boolean | No | Include 24hr price change. Default: `false` |
| `include_last_updated_at` | boolean | No | Include last updated UNIX timestamp. Default: `false` |
| `precision` | string | No | Decimal places: `full` or `0`–`18` |

### Notes
- Returns the global average price aggregated across all active exchanges on CoinGecko.

### Example Response
```json
{
  "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599": {
    "usd": 67187.34,
    "usd_market_cap": 1317802988326.25,
    "usd_24h_vol": 31260929299.52,
    "usd_24h_change": 3.64,
    "last_updated_at": 1711356300
  }
}
```

### Response Fields

| Field | Description |
|---|---|
| `{contract_address}` | Top-level key is the queried contract address |
| `{vs_currency}` | Price in the requested currency |
| `{vs_currency}_market_cap` | Market cap. Present when `include_market_cap=true` |
| `{vs_currency}_24h_vol` | 24hr volume. Present when `include_24hr_vol=true` |
| `{vs_currency}_24h_change` | 24hr price change %. Present when `include_24hr_change=true` |
| `last_updated_at` | Last updated UNIX timestamp. Present when `include_last_updated_at=true` |

---

## `GET /coins/{id}/contract/{contract_address}` — Coin Data by Token Address

| Field | Value |
|---|---|
| Description | Query full coin metadata and market data using an asset platform and contract address |
| Path | `GET /coins/{id}/contract/{contract_address}` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes (path) | Asset platform ID. Refer to `references/asset-platforms.md` → `GET /asset_platforms` |
| `contract_address` | string | Yes (path) | Token contract address |

### Notes
- Returns the same data structure as `GET /coins/{id}` in `references/coins.md`. Refer there for the full response field reference.
- Coin descriptions may contain `\r\n` newline escape sequences.

### Example Response
```json
{
  "id": "usd-coin",
  "symbol": "usdc",
  "name": "USDC",
  "asset_platform_id": "ethereum",
  "platforms": {
    "ethereum": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
    "solana": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
  },
  "detail_platforms": {
    "ethereum": {
      "decimal_place": 6,
      "contract_address": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
    }
  }
}
```

### Response Fields

See `references/coins.md` → `GET /coins/{id}` for the complete field reference. Additional contract-specific fields:

| Field | Description |
|---|---|
| `asset_platform_id` | The asset platform this coin is primarily associated with |
| `platforms` | Map of platform ID → contract address for all chains this token is deployed on |
| `detail_platforms` | Map of platform ID → `{decimal_place, contract_address}` with token decimal precision |

---

## `GET /coins/{id}/contract/{contract_address}/market_chart` — Coin Historical Chart Data by Token Address

| Field | Value |
|---|---|
| Description | Query historical price, market cap, and 24hr volume time-series by contract address up to N days ago |
| Path | `GET /coins/{id}/contract/{contract_address}/market_chart` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes (path) | Asset platform ID |
| `contract_address` | string | Yes (path) | Token contract address |
| `vs_currency` | string | Yes | Target currency |
| `days` | string | Yes | Number of days ago — any integer or `max` |
| `interval` | string | No | Explicit granularity override — omit for auto. See `references/core.md` → Auto-granularity |
| `precision` | string | No | Decimal places: `full` or `0`–`18` |

### Response

Same shape as `references/coin-history.md` → `GET /coins/{id}/market_chart/range` (arrays of `[timestamp, value]` pairs for `prices`, `market_caps`, `total_volumes`).

---

## `GET /coins/{id}/contract/{contract_address}/market_chart/range` — Coin Historical Chart Data within Time Range by Token Address

| Field | Value |
|---|---|
| Description | Query historical price, market cap, and 24hr volume within a specific date range by contract address |
| Path | `GET /coins/{id}/contract/{contract_address}/market_chart/range` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes (path) | Asset platform ID |
| `contract_address` | string | Yes (path) | Token contract address |
| `vs_currency` | string | Yes | Target currency |
| `from` | string | Yes | Start date — ISO string (`YYYY-MM-DD`) recommended, or UNIX timestamp |
| `to` | string | Yes | End date — ISO string (`YYYY-MM-DD`) recommended, or UNIX timestamp |
| `interval` | string | No | Explicit granularity override — omit for auto. See `references/core.md` → Auto-granularity |
| `precision` | string | No | Decimal places: `full` or `0`–`18` |

### Response

Same shape as `references/coin-history.md` → `GET /coins/{id}/market_chart/range`.