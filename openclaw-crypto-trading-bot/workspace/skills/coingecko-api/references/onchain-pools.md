# CoinGecko API — Onchain Pools Reference

Pool discovery, data retrieval, and filtering via GeckoTerminal. Load this file for
any request involving DEX pool data: specific pool lookup, trending/new pools, top
pools by network or DEX, multi-address batch lookup, megafilter, or pool search.

Requires network IDs and DEX IDs — load `references/onchain-networks.md` first if
those are unknown.

---

## Shared Pool Response Shape

All list and lookup endpoints return data in this structure. Differences between
endpoints are called out in per-endpoint notes.

```json
{
  "data": [
    {
      "id": "eth_0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
      "type": "pool",
      "attributes": {
        "address": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
        "name": "WETH / USDC 0.05%",
        "pool_created_at": "2021-12-29T12:35:14Z",
        "base_token_price_usd": "3653.12",
        "base_token_price_native_currency": "1.0",
        "quote_token_price_usd": "0.998",
        "quote_token_price_native_currency": "0.000273",
        "base_token_price_quote_token": "3662.46",
        "quote_token_price_base_token": "0.000273",
        "fdv_usd": "11007041041",
        "market_cap_usd": null,
        "reserve_in_usd": "163988541.38",
        "price_change_percentage": { "m5": "0", "m15": "0.21", "h1": "0.51", "h6": "0.86", "h24": "7.71" },
        "transactions": {
          "m5": { "buys": 7, "sells": 2, "buyers": 7, "sellers": 2 },
          "h24": { "buys": 2966, "sells": 3847, "buyers": 1625, "sellers": 2399 }
        },
        "volume_usd": { "m5": "868581.73", "h1": "16798158.01", "h24": "536545444.90" }
      },
      "relationships": {
        "base_token": { "data": { "id": "eth_0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", "type": "token" } },
        "quote_token": { "data": { "id": "eth_0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", "type": "token" } },
        "dex": { "data": { "id": "uniswap_v3", "type": "dex" } }
      }
    }
  ],
  "included": [
    {
      "id": "eth_0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
      "type": "token",
      "attributes": {
        "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
        "name": "Wrapped Ether",
        "symbol": "WETH",
        "decimals": 18,
        "image_url": "https://assets.coingecko.com/coins/images/2518/small/weth.png",
        "coingecko_coin_id": "weth"
      }
    }
  ]
}
```

### Pool Attributes

| Field | Type | Description |
|---|---|---|
| `address` | string | Pool contract address |
| `name` | string | Pool display name (e.g. `WETH / USDC 0.05%`) |
| `pool_created_at` | string | ISO 8601 creation timestamp |
| `base_token_price_usd` | string | Base token price in USD |
| `base_token_price_native_currency` | string | Base token price in the network's native currency |
| `quote_token_price_usd` | string | Quote token price in USD |
| `quote_token_price_native_currency` | string | Quote token price in the network's native currency |
| `base_token_price_quote_token` | string | Base token price denominated in quote token |
| `quote_token_price_base_token` | string | Quote token price denominated in base token |
| `fdv_usd` | string | Fully diluted valuation in USD |
| `market_cap_usd` | string \| null | Market cap in USD — `null` if not verified by CoinGecko team |
| `reserve_in_usd` | string | Total liquidity reserve in USD |
| `price_change_percentage` | object | Price change % keyed by interval: `m5`, `m15`, `m30`, `h1`, `h6`, `h24` (strings) |
| `transactions` | object | Buy/sell counts keyed by interval: `m5`, `m15`, `m30`, `h1`, `h6`, `h24`. Each: `buys`, `sells`, `buyers`, `sellers` (integers) |
| `volume_usd` | object | Volume in USD keyed by interval: `m5`, `m15`, `m30`, `h1`, `h6`, `h24` (strings) |

**Extended attributes** (only on single-pool and multi-pool lookup endpoints):

| Field | Type | Description |
|---|---|---|
| `pool_name` | string | Pool name without fee tier |
| `pool_fee_percentage` | string | Pool fee tier (e.g. `"0.05"`) |
| `base_token_balance` | string | Base token balance (requires `include_composition=true`) |
| `base_token_liquidity_usd` | string | Base token liquidity in USD (requires `include_composition=true`) |
| `quote_token_balance` | string | Quote token balance (requires `include_composition=true`) |
| `quote_token_liquidity_usd` | string | Quote token liquidity in USD (requires `include_composition=true`) |
| `net_buy_volume_usd` | object | Net buy volume by interval (requires `include_volume_breakdown=true`) |
| `buy_volume_usd` | object | Buy-side volume by interval (requires `include_volume_breakdown=true`) |
| `sell_volume_usd` | object | Sell-side volume by interval (requires `include_volume_breakdown=true`) |
| `locked_liquidity_percentage` | string | % of liquidity that is locked (updated daily) |

