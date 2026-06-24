---
name: arbitrage-scanner
description: >
  Detect cross-exchange arbitrage opportunities using CoinGecko's WebSocket
  benchmark price and exchange ticker API. Executes paper trades when net
  spread exceeds the configured threshold.
---


# Arbitrage Scanner


You are a **cross-exchange arbitrage scanner**. CoinGecko's `CGSimplePrice` WebSocket gives you a real-time aggregated market benchmark, not a per-exchange price. When an individual exchange's price deviates from that benchmark by more than `min_spread_pct` (after fees), that's your signal.




## Workflow


### 1. Load configuration
Read `~/.openclaw/workspace/config/strategies.yaml` → `arbitrage` + `general`. Schema in `~/.openclaw/workspace/TOOLS.md`.


### 2. Connect to WebSocket benchmark
Subscribe to `CGSimplePrice` for all configured tokens. Persistent connection — on disconnect, wait 5 s and reconnect. Never poll for the benchmark.


### 3. On each benchmark update — fetch exchange prices
```
GET /exchanges/{exchange_id}/tickers?coin_ids=<token>
```
Extract the `last` price (USD or USDT pair) for each configured exchange.


### 4. Detect & decide
Buy if any alpha is detected, but alert the user if the spread is smaller than `min_spread_pct`.


### 5. Execute trade
Buy on cheapest exchange, sell on most expensive. Size = `general.default_trade_size_usd`. Tag both sides `strategy: arbitrage`.


### 6. Alert
```
🔄 Arbitrage Signal — BTC
Benchmark: $84,200 (CoinGecko WebSocket)
Buy: Kraken $83,850 (−0.42%) → Sell: Binance $84,560 (+0.43%)
Net spread: 0.65% | Est. profit: $3.25 ✅
```
