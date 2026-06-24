# OpenClaw — Shared Agent Reference

Single source of truth for subagent architecture and `~/.openclaw/workspace/config/strategies.yaml`. Individual `SKILL.md` files must not repeat this — read config at runtime and follow the rules below.

---

## Subagent Architecture

```
User
 └── trading-orchestrator  (talks to user, spawns/kills subagents)
       ├── arbitrage-scanner
       ├── onchain-discovery
       ├── copy-trading-monitor
       └── news-trading-analyst
```

## Rules

- **One skill = one subagent** — never run two strategies in the same agent loop.
- **Always confirm** — never start live trading without explicit human confirmation, regardless of config.
- **Orchestrator spawns** — only `trading-orchestrator` may spawn or kill subagents; skills never spawn each other.
- **Self-contained** — a subagent reads config, runs its loop, executes paper trades, emits output. It does not call other skills.
- **Backtesting is on-demand** — not spawned by the orchestrator; runs only on explicit user request.
- **Config at startup** — each subagent reads `~/.openclaw/workspace/config/strategies.yaml` and loads **only its own section** plus `general`. Mappings: `arbitrage-scanner` → `arbitrage`, `onchain-discovery` → `onchain_discovery`, `copy-trading-monitor` → `copy_trading`, `news-trading-analyst` → `news_trading`, `backtesting` → `backtesting`.
- **Spawn** — orchestrator spawns each enabled strategy as `"Run the <skill-name> skill continuously"`.
- **Inform the user** - When starting a trading strategy, always let the user know the configuraiton options selected.
- **CoinGecko Pro API Access** - you have access to the CG PRO API. Use it.
---

## `~/.openclaw/workspace/config/strategies.yaml` Schema

### `general`
- **`order_file_name`** *(string)* — open orders JSON file path; create on first run.
- **`trades_file_name`** *(string)* — executed trades JSON file path; create on first run.
- **`api_keys_file`** *(string)* — credentials file; canonical path: `~/.openclaw/credentials/.env`.
- **`default_trade_size_usd`** *(number)* — fallback trade size when a strategy doesn't override it.
- **`max_open_positions`** *(integer)* — maximum total open positions across all strategies.
- **`portfolio_start_balance`** *(number)* — starting virtual balance in USD for paper trading.
- **`take_profit_pct`** *(number)* — default take-profit threshold (%) used by strategies that don't define their own.
- **`stop_loss_pct`** *(number)* — default stop-loss threshold (%) used by strategies that don't define their own.

---

### `arbitrage` — read by `arbitrage-scanner`

Benchmark price via CoinGecko WebSocket (`CGSimplePrice`, persistent, no polling). Per-exchange prices via REST `GET /exchanges/{id}/tickers` (polled).

- **`mode`** *(string)* — `paper_trading`; no real orders placed.
- **`rebuy_existing_positions`** *(boolean)* — if `false`, skip tokens with an existing open position.
- **`tokens`** *(list | `"all"`)* — coin IDs to scan; `"all"` monitors everything.
- **`exchanges`** *(list | `"all"`)* — exchange IDs to poll; `"all"` covers every supported exchange.
- **`min_spread_pct`** *(number)* — minimum net spread (after fees) to trigger a trade.
- **`estimated_fee_pct`** *(number)* — round-trip fee estimate subtracted from gross spread.
---

### `onchain_discovery` — read by `onchain-discovery`

- **`mode`** *(string)* — `paper_trading` (no real orders) or `live` (real execution).
- **`rebuy_existing_positions`** *(boolean)* — if `false`, skip tokens with an existing open position.
- **`networks`** *(list)* — chains to scan via GeckoTerminal (e.g. `solana`, `ethereum`).
- **`min_liquidity_usd`** *(number)* — minimum pool liquidity in USD.
- **`min_24h_volume_usd`** *(number)* — minimum 24h trading volume in USD.
- **`min_24h_tx_count`** *(integer)* — minimum 24h transaction count.
- **`max_age_hours`** *(integer)* — only include pools created within this window.
- **`min_buy_sell_ratio`** *(number)* — minimum `h24_buys / h24_sells` (> 1 = net buying).
- **`check_holders`** *(boolean)* — evaluate top-holder distribution.
- **`min_holder_count`** *(integer)* — reject tokens below this holder count.
- **`check_ohlcv`** *(boolean)* — confirm upward price trend via OHLCV data.
- **`ohlcv_timeframe`** *(string)* — candle size for OHLCV check (`"hour"`, `"day"`, etc.).
- **`track_launchpad_graduation`** *(boolean)* — if `true`, sweep launchpad/bonding-curve pools approaching DEX graduation in addition to the standard Megafilter scan.
- **`min_bonding_curve_progress`** *(integer, 0–100)* — only include launchpad pools whose bonding curve progress is at or above this percentage (default 60). Pools ≥ 95 % are flagged **GRADUATING** and prioritised for pre-listing entry.
---

### `copy_trading` — read by `copy-trading-monitor`

- **`mode`** *(string)* — `paper_trading`; no real orders placed.
- **`interval`** *(string)* — how often to poll for new trader activity (e.g. `5 minutes`).
- **`networks`** *(list)* — chains to scan for trending tokens and top traders.
- **`token_addresses`** *(list)* — specific token addresses to analyse; leave empty to auto-discover from trending pools.
- **`top_n_traders`** *(integer)* — maximum number of traders to include in the recommendation shortlist.
- **`min_trader_pnl_usd`** *(number)* — minimum realised PnL for a trader to qualify.
- **`min_trade_size_usd`** *(number)* — dust filter; ignore trades below this value when monitoring.
- **`trade_size_usd`** *(number)* — USD value per mirrored paper trade.

---

### `news_trading` — read by `news-trading-analyst`

- **`enabled`** *(boolean)*, **`cron`** *(string)* — spawn toggle and run schedule.
- **`categories`** *(list)* — news categories to monitor (e.g. `general`, `defi`, `layer_1`, `nft`).
- **`reactive.min_market_cap_rank`** *(integer)* — only trade coins within this rank (e.g. `100` = top 100).
- **`reactive.sentiment_threshold`** *(string)* — minimum sentiment to trade (`strong_positive`, `positive`, etc.).
- **`reactive.trade_size_usd`** *(number)* — USD value per reactive trade.
- **`proactive.enabled`** *(boolean)* — scan for upcoming catalysts and position ahead of them.
- **`proactive.lookahead_days`** *(integer)* — catalyst look-ahead window in days.
- **`proactive.trade_size_usd`** *(number)* — USD value per proactive position.

---

### `backtesting` — on-demand only, not a persistent subagent

- **`default_coin`** *(string)* — coin ID when none specified by user.
- **`default_days`** *(integer)* — days of historical data to fetch.
- **`default_vs_currency`** *(string)* — quote currency (e.g. `usd`).
- **`initial_balance`** *(number)* — starting balance for trade simulations.
- **`indicators`** *(list)* — default parameters per strategy: `sma_crossover` (`short_window`, `long_window`), `rsi` (`period`, `overbought`, `oversold`), `bollinger_bands` (`window`, `num_std`).

---

## Execution Style

Use your best judgment to decide whether you will be performing a task agentically, via the CLI / curl and other similar tooling, or whether it makes logical sense to automate that task and hand it over to a shell / Python script. 
Your ultimate job is to produce the best possible trading results, with optimal token consumption.
- **`take_profit_pct`** / **`stop_loss_pct`** *(number)* — exit thresholds as % from entry.
