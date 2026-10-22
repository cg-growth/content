# AGENTS.md: setting up the CoinGecko Memecoin Scanner

Instructions for an AI agent (Grok Bot or any coding agent with a shell) installing and operating this folder for a human owner.

## Hard rules
- **Paper trading only.** Never wire live trading, wallets, private keys or exchange keys unless the human explicitly builds that themselves and asks for it.
- **Secrets stay secret.** Ask the human for keys through your platform's secure/masked secret input. Never echo, print, log, commit or paste a key into chat or into a file inside this repo. Keys live in env vars or in `~/.coingecko/keys.env` / `~/.grokbot-memecoin/keys.env` (outside the repo, `chmod 600`).
- **Never buy impersonation tokens** (stocks, big brands, celebrities, tokenized-stock words; list in `auto/impersonation.json`) unless the exact contract address has organic buzz on X.
- **CA-first token resolution.** A contract address in the message, or the alert being replied to, always wins over a ticker. If a ticker matches several chains/CAs, ask the human to pick. Never guess a namesake. Solana addresses are case-sensitive; EVM addresses are lowercased.
- If something needs a key you don't have, stop and ask. Don't work around a missing key.

## Prerequisites
- Linux or macOS with `bash`, `curl`, `git`, Python 3.10+ (`uv` optional, used if present).
- Chrome or Chromium for image cards (set `CHROME_BIN` if it isn't on PATH). Optional: `ffmpeg` for voice notes.
- A **CoinGecko API key**. A CoinGecko API Demo (free) key is enough to start. Top-trader and wallet checks (spotting smart money vs bots) and Megafilter need a CoinGecko API Analyst plan or higher. The WebSocket price stream needs a CoinGecko API Basic plan or higher. See [pricing](https://www.coingecko.com/en/api/pricing?utm_source=grokbot&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=agents-pricing) and [`docs/PLANS.md`](docs/PLANS.md). Never call CoinGecko without a key, and never use a keyless MCP server.
- A **Telegram bot token** from @BotFather (optional but recommended; without it there are no alerts or buttons).
- Agent connectors: **X** (for buzz checks), **CoinGecko Docs MCP**, and **CoinGecko MCP** for a paid key only ([setup](https://docs.coingecko.com/ai-integration?utm_source=grokbot&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=agents-ai-tools)). The remote MCP needs a paid API key. On a CoinGecko API Demo (free) key the scanner runs without it; the optional local `@coingecko/coingecko-mcp` package works with `COINGECKO_DEMO_API_KEY` and `COINGECKO_ENVIRONMENT=demo`. Never use a keyless MCP server.

## Steps
1. **Get the code**
   ```bash
   git clone --depth 1 --filter=blob:none --sparse https://github.com/cg-growth/content.git
   git -C content sparse-checkout set coingecko-grokbot-memecoin-scanner
   cd content/coingecko-grokbot-memecoin-scanner
   ```
2. **Install:** `./install.sh` (creates `.venv`, installs `requirements.txt`, creates empty databases; no keys needed).
3. **Keys:** ask early, in these words: "Do you have a paid CoinGecko API key, or would you like to start with a CoinGecko API Demo (free) key?" Then one line on the difference: a CoinGecko API Demo (free) key has its own rate limit; top-trader and wallet checks (spotting smart money vs bots) and Megafilter need a CoinGecko API Analyst plan or higher; the WebSocket price stream needs a CoinGecko API Basic plan or higher. A key is required because it gives the scanner its own rate limit, separate from the shared limit used when no key is sent. In your own words, name every plan in full, the same way this file does ("CoinGecko API Demo (free) key", "CoinGecko API Basic plan or higher", "CoinGecko API Analyst plan or higher"). Do not shorten a plan name to the tier word on its own. If they need a key and do not have a CoinGecko API account yet, send the pricing page so they can sign up for a CoinGecko API Demo (free) plan or a paid plan. CoinGecko's sign-up then opens the developer dashboard, where they copy the key: https://www.coingecko.com/en/api/pricing?utm_source=grokbot&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=agents-signup Do not send that person to the developer dashboard first. If they already have a CoinGecko API account, send the developer dashboard to copy the key: https://www.coingecko.com/en/developers/dashboard?utm_source=grokbot&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=agents-dashboard#api-keys Request `COINGECKO_DEMO_API_KEY` or `COINGECKO_PRO_API_KEY` (one of them) and `TELEGRAM_BOT_TOKEN` as secrets. On the CoinGecko key card, set the description to: "From your CoinGecko developer dashboard. New to CoinGecko API? Sign up on the CoinGecko API pricing page first." On Grok Bot they arrive as env vars. Elsewhere,
   have the human write them to `~/.coingecko/keys.env` and `~/.grokbot-memecoin/keys.env` themselves (format in `.env.example`).
   Optional: `TELEGRAM_CHAT_ID`, `MEMESCAN_TZ` (IANA zone), `PAPER_START_CASH` (one bankroll for both paper books; a book with no trades adopts it on startup, including when `./install.sh` already created the ledger at the default). Environment values win over the keys files. Write `PAPER_START_CASH` before `./start.sh`. Do not keep a second amount in `auto/policy.json`; startup copies this value there while the AI book has no trades. A book that already has trades is left as it is.
4. **Ask preferences** (offer defaults): chains (default all four: `solana`, `base`, `bsc`, `robinhood` in `risk.json` → `discovery.networks`; X-first uses that list),
   scan cadence (routine default 15 min; discovery poll `discovery.interval_s`, default 60s — the owner picks both, including a slower discovery interval on a CoinGecko API Demo (free) key), which scanner (default CoinGecko-first only; both = more agent quota), risk settings in `risk.json`.
   Set `plan_tips.enabled` to false if they do not want plan-related tips. Wallet lookups in the routines run only when `./status.sh` shows those checks are on the plan. A skipped wallet check is not a fail.
5. **Start:** `./start.sh`. It exits with a clear message if a key is missing. Then `./status.sh`; every line should say `up`
   within ~1 min (`telegram` stays DOWN if there's no token). Dashboard: `http://127.0.0.1:8787` (local only).
6. **Health check:** `tail -n 5 logs/discovery.log logs/stream.log`. Heartbeats with no rejected-key line mean the key works.
   Error 10002, 10010, or 10011 = rejected key. HTTP 401 whose body says the call is exclusive to the CoinGecko API Analyst plan, or error 10005, = that call is not on this plan (the scan continues). `HTTP 429` = rate limit or monthly credits. On 429 the services log it, send a short note (Telegram when `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set, and `notices/pending.json` for this chat), and keep the same schedule. Relay each pending note as its own message, then `.venv/bin/python lib/plan_tips.py ack <id>`.
   On a CoinGecko API Demo (free) key, `./start.sh` prints a credit estimate from `lib/credits.py`. Read it to the owner and let them keep `discovery.interval_s` or pick a slower one. Do not change it yourself.
7. **Telegram owner:** ask the human to send `/start` to their bot ("✅ Owner registered"), unless `TELEGRAM_CHAT_ID` is set.
8. **Enable scanners:** schedule the prompts in [`grokbot/`](grokbot/) (replace `<FOLDER>` with this folder's absolute path):
   - `routine-coingecko-first-scanner.md`: ON by default, every 15 min.
   - `routine-x-first-scanner.md`: only if chosen.
   - Without a scheduler, run the same prompt by hand whenever you want a scan.
9. **Optional Telegram webhook:** create a webhook-triggered routine from `grokbot/routine-telegram-handler.md`, store its URL and key as
   `TELEGRAM_FORWARD_URL` / `TELEGRAM_FORWARD_KEY`, then `./stop.sh && ./start.sh`. Without it, research waits in `pending_research.json`
   for the scheduled scan, and unparsed chat gets a usage hint.

## Operating notes
- Use `.venv/bin/python` for every script. All paths are relative to this folder (override with `MEMESCAN_HOME`).
- Runtime data (`*.db`, `state.json`, `research/`, `logs/`, `log.md`) is git-ignored. Never commit it.
- Write verdicts with `scripts/assess.py record` and run summaries with `scripts/assess.py log` (locked, atomic writes).
- Paper commands for chat requests: `.venv/bin/python telegram/core.py cmd "/buy <CA> <usd> <chain>"`. Check `telegram/core.py recent-trade <ca> <side> 10` first.
- Background services cost no agent quota; routine runs do. Prefer one scanner and a 15–60 min cadence.
- Use the CoinGecko Docs MCP to check current endpoints before changing any API call; keep changes small and tell the human.
- Stop everything: `./stop.sh` (data is kept).
