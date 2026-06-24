# CoinGecko API — Onchain OHLCV & Trades Reference

Historical OHLCV candlestick data and recent trade records via GeckoTerminal. Load
this file for any request involving onchain price charts, candlestick data, or
individual trade history.

Requires network IDs — load `references/onchain-networks.md` first if unknown.

---

## OHLCV Endpoints

### `GET /onchain/networks/{network}/pools/{pool_address}/ohlcv/{timeframe}` — Pool OHLCV

OHLCV data for a specific pool. Use when a precise price source is required.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `network` | string | Yes | Network ID |
| `pool_address` | string | Yes | Pool contract address |
| `timeframe` | string | Yes | `day`, `hour`, `minute`, or `second` |
| `aggregate` | string | No | Candle size per timeframe — `day`: `1`; `hour`: `1`, `4`, `12`; `minute`: `1`, `5`, `15`; `second`: `1`, `15`, `30`. Default: `1` |
| `before_timestamp` | integer | No | Return data before this UNIX timestamp (seconds). Use for paginating historical data |
| `limit` | integer | No | Number of candles to return. Max: `1000`. Default: `100` |
| `currency` | string | No | `usd` (default) or `token` (denominate OHLCV in quote token) |
| `token` | string | No | `base` (default), `quote`, or a token contract address. Use to invert the chart perspective |
| `include_empty_intervals` | boolean | No | Default: `false` (see notes below) |

---

### `GET /onchain/networks/{network}/tokens/{token_address}/ohlcv/{timeframe}` — Token OHLCV

Same parameters and response shape as Pool OHLCV, sourced from the token's most
liquid pool. Supports an additional parameter:

| Parameter | Type | Required | Description |
|---|---|---|---|
| `network` | string | Yes | Network ID |
| `token_address` | string | Yes | Token contract address |
| `timeframe` | string | Yes | `day`, `hour`, `minute`, or `second` |
| `aggregate` | string | No | Same values as Pool OHLCV. Default: `1` |
| `before_timestamp` | integer | No | UNIX timestamp (seconds) upper bound |
| `limit` | integer | No | Max: `1000`. Default: `100` |
| `currency` | string | No | `usd` (default) or `token` |
| `include_empty_intervals` | boolean | No | Default: `false` |
| `include_inactive_source` | boolean | No | Expand to recently active pools if no active pool found. Default: `false` |

To verify which pool is being used, call `references/onchain-tokens.md` →
`GET /onchain/networks/{network}/tokens/{token_address}/pools` first.

---

### OHLCV Notes

- **Historical depth**: Higher-tier plans can access data from September 2021 to present. Each request covers a maximum range of 6 months. Use `before_timestamp` in successive requests to retrieve older data.
- **Skipped intervals**: By default (`include_empty_intervals=false`), intervals with no swaps are omitted. Higher-granularity timeframes (e.g. 1 minute) skip intervals more frequently.
- **Empty interval fill** (when `include_empty_intervals=true`): OHLC is set to the previous interval's close price (O = H = L = C = prev_close); volume is set to `0`.
- Timestamps are UNIX epoch seconds.

### OHLCV Response

```json
{
  "data": {
    "id": "bc786a99-7205-4c80-aaa1-b9634d97c926",
    "type": "ohlcv_request_response",
    "attributes": {
      "ohlcv_list": [
        [1712534400, 3454.62, 3660.86, 3417.92, 3660.86, 306823.28],
        [1712448000, 3362.60, 3455.29, 3352.95, 3454.62, 242144.86]
      ]
    }
  },
  "meta": {
    "base": {
      "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
      "name": "Wrapped Ether",
      "symbol": "WETH",
      "coingecko_coin_id": "weth"
    },
    "quote": {
      "address": "0xdac17f958d2ee523a2206206994597c13d831ec7",
      "name": "Tether USD",
      "symbol": "USDT",
      "coingecko_coin_id": "tether"
    }
  }
}
```

Each entry in `ohlcv_list` is a 6-element array: `[timestamp, open, high, low, close, volume]`. All values are numbers. `meta.base` and `meta.quote` identify the pool's tokens.

---

## Trades Endpoints

### `GET /onchain/networks/{network}/pools/{pool_address}/trades` — Pool Trades

Last 300 trades within the past 24 hours for a specific pool.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `network` | string | Yes | Network ID |
| `pool_address` | string | Yes | Pool contract address |
| `trade_volume_in_usd_greater_than` | number | No | Minimum trade volume filter in USD. Default: `0` |
| `token` | string | No | `base` (default), `quote`, or a token contract address. Determines the chart perspective (buy/sell direction) |

---

### `GET /onchain/networks/{network}/tokens/{token_address}/trades` — Token Trades

Last 300 trades within the past 24 hours across **all pools** for a token. Includes
`pool_address` and `pool_dex` fields not present in the pool trades endpoint.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `network` | string | Yes | Network ID |
| `token_address` | string | Yes | Token contract address |
| `trade_volume_in_usd_greater_than` | number | No | Minimum trade volume filter in USD. Default: `0` |

---

### Trades Response

```json
{
  "data": [
    {
      "id": "eth_19612255_0x0b8ac5a..._158_1712595165",
      "type": "trade",
      "attributes": {
        "block_number": 19612255,
        "tx_hash": "0x0b8ac5a16c291832...",
        "tx_from_address": "0x42c037c594eefeca...",
        "from_token_amount": "1.51717616246451",
        "to_token_amount": "5535.099061",
        "price_from_in_currency_token": "1.0",
        "price_to_in_currency_token": "0.000274100995437363",
        "price_from_in_usd": "3656.8970003075",
        "price_to_in_usd": "1.00235910799619",
        "block_timestamp": "2024-04-08T16:52:35Z",
        "kind": "buy",
        "volume_in_usd": "5548.15695745452",
        "from_token_address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
        "to_token_address": "0xdac17f958d2ee523a2206206994597c13d831ec7"
      }
    }
  ]
}
```

### Trade Attribute Fields

| Field | Type | Description |
|---|---|---|
| `block_number` | integer | Block number containing the trade |
| `tx_hash` | string | Transaction hash |
| `tx_from_address` | string | Wallet address that initiated the transaction |
| `from_token_amount` | string | Amount of token sent |
| `to_token_amount` | string | Amount of token received |
| `price_from_in_currency_token` | string | Price of the from-token denominated in the currency token |
| `price_to_in_currency_token` | string | Price of the to-token denominated in the currency token |
| `price_from_in_usd` | string | Price of the from-token in USD |
| `price_to_in_usd` | string | Price of the to-token in USD |
| `block_timestamp` | string | ISO 8601 timestamp of the block |
| `kind` | string | Trade direction: `buy` or `sell` |
| `volume_in_usd` | string | Trade volume in USD |
| `from_token_address` | string | Contract address of the token sent |
| `to_token_address` | string | Contract address of the token received |
| `pool_address` | string | Pool contract address (**token trades only**) |
| `pool_dex` | string | DEX ID of the pool (**token trades only**) |