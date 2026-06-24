# CoinGecko API — NFTs Reference

Covers NFT collection discovery, market data, tickers, and historical charts. Load
this file when the user asks about NFTs, NFT floor prices, NFT volume, NFT market cap,
or NFT collection data.

NFT collection IDs can be resolved via `GET /nfts/list` below. Asset platform IDs
(for contract address endpoints) can be resolved via `references/asset-platforms.md`
→ `GET /asset_platforms` with `filter=nft`.

**Solana NFTs and Art Blocks** must be queried by NFT ID (not contract address). The
contract address endpoints do not support them.

---

## `GET /nfts/list` — NFTs List (ID Map)

| Field | Value |
|---|---|
| Description | Query all supported NFT collections with ID, contract address, asset platform, name, and symbol |
| Path | `GET /nfts/list` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `order` | string | No | Sort order. Options: `h24_volume_usd_asc/desc`, `h24_volume_native_asc/desc`, `floor_price_native_asc/desc`, `market_cap_native_asc/desc`, `market_cap_usd_asc/desc` |
| `per_page` | number | No | Results per page. Max: `250` |
| `page` | number | No | Page number |

### Example Response
```json
[
  {
    "id": "bored-ape-yacht-club",
    "contract_address": "0xbc4ca0eda7647a8ab7c2061c2e118a18a936f13d",
    "name": "Bored Ape Yacht Club",
    "asset_platform_id": "ethereum",
    "symbol": "BAYC"
  }
]
```

### Response Fields

| Field | Description |
|---|---|
| `id` | NFT collection ID — use in all NFT ID-based endpoints |
| `contract_address` | Collection contract address |
| `name` | Collection name |
| `asset_platform_id` | Asset platform ID — use in contract address endpoints |
| `symbol` | Collection symbol |

---

## `GET /nfts/{id}` — NFTs Collection Data by ID

| Field | Value |
|---|---|
| Description | Query full NFT collection data including floor price, market cap, volume, and stats |
| Path | `GET /nfts/{id}` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes (path) | NFT collection ID. Refer to `GET /nfts/list` above |

### Notes
- Supports all collections including Solana NFTs and Art Blocks.

### Example Response
```json
{
  "id": "pudgy-penguins",
  "contract_address": "0xBd3531dA5CF5857e7CfAA92426877b022e612cf8",
  "asset_platform_id": "ethereum",
  "name": "Pudgy Penguins",
  "symbol": "PPG",
  "native_currency": "ethereum",
  "native_currency_symbol": "ETH",
  "market_cap_rank": 3,
  "floor_price": { "native_currency": 12.5, "usd": 42317 },
  "market_cap": { "native_currency": 111100, "usd": 376114941 },
  "volume_24h": { "native_currency": 429.88, "usd": 1455314 },
  "total_supply": 8888,
  "ath": { "native_currency": 22.9, "usd": 67535 },
  "ath_date": { "native_currency": "2024-02-17T09:25:05.056Z", "usd": "2024-02-29T11:45:08.150Z" }
}
```

### Response Fields

| Field | Description |
|---|---|
| `id` | NFT collection ID |
| `contract_address` | Contract address |
| `asset_platform_id` | Asset platform ID |
| `name` | Collection name |
| `symbol` | Collection symbol |
| `image.small`, `image.small_2x` | Collection logo URLs |
| `banner_image` | Banner image URL |
| `description` | Collection description |
| `native_currency` | Native pricing currency name |
| `native_currency_symbol` | Native pricing currency symbol |
| `market_cap_rank` | CoinGecko market cap rank |
| `floor_price.native_currency`, `floor_price.usd` | Current floor price |
| `market_cap.native_currency`, `market_cap.usd` | Market cap |
| `volume_24h.native_currency`, `volume_24h.usd` | 24hr trading volume |
| `floor_price_in_usd_24h_percentage_change` | Floor price USD 24hr change % |
| `floor_price_24h_percentage_change` | Floor price 24hr change % in USD and native currency |
| `floor_price_7d/14d/30d/60d/1y_percentage_change` | Floor price change over longer timeframes in USD and native currency |
| `market_cap_24h_percentage_change` | Market cap 24hr change % |
| `volume_24h_percentage_change` | Volume 24hr change % |
| `number_of_unique_addresses` | Number of unique owner addresses |
| `number_of_unique_addresses_24h_percentage_change` | Unique addresses 24hr change % |
| `total_supply` | Total token supply |
| `one_day_sales` | Number of sales in the past 24hr |
| `one_day_sales_24h_percentage_change` | Sales count 24hr change % |
| `one_day_average_sale_price` | Average sale price in the past 24hr (native currency) |
| `one_day_average_sale_price_24h_percentage_change` | Average sale price 24hr change % |
| `links.homepage`, `links.twitter`, `links.discord` | Collection links |
| `explorers` | Array of `{name, link}` block explorer entries |
| `user_favorites_count` | CoinGecko user favorites count |
| `ath.native_currency`, `ath.usd` | All-time high floor price |
| `ath_change_percentage` | Change from ATH in USD and native currency |
| `ath_date` | ATH date in USD and native currency |

---

## `GET /nfts/{asset_platform_id}/contract/{contract_address}` — NFTs Collection Data by Contract Address

