# CoinGecko plans and what the scanner does with each

A CoinGecko API key is required. The scanner never calls CoinGecko without one. Pick the plan that fits; `./start.sh` detects it from the key.

New to CoinGecko API? Sign up for a CoinGecko API Demo (free) plan or a paid plan on the [pricing page](https://www.coingecko.com/en/api/pricing?utm_source=github&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=docs-plans-signup). CoinGecko's sign-up then opens the developer dashboard, where you copy the key. Already have a CoinGecko API account? Copy the key from the [developer dashboard](https://www.coingecko.com/en/developers/dashboard?utm_source=github&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=docs-plans-dashboard#api-keys).

Checked against the [pricing](https://www.coingecko.com/en/api/pricing?utm_source=grokbot&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=docs-plans-pricing) page (22 Oct 2026), [errors and rate limits](https://docs.coingecko.com/docs/errors-and-rate-limits?utm_source=grokbot&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=docs-plans-rate-limits), [endpoint overview](https://docs.coingecko.com/reference/endpoint-overview?utm_source=grokbot&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=docs-plans-endpoints), and [data delivery methods](https://docs.coingecko.com/docs/data-delivery-methods?utm_source=grokbot&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=docs-plans-delivery). Dollar prices change. Use the pricing page for the current ones.

| | CoinGecko API Demo (free) | CoinGecko API Basic | CoinGecko API Analyst and higher |
|---|---|---|---|
| Env var | `COINGECKO_DEMO_API_KEY` (a CoinGecko API Demo (free) key in `COINGECKO_PRO_API_KEY` still works) | `COINGECKO_PRO_API_KEY` | `COINGECKO_PRO_API_KEY` |
| Host and header | `api.coingecko.com`, `x-cg-demo-api-key` | `pro-api.coingecko.com`, `x-cg-pro-api-key` | same as the CoinGecko API Basic plan |
| Credits / month | 10,000 | 100,000 | 500,000 on the CoinGecko API Analyst plan; more on Lite, Pro, Enterprise |
| Calls / minute | 100 | 300 | 500 on the CoinGecko API Analyst plan |
| Price (pricing page) | $0, attribution required | from $35/mo; compare table shows $29/mo billed yearly | compare table shows the CoinGecko API Analyst plan at $103.20/mo billed yearly |
| New pools, trending pools, pool, token info, OHLCV (including 15s), recent trades, pool search | Yes, including network id `robinhood` | Yes | Yes |
| Top traders, top holders, holder history, wallet PnL and trades, Megafilter | No | No (those endpoints are marked 💼 and need a CoinGecko API Analyst plan or higher) | Yes |
| WebSocket `wss://stream.coingecko.com/v1` | No. A refused key can still accept the socket, then send `{"message":"Unauthorized access, invalid API key"}`. The scanner then polls REST. | Yes (5 sockets) | Yes (10 sockets on the CoinGecko API Analyst plan) |
| `GET /key` usage | No. HTTP 401, error code 10005 | Yes | Yes |
| Pool liquidity events (`/pools/{pool}/liquidity_events`) | No. History and caller detail need a CoinGecko API Analyst plan or higher. A held Solana reserve drop still alerts from the reserve, and one daily note names that plan. | No. Same reserve alert and the same daily note. | Yes. Solana only, DEXes PumpSwap and Meteora DAMM v2. Other networks and DEXes return HTTP 400 and are not called. |

Lite, Pro and Enterprise map to the same capability tier as the CoinGecko API Analyst plan: wallet, trader, holder and Megafilter calls stay on.

## What each tier actually runs

The CoinGecko API Demo (free) plan and the CoinGecko API Basic plan still run the core loop: new pools (and trending pools, because Megafilter is off), pool data, token info, OHLCV, recent trades, exact-contract X buzz or the X-first reverse path, then a score and a verdict (Organic Hype, Watch, Scout, Discard).

Paid-only fields are omitted and labeled `not included with a CoinGecko API Demo (free) key`, or `needs a CoinGecko API Analyst plan or higher` on the CoinGecko API Basic plan. A missing field is never a fail. Token-info holder distribution, when present, is an approximation (it includes pools and exchanges) and is labeled as such. The safety check uses a looser top-10 cutoff for that approximation.

On a CoinGecko API Demo (free) key, prices for open paper positions are polled with the onchain simple-price endpoint at `stream.poll_interval_s` (default 60 seconds, up to 30 addresses per call). A CoinGecko API Basic plan or higher uses the WebSocket. If the socket drops, the existing REST fallback still runs.

## Discovery interval

`discovery.interval_s` in `risk.json` is seconds between discovery cycles. The scanner does not change it. With the default four networks, a cycle is one new-pools call per network, plus one Megafilter call on a CoinGecko API Analyst plan or higher (5 calls) or one trending-pools call per network on other plans.

Derived from that call count and the pricing-page allowances (not a figure CoinGecko publishes): 20 seconds is about 648,000 Megafilter-inclusive calls a month, which is above the CoinGecko API Analyst plan's 500,000 credits. The default is 60 seconds, about 216,000 of those calls a month. On a CoinGecko API Demo (free) key, 10,000 credits at 60 seconds is more than the month allows, so set a slower interval if you want the month to last. Any value is valid, including 20.

## Usage

`GET /key` on the paid host ([API usage](https://docs.coingecko.com/reference/api-usage?utm_source=grokbot&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=docs-plans-key)) is the source of truth on a CoinGecko API Basic plan or higher. Fields used: `plan`, `rate_limit_request_per_minute`, `monthly_call_credit`, `current_total_monthly_calls`, `current_remaining_monthly_calls`. When `api_key_monthly_call_credit` is set, the per-key used count (`api_key_current_total_monthly_calls`) is used instead. The scanner reads this at startup, about hourly, and after an HTTP 429.

The CoinGecko API Demo (free) endpoint list does not include `GET /key` ([utility overview](https://docs.coingecko.com/demo/reference/endpoint-overview?utm_source=grokbot&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=docs-plans-demo-utility)). Calling it with a CoinGecko API Demo (free) key returns HTTP 401, error code 10005, "This request is limited to PRO API subscribers...". That is a plan limit, not a bad key. On that key, a used-up month is detected from HTTP 429 or a credit-limit error. Those responses carry no rate-limit or credit headers. The local call counter is shown as an estimate only.

`lib/credits.py` estimates use on a CoinGecko API Demo (free) key from the repeating calls. Listing is one new-pools call and one trending-pools call per network. A measured run on 22 Oct 2026 (60 second interval, four networks) used about 17 credits per cycle, so the table adds 9 research credits at four networks and scales that with the network count. At those defaults the 10,000 monthly CoinGecko API Demo (free) credits last about 0.4 days (about 10 hours). The script prints the figure for the current `discovery.interval_s` and `discovery.networks`. The owner keeps that interval or picks a slower one. The scanner does not change it.

Around 90% of a paid month's credits, one short "running low" note is sent. At 0 remaining, one "used up" note is sent. Neither note changes the schedule. `/usage` in Telegram and the dashboard show the same figures.

## When the limit is hit

HTTP 429, or a body that says the monthly credits are used up, is logged and stored for `./status.sh`. The same text is queued for the Grok Bot chat (`notices/pending.json`) and sent on Telegram when `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are both set. Each note is its own message, not part of a scan alert.

A missing-feature note is sent at most once a day, and only when plan tips are on. Credits used up, and a rejected key, are sent once per event even when plan tips are off. Set `plan_tips.enabled` to false to hide the other notes. The schedule does not change. A higher plan has a higher monthly cap and a higher per-minute limit: [pricing](https://www.coingecko.com/en/api/pricing?utm_source=grokbot&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=docs-plans-limit).

## Plan tips

`plan_tips.enabled` in `risk.json` (default true). Set it to false to hide plan-related tips. `/plantips off` does the same and is stored locally. Credits used up and a rejected key still send.

- `credits_exhausted`: monthly credits used up. Once per event, even when tips are off.
- `credits_low`: about 90% of a paid month, from `GET /key`. Once per crossing, only when tips are on.
- `invalid_key`: CoinGecko rejected the key. Once per event, even when tips are off.
- `rate_limit`: HTTP 429 that is a per-minute limit. At most once a day, only when tips are on.
- `wallet_gap`: top-trader or wallet checks are not on this plan, and the score is within 8 points of 70 or of `discovery.deep_min_human` (default 60). At most once a day, only when tips are on.
- `liquidity_gap`: a held Solana position's reserve dropped, and this key is a CoinGecko API Demo (free) key or a CoinGecko API Basic plan. The note says liquidity-event detail (who removed it and how much, on Solana PumpSwap and Meteora DAMM v2) needs a CoinGecko API Analyst plan or higher. At most once a day, only when tips are on. The reserve alert itself still sends.
- `weekly`: its own message, at most once a week, only when the plan limited something and tips are on.

Notes are not added to scan cards. The routine relays `notices/pending.json` into the Grok Bot chat, one message each.

## Error shapes (checked with a CoinGecko API Demo (free) key, 22 Oct 2026)

| Situation | HTTP | Body |
|---|---|---|
| Endpoint that needs a CoinGecko API Analyst plan or higher, called with a CoinGecko API Demo (free) key (top traders, top holders, holder chart, wallet PnL, wallet trades, Megafilter) | 401 | `{"status":{"error_code":401,"error_message":"This request is exclusive to Analyst plan or above subscribers only. ..."}}` |
| `GET /key` with a CoinGecko API Demo (free) key | 401 | error code 10005, "This request is limited to PRO API subscribers..." |
| Missing or unknown key | 401 | error code 10002, "API Key Missing" |
| Pro header (`x-cg-pro-api-key`) on the CoinGecko API Demo (free) host | 400 | top-level `error_code` 10010 (not inside `status`) |
| CoinGecko API Demo (free) key on the paid host | 400 | top-level `error_code` 10011 (not inside `status`) |

Codes 10005 and 401-with-that-plan-message are a missing feature. The scan continues, and the feature-gap note is the plan tip (at most once a day, and only when plan tips are on). Codes 10002, 10010 and 10011, and a 401 without that plan wording, are a rejected key. That note still sends when plan tips are off.

Robinhood (`robinhood`) new pools and trending pools respond on a CoinGecko API Demo (free) key. 15-second OHLCV responds on that key too.

## CoinGecko MCP

The remote server `https://mcp.pro-api.coingecko.com/mcp` needs a paid CoinGecko API key. Its sign-in page says a Pro API key is required. On a CoinGecko API Demo (free) key the scanner runs without that server. The local `@coingecko/coingecko-mcp` package accepts `COINGECKO_DEMO_API_KEY` with `COINGECKO_ENVIRONMENT=demo`. Connect the remote server only when the owner has a paid key. Do not use a keyless MCP server.

## Detection

`lib/cgtier.py` (run by `./start.sh`):

1. If `COINGECKO_PRO_API_KEY` is set, `GET /key` on the pro host. The `plan` field maps to `demo`, `basic`, or `analyst` (the CoinGecko API Analyst plan, and anything else that is not the CoinGecko API Basic plan or the CoinGecko API Demo (free) plan).
2. Otherwise the CoinGecko API Demo (free) key is checked with `GET /onchain/networks?page=1` on the demo host.
3. A paid key stored in `COINGECKO_DEMO_API_KEY`, or a CoinGecko API Demo (free) key stored in `COINGECKO_PRO_API_KEY`, is still accepted. The note says which variable it was found in.
4. No key exits 2. A key CoinGecko rejects exits 3. A network error, HTTP 429, or HTTP 5xx during detection exits 4 and does not guess a tier.
5. `MEMESCAN_CG_TIER=demo|basic|analyst` skips the live check. Use it only when you already know the plan.

`CG_API_MODE` is ignored. A stale value in a keys file does not block startup.
