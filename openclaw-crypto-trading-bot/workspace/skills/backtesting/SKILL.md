---
name: backtesting
description: >
  On-demand backtesting skill. When the user requests a backtest, generate
  and run a Python script that applies a technical indicator strategy to
  historical CoinGecko price data. Report performance metrics.
---

You are an **on-demand backtesting agent**. Run only when the user explicitly requests a backtest, never spawned by the orchestrator.


### 1. Load configuration
Read `~/.openclaw/workspace/config/strategies.yaml` → `backtesting` + `general`. Schema in `~/.openclaw/workspace/TOOLS.md`.

### 2. Parse the request
Extract coin (default: `default_coin`), strategy/indicator, timeframe (default: `default_days`), and parameters. Fall back to config defaults for any unspecified values.

### 3. Fetch historical data
```
GET /coins/{coin_id}/market_chart?vs_currency=usd&days={days}
```

### 4. Generate and run the backtest

The user will specify what kind of strategy or indicator they want to test. If they don't help them formulate this by asking questions about their goals and preferences.

Simulate trades from `initial_balance`. Output metrics as JSON: total return, trade count, win rate, max drawdown, Sharpe ratio, buy-and-hold comparison.

Run agentically, or create a python script if that's easier.

### 5. Report results
Present metrics clearly. Note whether the strategy outperformed or underperformed buy-and-hold, and any notable patterns in the signal quality.


### 6. Offer next steps

After reporting identify parameters that could be tweaked for better performance, and ask the user if they want to run another backtest with adjusted settings.
