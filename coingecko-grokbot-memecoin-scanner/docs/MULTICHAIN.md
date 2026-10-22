# Multi-chain (Solana + EVM)

## Why CA-first ticker resolution matters
Memecoin tickers are not unique. A trader said "buy <TICKER>, $50" and an early version of `telegram/nl.py` → `core.resolve("<TICKER>")` picked the **latest** matching ticker in `alerts` / `state.json`, which was an EVM copycat (a CoinGecko-first discard), while the token actually buzzing on X was a Solana mint with the same ticker. Cause: ticker→CA resolution had no CA-first preference and no namesake picker.

## Fix (ticker resolution)
1. **CA-first**: EVM `0x…40` *and* Solana base58 are accepted anywhere in the message.
2. **Reply-to alert / recent alert CA** wins when the ticker matches that family.
3. When multiple (chain, CA) pairs share a ticker → Telegram shows **pick buttons** (chain + short CA + liquidity + age + verdict). Never auto-picks a namesake.
4. Live CoinGecko `/search/pools` is consulted when a ticker has only one assessed hit that isn't alerted, so a Solana runner still surfaces even if only an EVM clone is in `state.json`.
5. X-buzz assessed tokens (`source` starts with `x`) rank above CG-first discards in the picker list.

## Address casing
`lib/addr.py`:
- EVM → lowercase
- Solana / base58 → **case preserved** (CG PnL returns empty data for lowercased Solana addresses — verified)

Used in `walletdb.py`, discovery, xfirst, risk, telegram core/nl, send_card.

## Solana CoinGecko endpoints (verified Oct 2026; see the [CoinGecko API docs](https://docs.coingecko.com/?utm_source=grokbot&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=docs-multichain) for the current list)
| Endpoint | Solana |
|---|---|
| `/networks/solana/tokens/{ca}` info and trades | ✅ on a CoinGecko API Demo (free) key and above |
| `/networks/solana/tokens/{ca}` top_holders, top_traders, holders_chart | ✅ on a CoinGecko API Analyst plan or higher; omitted on the CoinGecko API Demo (free) plan and the CoinGecko API Basic plan |
| `/networks/solana/pools/{pool}/trades`, `/ohlcv/*`, `/simple/.../token_price` | ✅ (CoinGecko API Demo (free) pool trades: last 300 from the past 24h) |
| WebSocket G1 / G2 / G3 on solana pools & tokens | ✅ on a CoinGecko API Basic plan or higher; a CoinGecko API Demo (free) key polls REST prices instead |
| `/wallets/{addr}/pnl?networks=solana` | ✅ on a CoinGecko API Analyst plan or higher (lifetime; **case-sensitive**) |
| `/networks/solana/wallets/{addr}/trades` (cursor) | ✅ on a CoinGecko API Analyst plan or higher (~100/page) |
| `/wallets/{addr}/balances` | ❌ EVM only |
| `/networks/solana/wallets/{addr}/transfers` | ❌ empty/404 |

### Wallet history reconstruction (`lib/sol_profile.py`)
From PnL + wallet trades (≈2–3 credits/wallet, cached 6h in `wallets.db.wallet_history`):
- tokens traded, buy/sell counts & USD, realized/unrealized PnL, closed-trade win rate
- approx residual balances = net token flow (buy − sell amounts; no USD residual without price)
- hold-time / snipe (<60s) / flip (<5m) heuristics from newest ~200 trades (~1–3 days of tape for busy snipers, not a full 30d tape)
- labels: bot / sniper / flipper / proven_candidate / unknown → same `walletdb.py upsert` path

**Limits:** no true balance/transfer view; PnL is lifetime not windowed; trade tape is recent-only; 30d “approx balance” is reconstructed, not observed.

## Paper / risk / stream
`CHAINS` includes `solana`. Quotes use the configured CoinGecko key (Solana casing preserved).
Risk engine, stream subscriptions (WebSocket on a CoinGecko API Basic plan or higher, REST price poll on a CoinGecko API Demo (free) key), tracker, and portfolio/report cards are keyed by `(network, pool, ca)` and work for Solana.

## Discovery networks
`risk.json` → `discovery.networks = [robinhood, base, bsc, solana]`. X-first resolves only those networks, unless `xfirst.networks` is set.
Wallet PnL and trades run only on a CoinGecko API Analyst plan or higher (~8 wallets × ≤3 credits when labels are missing, cached 6h). On other plans that step is skipped and is not a fail.
Each discovery cycle is one new-pools call per network, plus Megafilter on a CoinGecko API Analyst plan or higher, or trending pools (one call per network) otherwise. The default `discovery.interval_s` is 60. At 20 seconds, four networks plus Megafilter is about 648,000 calls a month, above the CoinGecko API Analyst plan's 500,000 monthly credits. At 60 seconds that is about 216,000. The CoinGecko API Demo (free) monthly allowance is 10,000, so set a slower interval yourself. The scanner does not change `interval_s`.
