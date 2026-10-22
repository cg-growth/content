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

## Solana CoinGecko endpoints (verified Oct 2026; see the [CoinGecko API docs](https://docs.coingecko.com/?utm_source=github&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=docs-multichain) for the current list)
| Endpoint | Solana |
|---|---|
| `/networks/solana/tokens/{ca}` (+ info, top_holders, top_traders, holders_chart, trades) | ✅ |
| `/networks/solana/pools/{pool}/trades`, `/ohlcv/*`, `/simple/.../token_price` | ✅ |
| WebSocket G1 / G2 / G3 on solana pools & tokens | ✅ |
| `/wallets/{addr}/pnl?networks=solana` | ✅ (lifetime; **case-sensitive**) |
| `/networks/solana/wallets/{addr}/trades` (cursor) | ✅ (~100/page) |
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
`CHAINS` includes `solana`. Quote uses Pro API (case preserved) with GeckoTerminal fallback.
Risk engine, 1s stream subscriptions, tracker, portfolio/report cards all keyed by `(network, pool, ca)` and work for Solana (scratch ledger buy→sell + WS G1/G2/G3 + dry SL verified).

## Discovery networks
`risk.json` → `discovery.networks = [robinhood, base, bsc, solana]`.
Extra Solana cost per deep: ~8 wallets × ≤3 credits ≈ 24 credits when wallets are unverified (cached 6h). New-pools + megafilter add 1 call per network per 20s cycle (~4.3k REST calls/day per extra network at the default 20s interval — check your plan's monthly credits; raise `discovery.interval_s` to spend less).