**Community data attributes** (only when `include_gt_community_data=true`):

| Field | Type | Description |
|---|---|---|
| `sentiment_vote_positive_percentage` | number | % of positive sentiment votes |
| `sentiment_vote_negative_percentage` | number | % of negative sentiment votes |
| `community_sus_report` | number | Number of community suspicious reports |

### `included` Array

Populated when `include` param is used. Each item has `id`, `type`, and `attributes`:

| `type` | `attributes` fields |
|---|---|
| `token` | `address`, `name`, `symbol`, `decimals`, `image_url`, `coingecko_coin_id` |
| `dex` | `name` |
| `network` | `name`, `coingecko_asset_platform_id` |

### Common Notes (all endpoints)

- `data[].id` format: `{network_id}_{pool_address}` (e.g. `eth_0x88e6a...`)
- `market_cap_usd` is `null` when not verified; the displayed value on GeckoTerminal may match FDV and not be accurate.
- `include` param values are comma-separated: `base_token`, `quote_token`, `dex`, `network` (availability varies by endpoint).
- Included attributes appear under the top-level `"included"` key, not nested in `data`.
- Max 20 pools per page.

---

## Endpoints

### `GET /onchain/networks/{network}/pools/{address}` — Specific Pool by Address

Returns a single pool object (`data` is an object, not array). Includes extended
attributes. Supports `launchpad_details` for bonding curve pools.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `network` | string | Yes | Network ID |
| `address` | string | Yes | Pool contract address |
| `include` | string | No | `base_token`, `quote_token`, `dex` (comma-separated) |
| `include_volume_breakdown` | boolean | No | Default: `false` |
| `include_composition` | boolean | No | Default: `false` |

---

### `GET /onchain/networks/{network}/pools/multi/{addresses}` — Multiple Pools by Address

Batch lookup. Same extended attributes as single pool endpoint. Up to 50 addresses.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `network` | string | Yes | Network ID |
| `addresses` | string | Yes | Comma-separated pool contract addresses (max 50) |
| `include` | string | No | `base_token`, `quote_token`, `dex` (comma-separated) |
| `include_volume_breakdown` | boolean | No | Default: `false` |
| `include_composition` | boolean | No | Default: `false` |

---

### `GET /onchain/networks/trending_pools` — Trending Pools (All Networks)

| Parameter | Type | Required | Description |
|---|---|---|---|
| `include` | string | No | `base_token`, `quote_token`, `dex`, `network` (comma-separated) |
| `page` | integer | No | Default: `1` |
| `duration` | string | No | Trending window: `5m`, `1h`, `6h`, `24h`. Default: `24h` |
| `include_gt_community_data` | boolean | No | Default: `false` |

Trending rank is based on user engagement, trading activity, and pool security/liquidity checks.

---

### `GET /onchain/networks/{network}/trending_pools` — Trending Pools by Network

Same as above but scoped to one network.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `network` | string | Yes | Network ID |
| `include` | string | No | `base_token`, `quote_token`, `dex` (comma-separated) |
| `page` | integer | No | Default: `1` |
| `duration` | string | No | `5m`, `1h`, `6h`, `24h`. Default: `24h` |
| `include_gt_community_data` | boolean | No | Default: `false` |

---

### `GET /onchain/networks/{network}/pools` — Top Pools by Network

| Parameter | Type | Required | Description |
|---|---|---|---|
| `network` | string | Yes | Network ID |
| `include` | string | No | `base_token`, `quote_token`, `dex` (comma-separated) |
| `page` | integer | No | Default: `1` |
| `sort` | string | No | `h24_tx_count_desc` (default), `h24_volume_usd_desc` |
| `include_gt_community_data` | boolean | No | Default: `false` |

For more control over filtering, use `GET /onchain/pools/megafilter` instead.

---

### `GET /onchain/networks/{network}/dexes/{dex}/pools` — Top Pools by DEX

| Parameter | Type | Required | Description |
|---|---|---|---|
| `network` | string | Yes | Network ID |
| `dex` | string | Yes | DEX ID — refer to `references/onchain-networks.md` → `GET /onchain/networks/{network}/dexes` |
| `include` | string | No | `base_token`, `quote_token`, `dex` (comma-separated) |
| `page` | integer | No | Default: `1` |
| `sort` | string | No | `h24_tx_count_desc` (default), `h24_volume_usd_desc` |
| `include_gt_community_data` | boolean | No | Default: `false` |

---

### `GET /onchain/networks/new_pools` — New Pools (All Networks)

