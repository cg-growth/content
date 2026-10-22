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
- A **CoinGecko API key on a paid plan, Analyst or higher** ([plans](https://www.coingecko.com/en/api/pricing?utm_source=github&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=agents-get-key)). The free Demo key won't work: onchain top traders/holders, wallet PnL and the WebSocket need a paid plan.
- A **Telegram bot token** from @BotFather (optional but recommended; without it there are no alerts or buttons).
- Agent connectors: **X** (for buzz checks), **CoinGecko MCP** and **CoinGecko Docs MCP** ([setup](https://docs.coingecko.com/ai-integration?utm_source=github&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=agents-ai-tools)).

## Steps
1. **Get the code**
   ```bash
   git clone --depth 1 --filter=blob:none --sparse https://github.com/cg-growth/content.git
   git -C content sparse-checkout set coingecko-grokbot-memecoin-scanner
   cd content/coingecko-grokbot-memecoin-scanner
   ```
2. **Install:** `./install.sh` (creates `.venv`, installs `requirements.txt`, creates empty databases; no keys needed).
3. **Keys:** request `COINGECKO_PRO_API_KEY` and `TELEGRAM_BOT_TOKEN` as secrets. On Grok Bot they arrive as env vars. Elsewhere,
   have the human write them to `~/.coingecko/keys.env` and `~/.grokbot-memecoin/keys.env` themselves (format in `.env.example`).
   Optional: `TELEGRAM_CHAT_ID`, `MEMESCAN_TZ` (IANA zone), `PAPER_START_CASH`.
4. **Ask preferences** (offer defaults): chains (default all four: `solana`, `base`, `bsc`, `robinhood` in `risk.json` → `discovery.networks`),
   scan cadence (default 15 min), which scanner (default CoinGecko-first only; both = more agent quota), risk settings in `risk.json`.
5. **Start:** `./start.sh`. It exits with a clear message if a key is missing. Then `./status.sh`; every line should say `up`
   within ~1 min (`telegram` stays DOWN if there's no token). Dashboard: `http://127.0.0.1:8787` (local only).
6. **Health check:** `tail -n 5 logs/discovery.log logs/stream.log`. Heartbeats with no `HTTP 401`/`Auth Failed` mean the key works.
   `HTTP 401` = wrong key, `HTTP 403`/`429` = plan or rate limit.
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
