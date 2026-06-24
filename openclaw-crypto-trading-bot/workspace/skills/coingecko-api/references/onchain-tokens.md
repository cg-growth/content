# CoinGecko API — Onchain Tokens Reference

Token data, metadata, holders, traders, and price lookups via GeckoTerminal. Load
this file for any request involving onchain token details: price by contract address,
token market data, token metadata (socials/description/GT Score), top pools for a
token, holders, traders, or recently updated tokens.

Requires network IDs — load `references/onchain-networks.md` first if unknown.

---

## Endpoint Overview

| Summary | Path |
|---|---|
| Token Price by Token Addresses | `GET /onchain/simple/networks/{network}/token_price/{addresses}` |
| Token Data by Token Address | `GET /onchain/networks/{network}/tokens/{address}` |
| Tokens Data by Token Addresses | `GET /onchain/networks/{network}/tokens/multi/{addresses}` |
| Token Info by Token Address | `GET /onchain/networks/{network}/tokens/{address}/info` |
| Pool Tokens Info by Pool Address | `GET /onchain/networks/{network}/pools/{pool_address}/info` |
| Top Pools by Token Address | `GET /onchain/networks/{network}/tokens/{token_address}/pools` |
| Most Recently Updated Tokens List | `GET /onchain/tokens/info_recently_updated` |
| Top Token Holders by Token Address | `GET /onchain/networks/{network}/tokens/{address}/top_holders` |
| Historical Token Holders Chart | `GET /onchain/networks/{network}/tokens/{token_address}/holders_chart` |
| Top Token Traders by Token Address | `GET /onchain/networks/{network_id}/tokens/{token_address}/top_traders` |

---

## Shared Token Info Shape

Several endpoints (`GET .../tokens/{address}/info`, `GET .../pools/{pool_address}/info`,
`GET /tokens/info_recently_updated`) return a **Token Info** object. Fields:

| Field | Type | Description |
|---|---|---|
| `address` | string | Token contract address |
| `name` | string | Token name |
| `symbol` | string | Token symbol |
| `image_url` | string | Token image URL (small size) |
| `image.thumb/small/large` | string | Multi-size image URLs |
| `coingecko_coin_id` | string \| null | CoinGecko coin ID if listed |
| `websites` | array | Official website URLs |
| `description` | string | Token description (may be sourced on-chain, not vetted by CoinGecko) |
| `gt_score` | number | GeckoTerminal score (0–100) |
| `gt_score_details.pool/transaction/creation/info/holders` | number | GT Score component breakdown |
| `discord_url` | string \| null | Discord URL |
| `farcaster_url` | string \| null | Farcaster URL |
| `zora_url` | string \| null | Zora URL |
| `telegram_handle` | string \| null | Telegram handle |
| `twitter_handle` | string \| null | Twitter/X handle |
| `categories` | array | CoinGecko category names |
| `gt_categories_id` | array | GeckoTerminal category IDs |
| `holders.count` | integer | Total holder count (Beta) |
| `holders.distribution_percentage` | object | Holder concentration by tier (Beta) |
| `holders.last_updated` | string | ISO 8601 timestamp of last holder update |
| `mint_authority` | string \| null | Mint authority address (Solana) |
| `freeze_authority` | string \| null | Freeze authority address (Solana) |
| `is_honeypot` | boolean \| string | Honeypot status |

**Holders distribution tiers by chain:**
- Solana: `top_10`, `11_20`, `21_40`, `rest`
- All other chains: `top_10`, `11_30`, `31_50`, `rest`

**Metadata caveat:** image, websites, description, and socials may be sourced on-chain
and are not vetted by CoinGecko. For reviewed metadata, use
`references/coins.md` → `GET /coins/{id}` or `references/contract.md` →
`GET /coins/{id}/contract/{contract_address}`.

---

## `GET /onchain/simple/networks/{network}/token_price/{addresses}` — Token Price by Token Addresses

| Field | Value |
|---|---|
| Description | Token prices for up to 100 contract addresses |
| Path | `GET /onchain/simple/networks/{network}/token_price/{addresses}` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `network` | string | Yes | Network ID |
| `addresses` | string | Yes | Token contract address(es), comma-separated. Max 100 |
| `include_market_cap` | boolean | No | Include `market_cap_usd` per token. Default: `false` |
| `mcap_fdv_fallback` | boolean | No | Return FDV when market cap is unavailable. Default: `false` |
| `include_24hr_vol` | boolean | No | Include `h24_volume_usd`. Default: `false` |
| `include_24hr_price_change` | boolean | No | Include `h24_price_change_percentage`. Default: `false` |
| `include_total_reserve_in_usd` | boolean | No | Include `total_reserve_in_usd`. Default: `false` |
| `include_inactive_source` | boolean | No | When no active pool found, expand to recently active pools (up to 1 year). Default: `false` |

