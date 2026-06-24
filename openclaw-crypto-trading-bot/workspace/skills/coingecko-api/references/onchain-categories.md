# CoinGecko API — Onchain Categories Reference

GeckoTerminal category discovery and pool filtering by category. Load this file when
the user asks about onchain/GeckoTerminal categories, wants to browse pools by theme
(e.g. memecoins, launchpad tokens), or needs a category ID for filtering.

**GeckoTerminal categories are distinct from CoinGecko categories.** For CoinGecko
categories, use `references/categories.md` instead.

---

## `GET /onchain/categories` — Categories List

| Parameter | Type | Required | Description |
|---|---|---|---|
| `page` | integer | No | Default: `1`. Returns 50 categories per page |
| `sort` | string | No | See sort values below. Default: `h6_volume_percentage_desc` |

**`sort` values:** `h1_volume_percentage_desc`, `h6_volume_percentage_desc` (default),
`h12_volume_percentage_desc`, `h24_tx_count_desc`, `h24_volume_usd_desc`,
`fdv_usd_desc`, `reserve_in_usd_desc`

### Notes
- `data[].id` is the `category_id` path param used in `GET /onchain/categories/{category_id}/pools`.

### Example Response
```json
{
  "data": [
    {
      "id": "memecoin",
      "type": "category",
      "attributes": {
        "name": "Memecoin",
        "description": "Tokens that are memes or related to meme images.",
        "volume_change_percentage": {
          "h1": "-20.99", "h6": "1899.02", "h12": "1114.05", "h24": "554.86"
        },
        "reserve_in_usd": "196471556.46",
        "fdv_usd": "7525785445.92",
        "h24_volume_usd": "47065466.48",
        "h24_tx_count": 74150
      }
    }
  ]
}
```

### Response Fields

| Field | Type | Description |
|---|---|---|
| `data[].id` | string | Category ID — use as `{category_id}` in pools endpoint |
| `data[].attributes.name` | string | Category display name |
| `data[].attributes.description` | string | Category description |
| `data[].attributes.volume_change_percentage` | object | Volume change % keyed by interval: `h1`, `h6`, `h12`, `h24` (strings) |
| `data[].attributes.reserve_in_usd` | string | Total liquidity reserve across category pools |
| `data[].attributes.fdv_usd` | string | Combined FDV across category tokens |
| `data[].attributes.h24_volume_usd` | string | 24hr trading volume in USD |
| `data[].attributes.h24_tx_count` | integer | 24hr transaction count |

---

## `GET /onchain/categories/{category_id}/pools` — Pools by Category ID

| Parameter | Type | Required | Description |
|---|---|---|---|
| `category_id` | string | Yes | Category ID — refer to `GET /onchain/categories` above |
| `include` | string | No | `base_token`, `quote_token`, `dex`, `network` (comma-separated). Sideloaded under `included` |
| `page` | integer | No | Default: `1`. Max 20 pools per page |
| `sort` | string | No | See sort values below. Default: `pool_created_at_desc` |

**`sort` values:** `pool_created_at_desc` (default), `m5_trending`, `h1_trending`,
`h6_trending`, `h24_trending`, `h24_tx_count_desc`, `h24_volume_usd_desc`,
`h24_price_change_percentage_desc`

### Notes
- Pool response shape matches `references/onchain-pools.md` with two additions: `h24_volume_usd` (string) and `h24_tx_count` (integer) are included directly in `attributes`.
- `relationships` includes `network` (in addition to `base_token`, `quote_token`, `dex`), even without `include=network`. To get full network attributes, add `include=network`.
- To retrieve tokens for a category, use `include=base_token` and read the `included` array.

### Example Response
```json
{
  "data": [
    {
      "id": "solana_7dRpAUh3tYbtsVCZrtPXdwuk7ehbawrFo8xKCmDdj28V",
      "type": "pool",
      "attributes": {
        "address": "7dRpAUh3tYbtsVCZrtPXdwuk7ehbawrFo8xKCmDdj28V",
        "name": "SNAI / USDC",
        "pool_created_at": "2024-12-21T08:24:25Z",
        "base_token_price_usd": "0.0109071807291731",
        "fdv_usd": null,
        "market_cap_usd": null,
        "reserve_in_usd": "1087091.0112",
        "h24_volume_usd": "104.52",
        "h24_tx_count": 9,
        "price_change_percentage": { "m5": "0", "h1": "-0.13", "h24": "-1.18" }
      },
      "relationships": {
        "network": { "data": { "id": "solana", "type": "network" } },
        "dex": { "data": { "id": "raydium-clmm", "type": "dex" } },
        "base_token": { "data": { "id": "solana_JBMwoVt...", "type": "token" } },
        "quote_token": { "data": { "id": "solana_EPjFWdd...", "type": "token" } }
      }
    }
  ],
  "included": [
    {
      "id": "solana_JBMwoVtjMYFQJY4vYuM4JUkdEhDz7cgF45w8TeVGXgAB",
      "type": "token",
      "attributes": {
        "address": "JBMwoVtjMYFQJY4vYuM4JUkdEhDz7cgF45w8TeVGXgAB",
        "name": "SwarmNode.ai",
        "symbol": "SNAI",
        "decimals": 6,
        "image_url": "missing.png",
        "coingecko_coin_id": null
      }
    }
  ]
}
```