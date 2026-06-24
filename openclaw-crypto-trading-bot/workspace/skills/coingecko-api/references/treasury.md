# CoinGecko API — Public Treasury Reference

Covers public company and government cryptocurrency treasury data: entity discovery,
current holdings, historical holding charts, and transaction history. Load this file
when the user asks about corporate Bitcoin treasuries, government crypto holdings,
MicroStrategy/Strategy holdings, treasury transactions, or entity-level crypto data.

Entity IDs can be resolved via `GET /entities/list` below.

---

## `GET /entities/list` — Entities List (ID Map)

| Field | Value |
|---|---|
| Description | Query all supported public company and government entities with their IDs |
| Path | `GET /entities/list` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `entity_type` | string | No | Filter by type: `company` or `government`. Default: all |
| `per_page` | integer | No | Results per page. Default: `100`. Max: `250` |
| `page` | integer | No | Page number. Default: `1` |

### Example Response
```json
[
  { "id": "strategy", "symbol": "MSTR.US", "name": "Strategy", "country": "US" },
  { "id": "mara-holdings", "symbol": "MARA.US", "name": "MARA Holdings", "country": "US" }
]
```

### Response Fields

| Field | Description |
|---|---|
| `id` | Entity ID — use in all treasury endpoints |
| `symbol` | Stock market ticker symbol (public companies only) |
| `name` | Entity name |
| `country` | Country code |

---

## `GET /{entity}/public_treasury/{coin_id}` — Crypto Treasury Holdings by Coin ID

| Field | Value |
|---|---|
| Description | Query all companies or governments holding a specific coin, with aggregate stats |
| Path | `GET /{entity}/public_treasury/{coin_id}` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `entity` | string | Yes (path) | Entity type: `companies` or `governments` |
| `coin_id` | string | Yes (path) | CoinGecko coin ID (e.g. `bitcoin`, `ethereum`, `solana`) |
| `per_page` | integer | No | Results per page. Default: `250`. Max: `250` |
| `page` | integer | No | Page number. Default: `1` |
| `order` | string | No | Sort order. Default: `total_holdings_usd_desc`. Options: `total_holdings_usd_desc`, `total_holdings_usd_asc` |

### Example Response
```json
{
  "total_holdings": 2500000,
  "total_value_usd": 172500000000,
  "market_cap_dominance": 12.5,
  "companies": [
    {
      "name": "Strategy",
      "symbol": "MSTR.US",
      "country": "US",
      "total_holdings": 714644,
      "total_entry_value_usd": 54674553864,
      "total_current_value_usd": 48119580010,
      "percentage_of_total_supply": 3.403
    }
  ]
}
```

### Response Fields

| Field | Description |
|---|---|
| `total_holdings` | Aggregate coin holdings across all entities |
| `total_value_usd` | Total current value in USD |
| `market_cap_dominance` | Holdings as a percentage of total market cap |
| `companies` or `governments` | Array of entity holdings (key matches `entity` path param) |
| `[].name` | Entity name |
| `[].symbol` | Stock ticker symbol |
| `[].country` | Country code |
| `[].total_holdings` | Total coin holdings |
| `[].total_entry_value_usd` | Total cost basis in USD |
| `[].total_current_value_usd` | Current value in USD |
| `[].percentage_of_total_supply` | Holdings as a percentage of total coin supply |

---

## `GET /public_treasury/{entity_id}` — Crypto Treasury Holdings by Entity ID

| Field | Value |
|---|---|
| Description | Query a single entity's full treasury holdings with optional change data |
| Path | `GET /public_treasury/{entity_id}` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `entity_id` | string | Yes (path) | Entity ID. Refer to `GET /entities/list` above |
| `holding_amount_change` | string | No | Include holding amount change for specified timeframes, comma-separated. Valid values: `7d`, `14d`, `30d`, `90d`, `1y`, `ytd` |
| `holding_change_percentage` | string | No | Include holding change percentage for specified timeframes, comma-separated. Valid values: `7d`, `14d`, `30d`, `90d`, `1y`, `ytd` |

### Example Response
```json
{
  "name": "Strategy",
  "id": "strategy",
  "type": "company",
  "symbol": "MSTR.US",
  "country": "US",
  "website_url": "https://www.strategy.com/",
  "twitter_screen_name": "Strategy",
  "total_treasury_value_usd": 48119580010.66,
  "unrealized_pnl": -6554973853.34,
  "m_nav": 0.99,
  "total_asset_value_per_share_usd": 150.46,
  "holdings": [
    {
      "coin_id": "bitcoin",
      "amount": 714644,
      "percentage_of_total_supply": 3.403,
      "amount_per_share": 0.00223,
      "entity_value_usd_percentage": 100,
      "current_value_usd": 48119580010.66,
      "total_entry_value_usd": 54674553864,
      "average_entry_value_usd": 76506,
      "unrealized_pnl": -6554973853.34,
      "holding_amount_change": { "7d": 1142, "30d": 27234, "1y": 235904 },
      "holding_change_percentage": { "7d": 0.16, "30d": 3.962, "1y": 49.276 }
    }
  ]
}
```