| Field | Value |
|---|---|
| Description | Query full NFT collection data using asset platform and contract address |
| Path | `GET /nfts/{asset_platform_id}/contract/{contract_address}` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `asset_platform_id` | string | Yes (path) | Asset platform ID. Refer to `references/asset-platforms.md` → `GET /asset_platforms` with `filter=nft` |
| `contract_address` | string | Yes (path) | NFT collection contract address |

### Notes
- Does **not** support Solana NFTs or Art Blocks — use `GET /nfts/{id}` instead.
- Response schema is identical to `GET /nfts/{id}`. See response fields there.

---

## `GET /nfts/markets` — NFTs List with Market Data

| Field | Value |
|---|---|
| Description | Query all NFT collections with current market data, sortable and paginated |
| Path | `GET /nfts/markets` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `asset_platform_id` | string | No | Filter by blockchain. Refer to `references/asset-platforms.md` → `GET /asset_platforms` with `filter=nft` |
| `order` | string | No | Sort order. Default: `market_cap_usd_desc`. Options: `h24_volume_native_asc/desc`, `h24_volume_usd_asc/desc`, `market_cap_usd_asc/desc` |
| `per_page` | number | No | Results per page. Default: `100`. Max: `250` |
| `page` | number | No | Page number. Default: `1` |

### Response Fields

Same fields as `GET /nfts/{id}`, excluding `links`, `explorers`, `ath`, `ath_change_percentage`, `ath_date`, `floor_price_7d/14d/30d/60d/1y_percentage_change`, and `user_favorites_count`.

---

## `GET /nfts/{id}/tickers` — NFTs Collection Tickers by ID

| Field | Value |
|---|---|
| Description | Query per-marketplace floor price and 24hr volume for an NFT collection |
| Path | `GET /nfts/{id}/tickers` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes (path) | NFT collection ID. Refer to `GET /nfts/list` above |

### Example Response
```json
{
  "tickers": [
    {
      "floor_price_in_native_currency": 12.17,
      "h24_volume_in_native_currency": 402.37,
      "native_currency": "ethereum",
      "native_currency_symbol": "ETH",
      "updated_at": "2024-04-08T12:28:11.797Z",
      "nft_marketplace_id": "blur",
      "name": "Blur",
      "image": "https://assets.coingecko.com/nft_marketplaces/images/20/small/blur_logo.jpg",
      "nft_collection_url": "https://blur.io/collection/pudgypenguins"
    }
  ]
}
```

### Response Fields

| Field | Description |
|---|---|
| `tickers[].floor_price_in_native_currency` | Floor price on this marketplace in native currency |
| `tickers[].h24_volume_in_native_currency` | 24hr volume on this marketplace in native currency |
| `tickers[].native_currency` | Native currency name |
| `tickers[].native_currency_symbol` | Native currency symbol |
| `tickers[].updated_at` | Last updated timestamp (ISO 8601) |
| `tickers[].nft_marketplace_id` | Marketplace ID |
| `tickers[].name` | Marketplace name |
| `tickers[].image` | Marketplace logo URL |
| `tickers[].nft_collection_url` | Collection URL on this marketplace |

---

## NFT Historical Chart Endpoints

Both chart endpoints return the same response shape. Granularity is automatic:
1–14 days → 5-minutely; 15 days and above → daily (00:00 UTC).

### Chart Response Fields

| Field | Description |
|---|---|
| `floor_price_usd` | Array of `[UNIX timestamp (ms), floor price in USD]` pairs |
| `floor_price_native` | Array of `[UNIX timestamp (ms), floor price in native currency]` pairs |
| `h24_volume_usd` | Array of `[UNIX timestamp (ms), 24hr volume in USD]` pairs |
| `h24_volume_native` | Array of `[UNIX timestamp (ms), 24hr volume in native currency]` pairs |
| `market_cap_usd` | Array of `[UNIX timestamp (ms), market cap in USD]` pairs |
| `market_cap_native` | Array of `[UNIX timestamp (ms), market cap in native currency]` pairs |

---

## `GET /nfts/{id}/market_chart` — NFTs Collection Historical Chart Data by ID

| Field | Value |
|---|---|
| Description | Query historical floor price, market cap, and 24hr volume time-series for an NFT collection |
| Path | `GET /nfts/{id}/market_chart` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes (path) | NFT collection ID. Refer to `GET /nfts/list` above |
| `days` | string | Yes | Number of days ago — any integer or `max` |

### Notes
- Supports all collections including Solana NFTs and Art Blocks.

---

## `GET /nfts/{asset_platform_id}/contract/{contract_address}/market_chart` — NFTs Collection Historical Chart Data by Contract Address

| Field | Value |
|---|---|
| Description | Query historical floor price, market cap, and 24hr volume time-series using asset platform and contract address |
| Path | `GET /nfts/{asset_platform_id}/contract/{contract_address}/market_chart` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `asset_platform_id` | string | Yes (path) | Asset platform ID. Refer to `references/asset-platforms.md` → `GET /asset_platforms` with `filter=nft` |
| `contract_address` | string | Yes (path) | NFT collection contract address |
| `days` | string | Yes | Number of days ago — any integer or `max` |

### Notes
- Does **not** support Solana NFTs or Art Blocks — use `GET /nfts/{id}/market_chart` instead.