### Notes
- Price is sourced from GeckoTerminal's routing (best pool by liquidity/activity). For a fixed price source, use `references/onchain-pools.md` → `GET /onchain/networks/{network}/pools/{address}`.
- Unrecognised addresses are silently ignored.

### Example Response
```json
{
  "data": {
    "id": "1ba898f0-eda2-4291-9491-9a5b323f66ef",
    "type": "simple_token_price",
    "attributes": {
      "token_prices": {
        "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": "2289.33"
      },
      "market_cap_usd": {
        "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": "6692452895.78"
      },
      "h24_volume_usd": {
        "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": "965988358.73"
      },
      "h24_price_change_percentage": {
        "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": "3.387"
      },
      "total_reserve_in_usd": {
        "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": "1576179559.95"
      },
      "last_trade_timestamp": {
        "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": 1712534400
      }
    }
  }
}
```

### Response Fields

All attribute maps are keyed by token contract address.

| Field | Type | Description |
|---|---|---|
| `token_prices` | object | Price in USD per address (string values) |
| `market_cap_usd` | object | Market cap in USD per address — present when `include_market_cap=true` |
| `h24_volume_usd` | object | 24hr volume in USD per address — present when `include_24hr_vol=true` |
| `h24_price_change_percentage` | object | 24hr price change % per address — present when `include_24hr_price_change=true` |
| `total_reserve_in_usd` | object | Total reserve in USD per address — present when `include_total_reserve_in_usd=true` |
| `last_trade_timestamp` | object | Most recent trade timestamp per address (integer, UNIX seconds) |

---

## `GET /onchain/networks/{network}/tokens/{address}` — Token Data by Token Address

| Field | Value |
|---|---|
| Description | Single token market data with optional top pool sideload |
| Path | `GET /onchain/networks/{network}/tokens/{address}` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `network` | string | Yes | Network ID |
| `address` | string | Yes | Token contract address |
| `include` | string | No | `top_pools` — sideloads the token's top pool(s) under `included` |
| `include_composition` | boolean | No | Include token balances and liquidity per pool (requires `include=top_pools`). Default: `false` |
| `include_inactive_source` | boolean | No | Expand to recently active pools if no active pool found. Default: `false` |

### Notes
- `included` array (when `include=top_pools`) contains pool objects matching the shared pool shape from `references/onchain-pools.md`. Only the single most liquid pool per token is returned.

### Response Fields

| Field | Type | Description |
|---|---|---|
| `address` | string | Contract address |
| `name` / `symbol` | string | Token name and symbol |
| `decimals` | integer | Token decimals |
| `image_url` | string | Token image URL |
| `coingecko_coin_id` | string \| null | CoinGecko coin ID if listed |
| `total_supply` | string | Raw total supply |
| `normalized_total_supply` | string | Human-readable total supply (adjusted for decimals) |
| `price_usd` | string | Current price in USD |
| `fdv_usd` | string | Fully diluted valuation in USD |
| `total_reserve_in_usd` | string | Total reserve across all pools |
| `volume_usd.h24` | string | 24hr trading volume in USD |
| `market_cap_usd` | string \| null | Market cap — `null` if not verified |
| `last_trade_timestamp` | integer | UNIX timestamp of most recent trade |
| `launchpad_details` | object \| null | Graduation status for bonding curve tokens (see below) |

**`launchpad_details` fields** (present for non-graduated launchpad tokens):

| Field | Type | Description |
|---|---|---|
| `graduation_percentage` | number | % progress toward graduation threshold |
| `completed` | boolean | Whether the token has graduated |
| `completed_at` | string \| null | ISO 8601 graduation timestamp |
| `migrated_destination_pool_address` | string \| null | Pool address post-migration |

---

## `GET /onchain/networks/{network}/tokens/multi/{addresses}` — Tokens Data by Token Addresses

| Field | Value |
|---|---|
| Description | Batch token market data for up to 50 addresses |
| Path | `GET /onchain/networks/{network}/tokens/multi/{addresses}` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `network` | string | Yes | Network ID |
| `addresses` | string | Yes | Comma-separated token contract addresses (max 50) |
| `include` | string | No | `top_pools` |
| `include_composition` | boolean | No | Default: `false` |
| `include_inactive_source` | boolean | No | Default: `false` |

### Notes
- Response `data` is an array; all other fields identical to the single token endpoint above.

---

## `GET /onchain/networks/{network}/tokens/{address}/info` — Token Info by Token Address

