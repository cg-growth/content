# CoinGecko API — Coins Categories Reference

Covers CoinGecko coin category ID maps and category market data. Load this file when
the user needs to resolve a `category` ID for use in `GET /coins/markets` (see
`references/coins.md`), or when they ask for category-level market cap, volume, or
rankings.

Note: CoinGecko categories (this file) are distinct from GeckoTerminal on-chain
categories. For on-chain pool categories, see `references/onchain-categories.md`.

---

## `GET /coins/categories/list` — Coins Categories List (ID Map)

| Field | Value |
|---|---|
| Description | Query all CoinGecko coin category IDs and names |
| Path | `GET /coins/categories/list` |

### Parameters

None.

### Notes
- Use `category_id` values from this endpoint as the `category` filter param in `references/coins.md` → `GET /coins/markets`.

### Example Response
```json
[
  { "category_id": "aave-tokens", "name": "Aave Tokens" },
  { "category_id": "account-abstraction", "name": "Account Abstraction" }
]
```

### Response Fields

| Field | Description |
|---|---|
| `category_id` | Category ID — use as the `category` param in other endpoints. Same value as the `id` field returned by `GET /coins/categories` |
| `name` | Human-readable category name |

---

## `GET /coins/categories` — Coins Categories List with Market Data

| Field | Value |
|---|---|
| Description | Query all CoinGecko coin categories with market cap, volume, and top coins |
| Path | `GET /coins/categories` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `order` | string | No | Sort order. Default: `market_cap_desc`. Options: `market_cap_desc`, `market_cap_asc`, `name_desc`, `name_asc`, `market_cap_change_24h_desc`, `market_cap_change_24h_asc` |

### Example Response
```json
[
  {
    "id": "layer-1",
    "name": "Layer 1 (L1)",
    "market_cap": 2061406861196.14,
    "market_cap_change_24h": -0.66,
    "content": "",
    "top_3_coins_id": ["bitcoin", "ethereum", "binancecoin"],
    "top_3_coins": [
      "https://assets.coingecko.com/coins/images/1/small/bitcoin.png",
      "https://assets.coingecko.com/coins/images/279/small/ethereum.png",
      "https://assets.coingecko.com/coins/images/825/small/bnb-icon2_2x.png"
    ],
    "volume_24h": 61146432400.17,
    "updated_at": "2024-04-06T08:25:46.402Z"
  }
]
```

### Response Fields

| Field | Description |
|---|---|
| `id` | Category ID |
| `name` | Category name |
| `market_cap` | Total market cap of all coins in the category (USD) |
| `market_cap_change_24h` | 24hr market cap change percentage |
| `content` | Category description (may be empty) |
| `top_3_coins_id` | CoinGecko coin IDs of the top 3 coins by market cap in the category |
| `top_3_coins` | Image URLs of the top 3 coins |
| `volume_24h` | Total 24hr trading volume of all coins in the category (USD) |
| `updated_at` | Last updated timestamp (ISO 8601) |