# CoinGecko API — Onchain Networks & DEXes Reference

GeckoTerminal reference data for supported networks and DEXes. Load this file first
before any other onchain endpoint — network IDs and DEX IDs from these endpoints are
required params throughout `references/onchain-pools.md`,
`references/onchain-tokens.md`, and `references/onchain-ohlcv-trades.md`.

---

## `GET /onchain/networks` — Supported Networks List

| Field | Value |
|---|---|
| Description | Query all networks supported on GeckoTerminal |
| Path | `GET /onchain/networks` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `page` | integer | No | Page number. Default: `1` |

### Notes
- Results are paginated. Iterate `page` to retrieve all networks.
- `data[].id` is the `network` path param used in all other onchain endpoints.
- `data[].attributes.coingecko_asset_platform_id` maps to the CoinGecko asset
  platform ID used in `references/asset-platforms.md` and `references/contract.md`.

### Example Response
```json
{
  "data": [
    {
      "id": "eth",
      "type": "network",
      "attributes": {
        "name": "Ethereum",
        "coingecko_asset_platform_id": "ethereum"
      }
    },
    {
      "id": "bsc",
      "type": "network",
      "attributes": {
        "name": "BNB Chain",
        "coingecko_asset_platform_id": "binance-smart-chain"
      }
    },
    {
      "id": "polygon_pos",
      "type": "network",
      "attributes": {
        "name": "Polygon POS",
        "coingecko_asset_platform_id": "polygon-pos"
      }
    }
  ]
}
```

### Response Fields

| Field | Description |
|---|---|
| `data[].id` | Network ID — use as `{network}` in all onchain path params |
| `data[].type` | `"network"` |
| `data[].attributes.name` | Human-readable network name |
| `data[].attributes.coingecko_asset_platform_id` | Corresponding CoinGecko asset platform ID (may be `null` if no mapping exists) |

---

## `GET /onchain/networks/{network}/dexes` — Supported DEXes List by Network

| Field | Value |
|---|---|
| Description | Query all DEXes supported on a given network on GeckoTerminal |
| Path | `GET /onchain/networks/{network}/dexes` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `network` | string | Yes | Network ID — refer to `GET /onchain/networks` above |
| `page` | integer | No | Page number. Default: `1` |

### Notes
- Results are paginated. Iterate `page` to retrieve all DEXes for a network.
- `data[].id` is the `dex` path param used in pool endpoints — see
  `references/onchain-pools.md` → `GET /onchain/networks/{network}/dexes/{dex}/pools`.

### Example Response
```json
{
  "data": [
    {
      "id": "uniswap_v2",
      "type": "dex",
      "attributes": { "name": "Uniswap V2" }
    },
    {
      "id": "uniswap_v3",
      "type": "dex",
      "attributes": { "name": "Uniswap V3" }
    }
  ]
}
```

### Response Fields

| Field | Description |
|---|---|
| `data[].id` | DEX ID — use as `{dex}` in pool endpoints |
| `data[].type` | `"dex"` |
| `data[].attributes.name` | Human-readable DEX name |