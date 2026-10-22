# Routine: Telegram free-form handler (webhook)
Trigger: webhook. Optional. Instant replies to free-form Telegram questions and voice notes, and instant research on new candidates. Each POST is one routine run and uses Grok Bot quota. **Paper trading only.**

**If setup hasn't been completed, stop quietly.** Install dir: `D="${MEMESCAN_HOME:-$HOME/coingecko-grokbot-memecoin-scanner}"`. Setup is complete when `$D/start.sh` exists and `COINGECKO_DEMO_API_KEY` or `COINGECKO_PRO_API_KEY` is set. Never print a key.

Wiring (done once during setup): store this routine's webhook URL and key as `TELEGRAM_FORWARD_URL` and `TELEGRAM_FORWARD_KEY`, then `./stop.sh && ./start.sh` from `$D`.

The Telegram daemon already handles commands, buttons and simple trade phrases ("buy $50 of X", "sell half"). It forwards only what it can't parse, as JSON: `{text, chat_id, message_id, reply_to_ca, source}`. Discovery may also POST `{"type":"research", ...}`.

Work in `$D`. Use `.venv/bin/python`.

- **Plan and quota notes:** if `notices/pending.json` is non-empty, post each `text` as its own short message in this chat (not inside a scan alert), then `.venv/bin/python lib/plan_tips.py ack <id>`. These also go to Telegram when `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set. Credits used up and an invalid key are sent even when plan tips are off.

- **Research** (`type == "research"`): handle that one candidate like step 3 of the CoinGecko-first routine. Wallet look-ups run only when the plan includes them (a CoinGecko API Analyst plan or higher). A skipped check is not a fail. Then CA-first X buzz, the verdict, `alerts/send_card.py`, `scripts/assess.py record`, and `lib/fwdq.py done <ca>`.
- **Question** (why/what/should, "how is my book doing", "why is this a scout"): answer briefly from `research/<network>_<ca>.json`, `state.json`, `.venv/bin/python tracker/tracker.py --stats`, or `.venv/bin/python telegram/core.py cmd "/positions"` / `"/pnl"`. Reply with `.venv/bin/python telegram/core.py say "<html>" <message_id>`.
- **Trade intent the parser missed:** resolve **CA-first** (a CA in the message or `reply_to_ca` wins; if a ticker matches several chains, ask; never guess a namesake). Check `.venv/bin/python telegram/core.py recent-trade <ca> <side> 10` and ask before repeating a same-side trade from the last 10 min. Execute only as paper: `.venv/bin/python telegram/core.py cmd "/buy <CA> <usd> <chain>"` or `"/sell <CA> <pct|all>"`, then reply with the result. Refuse impersonation tokens (`auto/impersonation.json`) unless the exact CA has organic buzz.
- Empty or unrecognized payload: do nothing.

**Hard rules:** paper only. Never wire real trading, wallets, private keys or exchange keys unless the owner builds that and asks. Never print secrets. Answers are research, not financial advice.
