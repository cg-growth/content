# CoinGecko API — Asset Platforms Reference

Covers asset platform ID maps and token lists. Load this file when the user needs to
resolve an asset platform ID (e.g. `ethereum`, `polygon-pos`) for use in contract
address endpoints, or when they ask for a list of tokens on a blockchain network.

Asset platform IDs are required by endpoints in `references/contract.md` and
`references/nfts.md`.

**Note on GeckoTerminal network IDs:** CoinGecko asset platform IDs (e.g. `ethereum`,
`polygon-pos`) differ in format from GeckoTerminal network IDs (e.g. `eth`, `polygon_pos`).
The mapping between the two is available via `references/onchain-networks.md` →
`GET /onchain/networks` — each network object includes a `coingecko_asset_platform_id` field.
Do not use CoinGecko asset platform IDs directly in GeckoTerminal onchain endpoints.

---

## `GET /asset_platforms` — Asset Platforms List (ID Map)

| Field | Value |
|---|---|
| Description | Query all asset platforms on CoinGecko, including their IDs and chain metadata |
| Path | `GET /asset_platforms` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `filter` | string | No | Filter results: `nft` returns only NFT-supported platforms |

### Notes
- Use this endpoint to resolve asset platform IDs for contract address endpoints and NFT endpoints.

### Example Response
```json
[
  {
    "id": "polygon-pos",
    "chain_identifier": 137,
    "name": "Polygon POS",
    "shortname": "MATIC",
    "native_coin_id": "matic-network",
    "image": {
      "thumb": "https://coin-images.coingecko.com/asset_platforms/images/15/thumb/polygon_pos.png",
      "small": "https://coin-images.coingecko.com/asset_platforms/images/15/small/polygon_pos.png",
      "large": "https://coin-images.coingecko.com/asset_platforms/images/15/large/polygon_pos.png"
    }
  }
]
```

### Response Fields

| Field | Description |
|---|---|
| `id` | Asset platform ID — use this in contract address and NFT endpoints |
| `chain_identifier` | Chainlist chain ID (EVM chains only; `null` for non-EVM) |
| `name` | Full chain name |
| `shortname` | Short chain name or ticker |
| `native_coin_id` | CoinGecko coin ID of the chain's native currency |
| `image.thumb/small/large` | Platform logo at various sizes |

---

## `GET /token_lists/{asset_platform_id}/all.json` — Token Lists by Asset Platform ID

| Field | Value |
|---|---|
| Description | Get the full token list for a blockchain network in Ethereum token list standard format |
| Path | `GET /token_lists/{asset_platform_id}/all.json` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `asset_platform_id` | string | Yes (path) | Asset platform ID. Refer to `GET /asset_platforms` above |

### Notes
- Only tokens whose contract addresses have been verified by the CoinGecko team are included.
- Response conforms to the [Ethereum token list standard](https://tokenlists.org/).

### Example Response
```json
{
  "name": "CoinGecko",
  "logoURI": "https://static.coingecko.com/s/thumbnail-007177f3eca19695592f0b8b0eabbdae282b54154e1be912285c9034ea6cbaf2.png",
  "keywords": ["defi"],
  "timestamp": "2024-04-08T14:02:47.028+00:00",
  "tokens": [
    {
      "chainId": 1,
      "address": "0xd2877702675e6ceb975b4a1dff9fb7baf4c91ea9",
      "name": "Wrapped Terra Classic",
      "symbol": "LUNC",
      "decimals": 18,
      "logoURI": "https://assets.coingecko.com/coins/images/13628/thumb/wluna.png"
    }
  ]
}
```

### Response Fields

| Field | Description |
|---|---|
| `name` | List name |
| `logoURI` | CoinGecko logo URL |
| `keywords` | List category tags |
| `timestamp` | Last updated timestamp (ISO 8601) |
| `tokens[].chainId` | Chainlist chain ID |
| `tokens[].address` | Token contract address |
| `tokens[].name` | Token name |
| `tokens[].symbol` | Token symbol |
| `tokens[].decimals` | Token decimal precision |
| `tokens[].logoURI` | Token logo image URL |