| Field | Value |
|---|---|
| Description | Token metadata: name, symbol, image, socials, description, GT Score, holder distribution |
| Path | `GET /onchain/networks/{network}/tokens/{address}/info` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `network` | string | Yes | Network ID |
| `address` | string | Yes | Token contract address |

### Notes
- Response fields follow the [Shared Token Info Shape](#shared-token-info-shape).

---

## `GET /onchain/networks/{network}/pools/{pool_address}/info` — Pool Tokens Info by Pool Address

| Field | Value |
|---|---|
| Description | Token Info objects for both base and quote tokens of a pool |
| Path | `GET /onchain/networks/{network}/pools/{pool_address}/info` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `network` | string | Yes | Network ID |
| `pool_address` | string | Yes | Pool contract address |
| `include` | string | No | `pool` — sideloads the pool object under `included` with `base_token_address`, `quote_token_address`, and community data fields |

### Notes
- For pool market data (price, volume, transactions), use `references/onchain-pools.md` → `GET /onchain/networks/{network}/pools/{address}` instead.
- `holders` data is Beta; supported chains: Solana, EVM (Ethereum, Polygon, BNB, Arbitrum, Optimism, Base), Sui, TON, Ronin.
- Response `data` is an array of two token objects (base and quote token), each following the [Shared Token Info Shape](#shared-token-info-shape).

---

## `GET /onchain/networks/{network}/tokens/{token_address}/pools` — Top Pools by Token Address

| Field | Value |
|---|---|
| Description | Pools for a given token, ranked by combined liquidity and 24hr volume |
| Path | `GET /onchain/networks/{network}/tokens/{token_address}/pools` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `network` | string | Yes | Network ID |
| `token_address` | string | Yes | Token contract address |
| `include` | string | No | `base_token`, `quote_token`, `dex` (comma-separated) |
| `page` | integer | No | Default: `1` |
| `sort` | string | No | `h24_volume_usd_liquidity_desc` (default), `h24_tx_count_desc`, `h24_volume_usd_desc` |
| `include_gt_community_data` | boolean | No | Default: `false` |
| `include_inactive_source` | boolean | No | Expand to recently active pools. Default: `false` |

### Notes
- Max 20 pools per page.
- Pool objects follow the shared pool shape from `references/onchain-pools.md`, with an additional `last_trade_timestamp` field.

---

## `GET /onchain/tokens/info_recently_updated` — Most Recently Updated Tokens

| Field | Value |
|---|---|
| Description | Up to 100 tokens ordered by most recent metadata update |
| Path | `GET /onchain/tokens/info_recently_updated` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `include` | string | No | `network` — sideloads network object under `included` |
| `network` | string | No | Filter to a specific network ID |

### Notes
- Returns up to 100 tokens across all networks, or filtered to one network.
- Token objects are a subset of the full Token Info shape — full socials and holder data are not included.

### Response Fields

| Field | Type | Description |
|---|---|---|
| `address` | string | Token contract address |
| `name` | string | Token name |
| `symbol` | string | Token symbol |
| `image_url` | string | Token image URL |
| `coingecko_coin_id` | string \| null | CoinGecko coin ID if listed |
| `websites` | array | Official website URLs |
| `description` | string | Token description |
| `gt_score` | number | GeckoTerminal score (0–100) |
| `metadata_updated_at` | string | ISO 8601 timestamp of most recent metadata update |

---

## `GET /onchain/networks/{network}/tokens/{address}/top_holders` — Top Token Holders

| Field | Value |
|---|---|
| Description | Top holders by token balance for a given token address |
| Path | `GET /onchain/networks/{network}/tokens/{address}/top_holders` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `network` | string | Yes | Network ID |
| `address` | string | Yes | Token contract address |
| `holders` | string | No | Number of holders to return, or `max`. Default: `10`. Max: 50 (non-Solana), 40 (Solana) |
| `include_pnl_details` | boolean | No | Include PnL fields per holder. Default: `false` |

### Notes
- Beta — data quality and coverage are still improving.
- Supported chains: Solana, EVM (Ethereum, Polygon, BNB, Arbitrum, Optimism, Base), Sui, TON, Ronin.

### Example Response
```json
{
  "data": {
    "id": "base_0x6921b130...",
    "type": "top_holder",
    "attributes": {
      "last_updated_at": "2025-03-26T09:15:26.926Z",
      "holders": [
        {
          "rank": 1,
          "address": "0x56bbe420...",
          "label": null,
          "amount": "9703812154.0",
          "percentage": "14.3507",
          "value": "1016009.26",
          "average_buy_price_usd": null,
          "total_buy_count": null,
          "total_sell_count": null,
          "unrealized_pnl_usd": null,
          "unrealized_pnl_percentage": null,
          "realized_pnl_usd": null,
          "realized_pnl_percentage": null,
          "explorer_url": "https://basescan.org/address/0x56bbe420..."
        }
      ]
    }
  }
}
```

### Response Fields

| Field | Type | Description |
|---|---|---|
| `rank` | number | Holder rank by token amount |
| `address` | string | Wallet address |
| `label` | string \| null | ENS or known label |
| `amount` | string | Raw token amount held |
| `percentage` | string | % of total supply held |
| `value` | string | USD value of holdings |
| `average_buy_price_usd` | string \| null | Average buy price (requires `include_pnl_details=true`) |
| `total_buy_count` / `total_sell_count` | number \| null | Trade counts (requires `include_pnl_details=true`) |
| `unrealized_pnl_usd` / `unrealized_pnl_percentage` | string \| null | Unrealized PnL (requires `include_pnl_details=true`) |
| `realized_pnl_usd` / `realized_pnl_percentage` | string \| null | Realized PnL (requires `include_pnl_details=true`) |
| `explorer_url` | string | Block explorer URL for the wallet |

---

## `GET /onchain/networks/{network}/tokens/{token_address}/holders_chart` — Historical Token Holders Chart

| Field | Value |
|---|---|
| Description | Time-series holder count snapshots for a token |
| Path | `GET /onchain/networks/{network}/tokens/{token_address}/holders_chart` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `network` | string | Yes | Network ID |
| `token_address` | string | Yes | Token contract address |
| `days` | string | No | `7` (default), `30`, `max` |

### Notes
- Beta — data quality and coverage are still improving.
- Supported chains: same as Top Token Holders above.
- Granularity by `days`: `7` → all data points; `30` → daily; `max` → weekly.

### Example Response
```json
{
  "data": {
    "id": "eb8f8786-...",
    "type": "token_holders_snapshot",
    "attributes": {
      "token_holders_list": [
        ["2025-05-29T10:44:50.813Z", 7705761],
        ["2025-05-29T11:45:03.137Z", 7705748]
      ]
    }
  },
  "meta": {
    "token": {
      "address": "0xdac17f958d2ee523a2206206994597c13d831ec7",
      "name": "Tether USD",
      "symbol": "USDT",
      "coingecko_coin_id": "tether"
    }
  }
}
```

### Response Fields

| Field | Type | Description |
|---|---|---|
| `token_holders_list` | array | Array of `[ISO 8601 timestamp (string), holder count (integer)]` pairs |
| `meta.token.address` | string | Token contract address |
| `meta.token.name` | string | Token name |
| `meta.token.symbol` | string | Token symbol |
| `meta.token.coingecko_coin_id` | string \| null | CoinGecko coin ID if listed |

---

## `GET /onchain/networks/{network_id}/tokens/{token_address}/top_traders` — Top Token Traders

| Field | Value |
|---|---|
| Description | Top traders by PnL or volume for a given token |
| Path | `GET /onchain/networks/{network_id}/tokens/{token_address}/top_traders` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `network_id` | string | Yes | Network ID |
| `token_address` | string | Yes | Token contract address |
| `traders` | string | No | Number of traders to return, or `max`. Default: `10`. Max: `50` |
| `sort` | string | No | `realized_pnl_usd_desc` (default), `unrealized_pnl_usd_desc`, `total_buy_usd_desc`, `total_sell_usd_desc` |
| `include_address_label` | boolean | No | Include address label data. Default: `false` |

### Notes
- Beta — data quality and coverage are still improving.
- Only tokens created after 1 September 2023 are supported.
- Stablecoins and wrapped native tokens (e.g. wSOL, wETH) are not supported.

### Response Fields

| Field | Type | Description |
|---|---|---|
| `address` | string | Wallet address |
| `name` | string \| null | Display name (e.g. Twitter handle) |
| `label` | string \| null | ENS or known label (requires `include_address_label=true`) |
| `type` | string | Wallet type classification |
| `realized_pnl_usd` | string | Realized profit/loss in USD |
| `unrealized_pnl_usd` | string | Unrealized profit/loss in USD |
| `token_balance` | string | Current token balance |
| `average_buy_price_usd` | string | Average buy price in USD |
| `average_sell_price_usd` | string | Average sell price in USD |
| `total_buy_count` / `total_sell_count` | integer | Number of buy/sell transactions |
| `total_buy_token_amount` / `total_sell_token_amount` | string | Total token volume bought/sold |
| `total_buy_usd` / `total_sell_usd` | string | Total USD volume bought/sold |
| `explorer_url` | string | Block explorer URL for the wallet |