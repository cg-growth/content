> Read the full article: [How to Build a DEX Aggregator to Find the Best Swap Rates](https://www.coingecko.com/learn/how-to-build-dex-aggregator)

Turn every on-chain swap into a win. The DEX Aggregator Dashboard gives you a trader’s-eye view of liquidity, fees, and slippage across networks in seconds, so you can spot the optimal route before anyone else.

![alt text](<DEX App.gif>)
The app orchestrates a live quote: it pulls the supported networks from CoinGecko, lets you choose a chain and token pair, then discovers pools containing the input token. It cross-checks for the output token, batches the pool metrics, and reranks routes so you instantly see the best path, expected output, slippage, and fee impact while weaker pools stay visible for context.

<h2>Endpoints Used</h2>

DEX Aggregator Dashboard — Endpoints

- Framework: React (single-page UI served by Express).
- API: CoinGecko On‑chain Demo API, base `https://api.coingecko.com/api/v3/onchain` with `x-cg-demo-api-key` header. No runtime fallback is used.

- Discover Pools: `GET /onchain/networks/{network}/tokens/{token_address}/pools`
  - Role: Core discovery. Finds all pools on a specific network that involve `token_address`. Used to assemble the candidate pool list for the selected pair (the app discovers using the "from" token, then filters to those that include the "to" token).

- Pool Details (bulk): `GET /onchain/networks/{network}/pools/multi/{addresses}`
  - Role: Fetches detailed attributes for multiple pools in a single request, including prices, `reserve_in_usd` (liquidity), and `pool_fee_percentage`. Used to compute Estimated Output and rank pools best → worst.

- Networks (helper): `GET /onchain/networks`
  - Role: Populates the network dropdown with supported networks and display names.

Env keys: `CG_DEMO_API_KEY` (demo). If you choose to use Pro instead, change the base to `https://pro-api.coingecko.com/api/v3/onchain` and use header `x-cg-pro-api-key` with `CG_PRO_API_KEY`.


