# CoinGecko API — Global Market Data Reference

Covers global crypto market stats, DeFi market data, and historical global market cap
charts. Load this file when the user asks about total crypto market cap, global trading
volume, BTC dominance, DeFi market cap, or historical global market chart data.

---

## `GET /global` — Crypto Global Market Data

| Field | Value |
|---|---|
| Description | Query global cryptocurrency market data including total market cap, volume, and dominance |
| Path | `GET /global` |

### Parameters

None.

### Example Response
```json
{
  "data": {
    "active_cryptocurrencies": 13690,
    "upcoming_icos": 0,
    "ongoing_icos": 49,
    "ended_icos": 3376,
    "markets": 1046,
    "total_market_cap": { "usd": 2721226850772.63, "btc": 39003738.08 },
    "total_volume": { "usd": 69327091133.55, "btc": 993675.23 },
    "market_cap_percentage": {
      "btc": 50.45,
      "eth": 14.92,
      "usdt": 3.93
    },
    "market_cap_change_percentage_24h_usd": 1.72,
    "volume_change_percentage_24h_usd": -0.27,
    "updated_at": 1712512855
  }
}
```

### Response Fields

| Field | Description |
|---|---|
| `data.active_cryptocurrencies` | Number of active cryptocurrencies tracked |
| `data.upcoming_icos` | Number of upcoming ICOs |
| `data.ongoing_icos` | Number of ongoing ICOs |
| `data.ended_icos` | Number of ended ICOs |
| `data.markets` | Number of active exchanges |
| `data.total_market_cap` | Total crypto market cap in all supported currencies |
| `data.total_volume` | Total 24hr trading volume in all supported currencies |
| `data.market_cap_percentage` | Market cap dominance by coin (top coins, keyed by symbol) |
| `data.market_cap_change_percentage_24h_usd` | Global market cap 24hr change % in USD |
| `data.volume_change_percentage_24h_usd` | Global volume 24hr change % in USD |
| `data.updated_at` | Last updated UNIX timestamp |

---

## `GET /global/decentralized_finance_defi` — Global DeFi Market Data

| Field | Value |
|---|---|
| Description | Query global DeFi market data based on the top 100 DeFi coins |
| Path | `GET /global/decentralized_finance_defi` |

### Parameters

None.

### Notes
- Data is derived from the top 100 DeFi cryptocurrencies only.

### Example Response
```json
{
  "data": {
    "defi_market_cap": "105273842288.23",
    "eth_market_cap": "406184911478.58",
    "defi_to_eth_ratio": "25.92",
    "trading_volume_24h": "5046503746.29",
    "defi_dominance": "3.87",
    "top_coin_name": "Lido Staked Ether",
    "top_coin_defi_dominance": 30.59
  }
}
```

### Response Fields

| Field | Description |
|---|---|
| `data.defi_market_cap` | Total DeFi market cap in USD (string) |
| `data.eth_market_cap` | Ethereum market cap in USD (string) |
| `data.defi_to_eth_ratio` | DeFi market cap as a percentage of Ethereum market cap (string) |
| `data.trading_volume_24h` | Total DeFi 24hr trading volume in USD (string) |
| `data.defi_dominance` | DeFi market cap as a percentage of total crypto market cap (string) |
| `data.top_coin_name` | Name of the largest DeFi coin by market cap |
| `data.top_coin_defi_dominance` | Largest DeFi coin's dominance within DeFi market cap (number) |

---

## `GET /global/market_cap_chart` — Global Market Cap Chart Data

| Field | Value |
|---|---|
| Description | Query historical global total market cap and volume time-series |
| Path | `GET /global/market_cap_chart` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `days` | string | Yes | Lookback period: `1`, `7`, `14`, `30`, `90`, `180`, `365`, or `max` |
| `vs_currency` | string | No | Target currency. Default: `usd`. Refer to `references/utils.md` → `GET /simple/supported_vs_currencies` |

### Notes
- Granularity is automatic: 1 day → hourly; 2 days and above → daily.

### Example Response
```json
{
  "market_cap_chart": {
    "market_cap": [
      [1741777205268, 2766533155566],
      [1741780800808, 2784800753369]
    ],
    "volume": [
      [1741777205268, 141144791036],
      [1741780800808, 140341392201]
    ]
  }
}
```

### Response Fields

| Field | Description |
|---|---|
| `market_cap_chart.market_cap` | Array of `[UNIX timestamp (ms), total market cap]` pairs |
| `market_cap_chart.volume` | Array of `[UNIX timestamp (ms), total 24hr volume]` pairs |