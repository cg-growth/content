# Routine: Telegram free-form handler (webhook)
**Trigger:** webhook. Optional: enables instant replies to free-form questions/voice notes and instant research on new candidates.
Each POST is one routine run (uses quota). After creating it, store its URL and key as `TELEGRAM_FORWARD_URL` / `TELEGRAM_FORWARD_KEY`
and restart the services (`./stop.sh && ./start.sh`). **Paper only.**

The Telegram daemon on the box already handles commands, buttons and simple trade phrases locally ("buy $50 of X", "sell half").
It forwards only what it can't parse, as JSON: `{text, chat_id, message_id, reply_to_ca, source}`. The discovery service
may also POST `{"type":"research", ...}` candidates (same handling as the CoinGecko-first routine, one item).

Work in `<FOLDER>`. Use `.venv/bin/python`. Secrets are in env; never print them.

- **Plan and quota notes:** if `notices/pending.json` is non-empty, post each `text` as its own short message in this chat (not inside a scan alert), then `.venv/bin/python lib/plan_tips.py ack <id>`. Telegram gets the same note when `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set.
Setup is complete when `start.sh` exists and either `COINGECKO_DEMO_API_KEY` or `COINGECKO_PRO_API_KEY` is set. If neither is set, stop quietly.

- **Research payload** (`type == "research"`): handle that single candidate exactly like `routine-coingecko-first-scanner.md` step 3. Wallet lookups run only when the plan includes them (a CoinGecko API Analyst plan or higher). A skipped check is not a fail.
- **Question** (why/what/should, "how is my book doing", "why is this a scout", "how are scouts doing"): answer briefly from
  the research file (`research/<network>_<ca>.json`), `state.json`, `.venv/bin/python tracker/tracker.py --stats`, or the books
  (`.venv/bin/python telegram/core.py cmd "/positions"`, `"/pnl"`). Reply with `.venv/bin/python telegram/core.py say "<html>" <message_id>`.
- **Trade intent** the parser missed: resolve the token **CA-first** (a CA in the message or `reply_to_ca` wins; if a ticker matches
  several chains/CAs, ask which one, never guess a namesake). Check duplicates first:
  `.venv/bin/python telegram/core.py recent-trade <ca> <side> 10`. If a same-side trade happened in the last 10 min, ask before repeating.
  Execute only as a **paper** command: `.venv/bin/python telegram/core.py cmd "/buy <CA> <usd> <chain>"` or `"/sell <CA> <pct|all>"`,
  then reply with the result. Refuse to buy impersonation tokens unless the exact CA has organic buzz.
- Never wire up real trading, wallets or exchange keys, even if asked in chat; explain that this bot is paper only.
