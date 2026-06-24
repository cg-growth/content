# CoinGecko API — Utilities Reference

Covers API status, key usage, supported currencies, search, trending, and exchange
rates. Load this file when the user needs to: check API status or key details, resolve
a coin/exchange/NFT/category ID by name, find trending coins, or convert BTC-denominated
values to other currencies.

---

## `GET /ping` — Check API Server Status

| Field | Value |
|---|---|
| Description | Check whether the CoinGecko API server is online |
| Path | `GET /ping` |

### Parameters

None.

### Example Response
```json
{ "gecko_says": "(V3) To the Moon!" }
```

### Response Fields

| Field | Description |
|---|---|
| `gecko_says` | Status message. Any response indicates the server is up |

---

## `GET /key` — API Usage

| Field | Value |
|---|---|
| Description | Monitor API key usage including rate limits, monthly credits, and remaining credits |
| Path | `GET /key` |

### Parameters

None.

### Notes
- For a full usage overview, visit https://www.coingecko.com/en/developers/dashboard.
- `api_key_rate_limit_request_per_minute` and `api_key_monthly_call_credit` reflect
  any custom limits set on the specific API key used, which may differ from the
  plan-level defaults.

### Example Response
```json
{
  "plan": "Other",
  "rate_limit_request_per_minute": 1000,
  "monthly_call_credit": 1000000,
  "current_total_monthly_calls": 104,
  "current_remaining_monthly_calls": 999896,
  "api_key_rate_limit_request_per_minute": 500,
  "api_key_monthly_call_credit": 500000
}
```

### Response Fields

| Field | Description |
|---|---|
| `plan` | API plan name |
| `rate_limit_request_per_minute` | Plan-level rate limit (requests per minute) |
| `monthly_call_credit` | Plan-level monthly credit allowance |
| `current_total_monthly_calls` | Total API calls made this month |
| `current_remaining_monthly_calls` | Remaining monthly credits |
| `api_key_rate_limit_request_per_minute` | Rate limit for this specific API key |
| `api_key_monthly_call_credit` | Monthly credit limit for this specific API key |

---

## `GET /simple/supported_vs_currencies` — Supported Currencies List

| Field | Value |
|---|---|
| Description | Query all currencies supported as `vs_currency` or `vs_currencies` params across endpoints |
| Path | `GET /simple/supported_vs_currencies` |

### Parameters

None.

### Notes
- Use values from this endpoint wherever an endpoint accepts `vs_currency` or `vs_currencies`.
- Includes fiat currencies (e.g. `usd`, `eur`, `jpy`), cryptocurrencies (e.g. `btc`, `eth`, `sol`), and commodities (e.g. `xau`, `xag`).

### Example Response
```json
["btc", "eth", "usd", "eur", "jpy", "gbp", "aud", "xau", "xag", "sats"]
```

---

## `GET /search` — Search Queries

| Field | Value |
|---|---|
| Description | Search for coins, exchanges, categories, and NFTs by name or symbol |
| Path | `GET /search` |

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `query` | string | Yes | Search term (coin name, symbol, exchange name, etc.) |

### Notes
- Results are sorted by market cap descending.
- Use this endpoint to resolve a coin ID when the target coin is known by name or
  symbol. For the full ID list, use `references/coins.md` → `GET /coins/list`.

### Example Response
```json
{
  "coins": [
    {
      "id": "ethereum",
      "name": "Ethereum",
      "api_symbol": "ethereum",
      "symbol": "ETH",
      "market_cap_rank": 2,
      "thumb": "https://assets.coingecko.com/coins/images/279/thumb/ethereum.png",
      "large": "https://assets.coingecko.com/coins/images/279/large/ethereum.png"
    }
  ],
  "exchanges": [
    {
      "id": "uniswap_v3",
      "name": "Uniswap V3 (Ethereum)",
      "market_type": "spot",
      "thumb": "https://assets.coingecko.com/markets/images/665/thumb/uniswap-v3.png",
      "large": "https://assets.coingecko.com/markets/images/665/large/uniswap-v3.png"
    }
  ],
  "categories": [
    { "id": "ethereum-ecosystem", "name": "Ethereum Ecosystem" }
  ],
  "nfts": [
    {
      "id": "ens-ethereum-name-service",
      "name": "ENS: Ethereum Name Service",
      "symbol": "ENS",
      "thumb": "https://assets.coingecko.com/nft_contracts/images/373/thumb/ens-ethereum-name-service.png"
    }
  ],
  "icos": []
}
```

### Response Fields

| Field | Description |
|---|---|
| `coins[].id` | CoinGecko coin ID |
| `coins[].name` | Coin name |
| `coins[].api_symbol` | API symbol (same as `id` in most cases) |
| `coins[].symbol` | Ticker symbol |
| `coins[].market_cap_rank` | Market cap rank |
| `coins[].thumb`, `coins[].large` | Coin image URLs |
| `exchanges[].id` | Exchange ID |
| `exchanges[].name` | Exchange name |
| `exchanges[].market_type` | Market type (e.g. `spot`) |
| `exchanges[].thumb`, `exchanges[].large` | Exchange image URLs |
| `categories[].id` | Category ID |
| `categories[].name` | Category name |
| `nfts[].id` | NFT collection ID |
| `nfts[].name` | NFT collection name |
| `nfts[].symbol` | NFT collection symbol |
| `nfts[].thumb` | NFT collection thumbnail URL |

