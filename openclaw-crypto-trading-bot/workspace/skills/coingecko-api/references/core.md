# CoinGecko API — Core Reference

Shared context loaded for every request. Covers data methodology, authentication,
and rate limits — read this before making any API call.

---

## Methodology: CoinGecko vs GeckoTerminal

### CoinGecko (aggregated data)
Covers tens of thousands of coins, each reviewed by the CoinGecko team before listing.
Aggregates market data across CEX, DEX, and derivatives markets — volume-weighted
aggregation makes prices more reliable and manipulation-resistant than any single venue.
Best suited for well-known assets (Bitcoin, Ethereum, Solana, major memecoins, etc.) and
broad market overviews like top coins by market cap, category rankings, and global stats.

### GeckoTerminal (on-chain DEX data only)
Covers tens of millions of tokens and pools, listed automatically from on-chain activity
— no review gate. Includes the full long tail: newly launched tokens, micro-cap coins,
and pools that don't meet CoinGecko's listing criteria. Tracks real-time on-chain
activity across blockchain networks and DEXes.

Use GeckoTerminal when:
- The user needs pool-level data (liquidity, specific trading pairs)
- The token is long-tail or newly launched and isn't listed on CoinGecko
- The user needs on-chain trade history or OHLCV
- The user is asking about a specific DEX or network

### Which to use
**Prefer CoinGecko** when both APIs could answer the question — aggregated data is
broader, more accurate, and less susceptible to thin-liquidity or single-pool distortion.

Fall back to GeckoTerminal when the request is inherently on-chain (pool data, DEX-native
tokens, contract address lookups, on-chain trade activity) or targets tokens not listed
on CoinGecko.

---

## Authentication

### Plan types

| Plan | Rate Limit | Notes |
|---|---|---|
| **Paid (Pro)** | 250+ calls/min (varies by plan) | Full endpoint access, highest reliability |
| **Demo** | 30 calls/min | Most endpoints, free with registration |
| **Keyless** | 5 calls/min | Unstable, shared IP pool, not recommended |

Once you know the user's plan, hard-code that tier's config — do not write branching logic that auto-detects the plan.

### Base URLs and auth

| Plan | Base URL | Auth header | Query param |
|---|---|---|---|
| **Paid (Pro)** | `https://pro-api.coingecko.com/api/v3` | `x-cg-pro-api-key: KEY` | `?x_cg_pro_api_key=KEY` |
| **Demo** | `https://api.coingecko.com/api/v3` | `x-cg-demo-api-key: KEY` | `?x_cg_demo_api_key=KEY` |
| **Keyless** | `https://api.coingecko.com/api/v3` | *(omit all auth)* | *(omit all auth)* |

Use header or query param — not both.

For GeckoTerminal endpoints, append `/onchain` to the base URL —
e.g. `https://pro-api.coingecko.com/api/v3/onchain/...`

---

## Common conventions

These patterns recur across many endpoints and are documented here once to avoid repetition.

### Coin ID resolution
Use `GET /search` (in `references/utils.md`) when you know the coin name or symbol, or
`GET /coins/list` (in `references/coins.md`) for the full ID map.

### Date/Time parameters
Check each endpoint's date/time format — it varies:

| Context | Format |
|---|---|
| Coin/Contract/Supply `from`/`to` | ISO `YYYY-MM-DD` |
| `GET /exchanges/{id}/volume_chart/range` `from`/`to` | UNIX timestamp (seconds) |
| `GET /coins/{id}/history` `date` | `DD-MM-YYYY` |
| GeckoTerminal `before_timestamp` | UNIX timestamp (seconds) |

When the user refers to "now", "today", "this week", "last 7 days", or any relative time
expression, always resolve it using the actual current date provided by the system context
— never infer or guess dates from training data.

### Auto-granularity for chart endpoints
When an `interval` param is left empty, granularity is determined automatically by the
date range:
- 1 day → 5-minutely
- 2–90 days → hourly
- Above 90 days → daily (00:00 UTC)

You may bypass auto-granularity by setting `interval` explicitly:
- `interval=daily` — daily historical data.
- `interval=hourly` — hourly historical data, up to the **past 100 days**.
- `interval=5m` — 5-minutely historical data, up to the **past 10 days** (or up to **any 10-day** date range per request). Exclusive to Enterprise subscribers.

### Data availability
The last completed UTC day is typically available 10–35 minutes after midnight UTC,
depending on the endpoint.

### BTC-denominated values
Exchange and derivatives volume endpoints return values in BTC. Use `GET /exchange_rates`
(in `references/utils.md`) to convert to other currencies.

---

## Error handling

### Auth-related errors

| Code | Meaning | What to do |
|---|---|---|
| `401` | No API key provided at all | Ask the user to provide their API key |
| `10002` | Wrong auth method or key missing | Verify correct header name for the plan type; check key isn't used against the wrong base URL |
| `10005` | Endpoint requires a higher plan | Tell the user; direct them to https://www.coingecko.com/en/api/pricing |
| `10010` | Wrong key type (Pro key on Free URL) | Switch base URL to `https://pro-api.coingecko.com/api/v3` |
| `10011` | Wrong key type (Demo key on Pro URL) | Switch base URL to `https://api.coingecko.com/api/v3` |

If no valid key can be obtained, fall back to keyless access.

### Rate limit errors

| Code | Meaning | What to do |
|---|---|---|
| `429` | Rate limit exceeded | Suggest upgrading at https://www.coingecko.com/en/api/pricing; update memory if they subscribe |

### Network-level failures ("Failed to fetch", `TypeError`, no response body)

When a request fails at the network level — no HTTP status code, no JSON body, just a
generic "Failed to fetch" or `TypeError: Failed to fetch`:

**If running inside Claude:** The cause is almost certainly a Claude platform constraint,
not a URL or CORS issue. See `references/claude-env.md` for the full diagnostic flowchart.
The most common causes are: (1) the call was made from inside an Artifact (blocked by
sandbox CSP — move to `bash_tool`), or (2) the user hasn't allowlisted CoinGecko domains
in their Claude settings.

**If running outside Claude** (local dev, other LLMs, server-side): The cause is likely a
**wrong base URL**:

1. **Verify the base URL matches the tier:**
   - Pro key → must use `https://pro-api.coingecko.com/api/v3`
   - Demo key → must use `https://api.coingecko.com/api/v3`
   - Keyless → must use `https://api.coingecko.com/api/v3` with no auth header
   - Mixing these up causes the request to fail at the network level.
2. **Check the endpoint path** for typos or missing segments.
3. **Check the auth header name** matches the plan type (`x-cg-pro-api-key` vs
   `x-cg-demo-api-key`).

**In all cases:** Never assume CORS. The CoinGecko API does not block requests via CORS.
Do not suggest CORS workarounds, proxy servers, or backend routing as a fix.

### Other errors

| Code | Meaning |
|---|---|
| `400` | Bad request — invalid parameters |
| `408` | Request timeout — likely a slow network |
| `500` | Internal server error |