### Response Fields

| Field | Description |
|---|---|
| `name` | Entity name |
| `id` | Entity ID |
| `type` | Entity type: `company` or `government` |
| `symbol` | Stock ticker symbol |
| `country` | Country code |
| `website_url` | Official website URL |
| `twitter_screen_name` | Twitter/X handle |
| `total_treasury_value_usd` | Total current value of all holdings in USD |
| `unrealized_pnl` | Unrealized P&L (current value minus total entry cost) |
| `m_nav` | Market-to-NAV ratio |
| `total_asset_value_per_share_usd` | Crypto NAV per share in USD |
| `holdings[].coin_id` | CoinGecko coin ID |
| `holdings[].amount` | Amount of the coin held |
| `holdings[].percentage_of_total_supply` | Holdings as percentage of total supply |
| `holdings[].amount_per_share` | Coin amount per share of the entity |
| `holdings[].entity_value_usd_percentage` | This holding as percentage of entity's total treasury value |
| `holdings[].current_value_usd` | Current value in USD |
| `holdings[].total_entry_value_usd` | Total cost basis in USD |
| `holdings[].average_entry_value_usd` | Average entry price per unit in USD |
| `holdings[].unrealized_pnl` | Unrealized P&L for this holding |
| `holdings[].holding_amount_change` | Change in holding amount by timeframe. Present when `holding_amount_change` param is used |
| `holdings[].holding_change_percentage` | Change percentage by timeframe. Present when `holding_change_percentage` param is used |

---

## `GET /public_treasury/{entity_id}/{coin_id}/holding_chart` — Crypto Treasury Holdings Historical Chart Data by ID

| Field | Value |
|---|---|
| Description | Query historical holding amount and USD value chart for an entity's specific coin |
| Path | `GET /public_treasury/{entity_id}/{coin_id}/holding_chart` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `entity_id` | string | Yes (path) | Entity ID. Refer to `GET /entities/list` above |
| `coin_id` | string | Yes (path) | CoinGecko coin ID (e.g. `bitcoin`, `ethereum`) |
| `days` | string | Yes | Lookback period. Valid values: `7`, `14`, `30`, `90`, `180`, `365`, `730`, `max` |
| `include_empty_intervals` | boolean | No | Include intervals with no transaction data, filled with most recent values. Default: `false` |

### Notes
- Data available from August 2020 onwards.
- When `include_empty_intervals=false` (default), only intervals with transaction activity are returned.

### Example Response
```json
{
  "holdings": [
    [1733097600000, 402100],
    [1733616000000, 423650]
  ],
  "holding_value_in_usd": [
    [1733097600000, 39129037461.44],
    [1733616000000, 42272572276.10]
  ]
}
```

### Response Fields

| Field | Description |
|---|---|
| `holdings` | Array of `[UNIX timestamp (ms), coin amount]` pairs |
| `holding_value_in_usd` | Array of `[UNIX timestamp (ms), USD value]` pairs |

---

## `GET /public_treasury/{entity_id}/transaction_history` — Crypto Treasury Transaction History by Entity ID

| Field | Value |
|---|---|
| Description | Query an entity's cryptocurrency buy/sell transaction history |
| Path | `GET /public_treasury/{entity_id}/transaction_history` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `entity_id` | string | Yes (path) | Entity ID. Refer to `GET /entities/list` above |
| `per_page` | number | No | Results per page. Default: `100`. Max: `250` |
| `page` | number | No | Page number. Default: `1` |
| `order` | string | No | Sort order. Default: `date_desc`. Options: `date_desc`, `date_asc`, `holding_net_change_desc`, `holding_net_change_asc`, `transaction_value_usd_desc`, `transaction_value_usd_asc`, `average_cost_desc`, `average_cost_asc` |
| `coin_ids` | string | No | Filter by coin IDs, comma-separated |

### Notes
- Data available from August 2020 onwards.

### Example Response
```json
{
  "transactions": [
    {
      "date": 1763337600000,
      "source_url": "https://assets.contentstack.io/...",
      "coin_id": "bitcoin",
      "type": "buy",
      "holding_net_change": 8178,
      "transaction_value_usd": 835554438,
      "holding_balance": 649870,
      "average_entry_value_usd": 102171
    }
  ]
}
```

### Response Fields

| Field | Description |
|---|---|
| `transactions[].date` | Transaction date as UNIX timestamp in milliseconds |
| `transactions[].source_url` | Source document URL (e.g. SEC filing) |
| `transactions[].coin_id` | CoinGecko coin ID |
| `transactions[].type` | Transaction type: `buy` or `sell` |
| `transactions[].holding_net_change` | Net change in holdings from this transaction |
| `transactions[].transaction_value_usd` | Transaction value in USD |
| `transactions[].holding_balance` | Total holdings after the transaction |
| `transactions[].average_entry_value_usd` | Average cost basis per unit after the transaction |