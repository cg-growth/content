> **Routines: also read and follow `docs/SCOUT.md` (Scout near-miss tier) every run.**

# Real-time paper layer (ALL PAPER — never real funds)
Start: `./start.sh` (loads keys from `~/.coingecko/keys.env` / `~/.grokbot-memecoin/keys.env` or the environment; Grok Bot routine runs
have them as secrets). Secrets are inherited only; never written/logged. `scripts/supervise.sh` (proc name memescan-supervise) checks every 30s:
dashboard, telegram, stream, risk, discovery, tracker, autotrader, risk_auto; restarts dead/stale (>180s log silence) children; TG ping if down >2 min.
Stop: `./stop.sh`. Status: `./status.sh`. Logs: logs/*.log. Dry flags: RISK_DRY=1, DISCOVERY_DRY=1, TRACKER_DRY=1, `send_card.py x.json --dry`.

| service | file | does |
|---|---|---|
| stream | stream/stream.py | WebSocket `wss://stream.coingecko.com/v1` on a CoinGecko API Basic plan or higher (header from the detected key). G3 1s (positions), 1m (watchlist), G2 trades, G1 price+reserve. Resyncs subs every 5s from paper.db positions + watchlist table. REST fallback (1s/15s OHLCV, pool trades, simple price) on WS drop, backoff. On a CoinGecko API Demo (free) key, WebSocket is not on the plan, so token prices are polled over REST at `stream.poll_interval_s` (default 60s). If a socket accepts and the first message is `{"message":"Unauthorized access, invalid API key"}`, the scanner switches to that poll. 15s OHLCV works on a CoinGecko API Demo (free) key. market.db ring: 1s 6h, 15s/1m 3d, trades/prices 2d. |
| risk | risk/risk.py | plans in paper.db risk_plans (auto-attached to every position). Auto: SL -45% (first 10 min needs 60s below), BE at 2x, trailing 25% after +50%, danger (reserve -40%/5m, insider/dev sell via REST trades + wallets.db labels, honeypot flip). Ask (Sell X%/Hold/Adjust): dynamic TP, time stop. |
| discovery | discovery/discovery.py | every `discovery.interval_s` (default 60s): new_pools on each `discovery.networks` chain (robinhood/base/bsc/solana). Megafilter (price_change, buys, tax, honeypot checks) runs on a CoinGecko API Analyst plan or higher; other plans also poll trending pools and use the same local filters. Then quick filters → deep research thread → research/<net>_<ca>.json → queued in pending_research.json for the scheduled scan routine (and POSTed to TELEGRAM_FORWARD_URL if set). HTTP 429 does not change the interval. |
| tracker | tracker/tracker.py | outcomes 1h/6h/24h/max for every alert (bought/skipped/ignored); 21:00 local-time recap image (MEMESCAN_TZ). |
| alerts | alerts/send_card.py, card.py, portfolio.py | PNG chart card + dynamic-size buttons; /portfolio image. |

## Research payload (discovery → pending_research.json, and TELEGRAM_FORWARD_URL if set)
POST JSON, headers `Authorization: Bearer <key>`, `X-Api-Key: <key>`. Max 12/hour. Deep-discarded tokens are re-researched only on >=50% growth in buyers_h1 or liquidity.
```
{"type":"research","source":"discovery","chat_id":null,"text":"[research] <verdict> candidate <SYM> on <net> score <n>. ...",
 "ca":"0x..","network":"robinhood","pool":"0x..",
 "metrics":{"liq","fdv","age_min","h1_change","m5_change","buyers_h1","sellers_h1","buys_h1","sells_h1","vol_h1","pool_created_at","name","price"},
 "token":{name,symbol,gt_score,gt_score_details,is_honeypot,developer_address,developer_holding_percentage,twitter_handle,telegram_handle,websites,description,categories,holders},
 "holders":{"top10_pct_ex_pools":n,"top":[{"a","pct","label"}]}, "top_traders":[{"a","realized","unrealized","buy_usd","sell_usd"}],
 "holders_chart":[[iso,count],...], "wallet_score":{n_wallets,mix,human_participation,read,bundles},
 "smart_money_wallets":[..], "components":{human,safety,momentum,smart_money,holder_growth}, "score":n, "flow_buy_share":0.xx,
 "prelim_verdict":"Watch"|"Watch? (wallets unverified)"|"Organic Hype?", "fail_reasons":[], "bundles_n":n,
 "links":{"gt","x_ca","x_ticker"}, "research_secs":n, "generated_at":iso, "card_cmd":"python3 alerts/send_card.py <alert.json>"}
```
`holders`, `top_traders`, `holders_chart` and wallet profiles are filled only when the plan includes them (a CoinGecko API Analyst plan or higher). Otherwise the payload carries a note (`not included with a CoinGecko API Demo (free) key`, or `needs a CoinGecko API Analyst plan or higher`) and that gap is not a fail. `prelim_verdict` can still be `Organic Hype?` when wallet checks are not on the plan. See `docs/PLANS.md`.

The routine should: (1) classify unverified wallets with wallet PnL/trades endpoints **only when `./status.sh` shows those checks are on the plan**; if the payload says they are not available, skip the lookup and do not treat that as a fail, (2) X search by CA then ticker (drop namesakes),
(3) write narrative, (4) write alert.json and run send_card.py — or stay silent if it discards.

## alert.json for send_card.py
`{ca, network, pool, symbol, tag ("Watch"|"Organic Hype"), confidence ("low"|"high"), score, human_score, components{}, mix{},
  metrics{liq,fdv,age_min}, pool_created_at, smart_buys[{t,price}], bundles[], bot_share, narrative, x_links[[title,url],...], price}`
Sizing is recomputed at send time (lib/sizing.py): min(pool cap = median trade ≤1% liq, shrunk if predatory; conviction-scaled; portfolio cap).
Buttons: Buy rec / 0.5x / 2x · Skip · Mute · Positions · GT · X. Skip/Buy logged to paper.db decisions + outcomes.

## Telegram free-form forwarding (latency + idempotency)
- nl.py parses locally (confirm buttons): "let's get into X $50", "ape X 50", "put 50 in X", "jump into X 25", typo "but $50 of it" (only with a reply or an alert sent in the last 45 min). Questions (why/what/should…, or ending in "?" without a leading trade verb) are never parsed as trades.
- Forwarded messages get an instant "⏳ On it, researching… ~1–3 min" reply.
- Confirm prompts warn when a same-CA same-side trade happened in the last 10 min. The routine must call `core.recent_trade(ca, side, 10)` (CLI: `.venv/bin/python telegram/core.py recent-trade <ca> <side> 10`) before any forwarded trade.
