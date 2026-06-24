# CoinGecko API — Coin Supply Charts Reference

Covers historical circulating and total supply time-series by coin ID. Load this file
when the user asks about supply charts, circulating supply history, total supply history,
or token emission schedules.

For current circulating/total supply figures (not charts), see `references/coins.md` →
`GET /coins/{id}`.

Auto-granularity applies per `references/core.md`.

---

## `GET /coins/{id}/circulating_supply_chart` — Circulating Supply Chart by ID

| Field | Value |
|---|---|
| Description | Query historical circulating supply of a coin up to N days ago |
| Path | `GET /coins/{id}/circulating_supply_chart` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes (path) | CoinGecko coin ID |
| `days` | string | Yes | Number of days ago — any integer or `max` |
| `interval` | string | No | Data granularity: `5m`, `hourly`, or `daily`. Leave empty for auto granularity |

### Example Response
```json
{
  "circulating_supply": [
    [1712448000000, "19675268.0"],
    [1712534400000, "19675268.0"]
  ]
}
```

### Response Fields

| Field | Description |
|---|---|
| `circulating_supply` | Array of `[UNIX timestamp (ms), circulating supply]` pairs. Supply value is a string |

---

## `GET /coins/{id}/circulating_supply_chart/range` — Circulating Supply Chart within Time Range by ID

| Field | Value |
|---|---|
| Description | Query historical circulating supply of a coin within a specific date range |
| Path | `GET /coins/{id}/circulating_supply_chart/range` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes (path) | CoinGecko coin ID |
| `from` | string | Yes | Start date — ISO string (`YYYY-MM-DD`) recommended, or UNIX timestamp |
| `to` | string | Yes | End date — ISO string (`YYYY-MM-DD`) recommended, or UNIX timestamp |

### Response Fields

Same as `circulating_supply_chart` above.

---

## `GET /coins/{id}/total_supply_chart` — Total Supply Chart by ID

| Field | Value |
|---|---|
| Description | Query historical total supply of a coin up to N days ago |
| Path | `GET /coins/{id}/total_supply_chart` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes (path) | CoinGecko coin ID |
| `days` | string | Yes | Number of days ago — any integer or `max` |
| `interval` | string | No | Only `daily` is supported. Leave empty for auto granularity |

### Example Response
```json
{
  "total_supply": [
    [1712448000000, "21000000.0"],
    [1712534400000, "21000000.0"]
  ]
}
```

### Response Fields

| Field | Description |
|---|---|
| `total_supply` | Array of `[UNIX timestamp (ms), total supply]` pairs. Supply value is a string |

---

## `GET /coins/{id}/total_supply_chart/range` — Total Supply Chart within Time Range by ID

| Field | Value |
|---|---|
| Description | Query historical total supply of a coin within a specific date range |
| Path | `GET /coins/{id}/total_supply_chart/range` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes (path) | CoinGecko coin ID |
| `from` | string | Yes | Start date — ISO string (`YYYY-MM-DD`) recommended, or UNIX timestamp |
| `to` | string | Yes | End date — ISO string (`YYYY-MM-DD`) recommended, or UNIX timestamp |

### Notes
- Returns data at daily intervals (00:00 UTC) — no `interval` param.

### Response Fields

Same as `total_supply_chart` above.