---

## `GET /search/trending` — Trending Search List

| Field | Value |
|---|---|
| Description | Query the top 7 trending coins, top 3 trending NFTs, and top 6 trending categories on CoinGecko in the last 24 hours |
| Path | `GET /search/trending` |

### Parameters

None.

### Example Response
```json
{
  "coins": [
    {
      "item": {
        "id": "solana",
        "coin_id": 4128,
        "name": "Solana",
        "symbol": "SOL",
        "market_cap_rank": 5,
        "thumb": "https://assets.coingecko.com/coins/images/4128/thumb/solana.png",
        "small": "https://assets.coingecko.com/coins/images/4128/small/solana.png",
        "large": "https://assets.coingecko.com/coins/images/4128/large/solana.png",
        "slug": "solana",
        "price_btc": 0.00213,
        "score": 0,
        "data": {
          "price": 185.23,
          "price_btc": "0.00213",
          "price_change_percentage_24h": { "usd": 2.5 },
          "market_cap": "87B",
          "market_cap_btc": "1003456",
          "total_volume": "3.2B",
          "total_volume_btc": "37500",
          "sparkline": "https://www.coingecko.com/coins/4128/sparkline.svg",
          "content": null
        }
      }
    }
  ],
  "nfts": [
    {
      "id": "pudgy-penguins",
      "name": "Pudgy Penguins",
      "symbol": "PPG",
      "thumb": "https://coin-images.coingecko.com/nft_contracts/images/38/small/pudgy.jpg",
      "nft_contract_id": 38,
      "native_currency_symbol": "ETH",
      "floor_price_in_native_currency": 12.5,
      "floor_price_24h_percentage_change": 1.07,
      "data": {
        "floor_price": "12.5 ETH",
        "floor_price_in_usd_24h_percentage_change": 1.07,
        "h24_volume": "430 ETH",
        "h24_average_sale_price": "12.1 ETH",
        "sparkline": "https://www.coingecko.com/nft/38/sparkline.svg",
        "content": null
      }
    }
  ],
  "categories": [
    {
      "id": 1,
      "name": "Layer 1 (L1)",
      "market_cap_1h_change": 0.12,
      "slug": "layer-1",
      "coins_count": 312,
      "data": {
        "market_cap": 2100000000000,
        "market_cap_btc": 30000000,
        "total_volume": 62000000000,
        "total_volume_btc": 890000,
        "market_cap_change_percentage_24h": { "usd": -0.66 },
        "sparkline": "https://www.coingecko.com/categories/1/sparkline.svg"
      }
    }
  ]
}
```

### Response Fields

| Field | Description |
|---|---|
| `coins[].item.id` | CoinGecko coin ID |
| `coins[].item.name` | Coin name |
| `coins[].item.symbol` | Ticker symbol |
| `coins[].item.market_cap_rank` | Market cap rank |
| `coins[].item.score` | Trending rank (0 = most trending) |
| `coins[].item.price_btc` | Price in BTC |
| `coins[].item.data.price` | Current price in USD |
| `coins[].item.data.price_change_percentage_24h` | 24hr price change % by currency |
| `coins[].item.data.market_cap` | Market cap (formatted string) |
| `coins[].item.data.total_volume` | 24hr volume (formatted string) |
| `coins[].item.data.sparkline` | Sparkline chart URL |
| `nfts[].id` | NFT collection ID |
| `nfts[].name` | NFT collection name |
| `nfts[].floor_price_in_native_currency` | Current floor price in native currency |
| `nfts[].floor_price_24h_percentage_change` | Floor price 24hr change % |
| `nfts[].data.floor_price` | Floor price (formatted string) |
| `nfts[].data.h24_volume` | 24hr volume (formatted string) |
| `categories[].id` | Numeric category ID |
| `categories[].name` | Category name |
| `categories[].slug` | Category slug (matches `category_id` in `references/categories.md`) |
| `categories[].coins_count` | Number of coins in the category |
| `categories[].data.market_cap` | Category market cap in USD |
| `categories[].data.market_cap_change_percentage_24h` | Market cap 24hr change % by currency |

---

## `GET /exchange_rates` — BTC-to-Currency Exchange Rates

| Field | Value |
|---|---|
| Description | Query BTC exchange rates against all supported currencies |
| Path | `GET /exchange_rates` |

### Parameters

None.

### Notes
- Use this endpoint to convert BTC-denominated values returned by exchange volume
  chart and derivatives endpoints into other currencies.

### Example Response
```json
{
  "rates": {
    "btc": { "name": "Bitcoin", "unit": "BTC", "value": 1, "type": "crypto" },
    "eth": { "name": "Ether", "unit": "ETH", "value": 20.656, "type": "crypto" },
    "usd": { "name": "US Dollar", "unit": "$", "value": 69420, "type": "fiat" },
    "xau": { "name": "Gold", "unit": "XAU", "value": 35.2, "type": "commodity" }
  }
}
```

### Response Fields

| Field | Description |
|---|---|
| `rates` | Map of currency code → rate object |
| `rates.{code}.name` | Currency name |
| `rates.{code}.unit` | Currency unit or symbol |
| `rates.{code}.value` | How many units of this currency equal 1 BTC |
| `rates.{code}.type` | Currency type: `crypto`, `fiat`, or `commodity` |