| Parameter | Type | Required | Description |
|---|---|---|---|
| `include` | string | No | `base_token`, `quote_token`, `dex`, `network` (comma-separated) |
| `page` | integer | No | Default: `1` |
| `include_gt_community_data` | boolean | No | Default: `false` |

---

### `GET /onchain/networks/{network}/new_pools` — New Pools by Network

Returns newly created pools in the past 48 hours on the specified network.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `network` | string | Yes | Network ID |
| `include` | string | No | `base_token`, `quote_token`, `dex` (comma-separated) |
| `page` | integer | No | Default: `1` |
| `include_gt_community_data` | boolean | No | Default: `false` |

---

### `GET /onchain/pools/megafilter` — Megafilter for Pools

Full-featured pool filter across all networks. Use this when the simpler top/trending
endpoints lack the required precision.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `include` | string | No | `base_token`, `quote_token`, `dex`, `network` (comma-separated) |
| `page` | integer | No | Default: `1` |
| `networks` | string | No | Filter by network IDs, comma-separated |
| `dexes` | string | No | Filter by DEX IDs, comma-separated. **Only valid when exactly one `networks` value is set** |
| `sort` | string | No | See sort values below. Default: `h6_trending` |
| `fdv_usd_min` / `fdv_usd_max` | number | No | FDV range filter in USD |
| `reserve_in_usd_min` / `reserve_in_usd_max` | number | No | Liquidity reserve range filter in USD |
| `h24_volume_usd_min` / `h24_volume_usd_max` | number | No | 24hr volume range filter in USD |
| `pool_created_hour_min` / `pool_created_hour_max` | number | No | Pool age range in hours |
| `tx_count_min` / `tx_count_max` | integer | No | Transaction count range |
| `tx_count_duration` | string | No | Duration for tx count: `5m`, `1h`, `6h`, `24h`. Default: `24h` |
| `buys_min` / `buys_max` | integer | No | Buy transaction count range |
| `buys_duration` | string | No | `5m`, `1h`, `6h`, `24h`. Default: `24h` |
| `sells_min` / `sells_max` | integer | No | Sell transaction count range |
| `sells_duration` | string | No | `5m`, `1h`, `6h`, `24h`. Default: `24h` |
| `buy_tax_percentage_min` / `buy_tax_percentage_max` | number | No | Buy tax % range |
| `sell_tax_percentage_min` / `sell_tax_percentage_max` | number | No | Sell tax % range |
| `price_change_percentage_min` / `price_change_percentage_max` | number | No | Price change % range |
| `price_change_percentage_duration` | string | No | `5m`, `1h`, `6h`, `24h` |
| `checks` | string | No | Safety/quality filters, comma-separated (see below) |
| `include_unknown_honeypot_tokens` | boolean | No | When `checks` includes `no_honeypot`, also include tokens with unknown honeypot status. Default: `false` |

**`sort` values:**
`m5_trending`, `h1_trending`, `h6_trending` (default), `h24_trending`,
`h24_tx_count_desc`, `h24_tx_count_asc`, `h24_volume_usd_desc`, `h24_volume_usd_asc`,
`m5/h1/h6/h24_price_change_percentage_asc/desc`,
`fdv_usd_asc`, `fdv_usd_desc`,
`reserve_in_usd_asc`, `reserve_in_usd_desc`,
`price_asc`, `price_desc`,
`pool_created_at_desc`

**`checks` values:**

| Value | Effect |
|---|---|
| `no_honeypot` | Exclude honeypot pools (via GoPlus and De.Fi Scanner) |
| `good_gt_score` | Only pools with a GT Score of at least 75 |
| `on_coingecko` | Only pools with tokens listed on CoinGecko |
| `has_social` | Only pools with social links and token info updated |

---

### `GET /onchain/pools/trending_search` — Trending Search Pools

Returns the top trending search pools across all networks. Response attributes are a
**subset** of the standard pool shape: only `trending_rank`, `address`, `name`,
`pool_created_at`, `fdv_usd`, `market_cap_usd`, `volume_usd.h24`, and
`reserve_in_usd`. Price change and transactions are not included.

`relationships` includes `network` in addition to `base_token`, `quote_token`, `dex`.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `include` | string | No | `base_token`, `quote_token`, `dex`, `network` (comma-separated) |
| `pools` | integer | No | Number of pools to return. Max: `10`. Default: `4` |

---

### `GET /onchain/search/pools` — Search Pools & Tokens

Search by pool contract address, token name, token symbol, or token contract address.
Returns the standard pool shape (without extended attributes).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `query` | string | No | Search term — pool address, token name, symbol, or token contract address |
| `network` | string | No | Scope results to a specific network ID |
| `include` | string | No | `base_token`, `quote_token`, `dex` (comma-separated) |
| `page` | integer | No | Default: `1` |