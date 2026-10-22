<p align="center"><img src="assets/coingecko-logo.png" alt="CoinGecko" height="40"></p>

<h1 align="center">CoinGecko API × Grok Bot: Memecoin Scanner</h1>
<p align="center"><b>New pairs and X buzz in. Wallet-checked, paper-traded memecoin calls out.</b></p>

> Paper trading only. Not financial advice. Always DYOR.

A 24/7 memecoin research desk that runs on your own Grok Bot (or any machine). It finds brand-new pools across **Solana, Base, BSC and Robinhood Chain** with [CoinGecko's onchain API](https://www.coingecko.com/en/api?utm_source=grokbot&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=readme-intro), checks who's actually buying (humans, bots, bundles, insiders, smart money), confirms the buzz on X by exact contract address, and sends you a Telegram card with buy/skip buttons. Every trade is **paper**: a human-in-the-loop book you drive from Telegram, plus a fully autonomous AI book next to it so you can compare.

Built on the CoinGecko API. Not a CoinGecko product, not financial advice. See [Disclaimer](#disclaimer).

## What it does

| Feature | What it does |
|---|---|
| **CoinGecko-first scanner** | Polls new pools on every enabled chain at `discovery.interval_s` (default 60s). Megafilter runs on a CoinGecko API Analyst plan or higher; other plans also poll trending pools and use the same local filters. Deep research reads token info, pool trades and, when the plan includes them, holders, top traders and wallet mix before the AI writes a verdict. |
| **X-first scanner** | The reverse: catches contract addresses people are posting on X, resolves the CoinGecko pool and runs the same gates and wallet checks. |
| **Telegram alerts** | Chart cards with sized Buy / 0.5x / 2x / Skip / Mute buttons, `/positions`, `/portfolio`, `/report`, free-form chat and voice notes ("buy $50 of it", "sell half"). |
| **Human paper book** | $10,000 paper bankroll. Constant-product fills with DEX fees, slippage and per-chain gas. Automatic stop-loss, breakeven, trailing stop, danger and rug exits; take-profit "clips" that ask first (or Auto-clip per position). |
| **Scout tier** | Lower-conviction "near-miss" cards (soft fails + strong momentum), rate-limited, smaller size, with the reasons they missed. |
| **AI autonomous book** | A separate $10,000 paper book that enters and exits on its own with a bounded self-tuning policy. `/auto` and `/compare` show human vs AI. |
| **Entry filters** | Impersonation block (stocks, brands, celebrities, tokenized-stock words), exact-CA buzz requirement, fragile-pool guard (age < 10 min, live liquidity < $10k), winner-profile sizing. |
| **Tick sanitation** | Rejects bad price prints (wrong pool, dust trades, unit mismatches, unconfirmed spikes) before they can trigger exits or fake wins. |
| **Price stream** | WebSocket on a CoinGecko API Basic plan or higher (candles, trades, price and reserve). On a CoinGecko API Demo (free) key, token prices are polled over REST at `stream.poll_interval_s` (default 60s). |
| **Wallet database** | Labels wallets (smart money, sniper, flipper, bot, insider, bundle clusters) from CoinGecko wallet PnL and trades when the plan includes those endpoints (a CoinGecko API Analyst plan or higher), and reuses them across tokens. |
| **Dashboard** | Local read-only web dashboard: verdicts, books, AI policy, stream status. |

## Why

New memecoin pools appear every few seconds and most are bots, bundles or copycats. CoinGecko's onchain data (new pools, holders, top traders, wallet PnL, live trades) is detailed enough to tell real early demand from manufactured volume, and an AI agent can do the part scripts can't: read the room on X and write the call. This folder wires the two together end to end, with paper money, so you can see how it behaves before trusting any of it.

## Run it with Grok Bot

The easiest path: import the Grok Bot template. Its getting-started chat installs this folder on your bot's computer, asks for your keys through secure inputs, and sets up the routines.

TEMPLATE_LINK_TBD

What the template contains (routines, prompts, first-run chat) is documented in plain text in [`grokbot/`](grokbot/).

## Run it yourself

```bash
git clone https://github.com/cg-growth/content.git
cd content/coingecko-grokbot-memecoin-scanner
./install.sh   # once: Python env + deps (uv if present, else venv + pip) + empty local databases
./start.sh     # starts everything; dashboard on http://127.0.0.1:8787
./status.sh    # what's running
./stop.sh      # stop (data is kept)
```

- Needs Python 3.10+, `bash`, `curl`, and Chrome/Chromium for image cards (`CHROME_BIN` to point at it). Optional voice notes: `WITH_VOICE=1 ./install.sh` + `ffmpeg`.
- The services do the data work on their own. The **AI judgment** steps (X buzz checks, narratives, verdicts) are run by an agent on a schedule: Grok Bot routines, or any coding agent following [`AGENTS.md`](AGENTS.md) and the prompts in [`grokbot/`](grokbot/).
- Tests (offline, mocked): `cd telegram && ../.venv/bin/python tests/test_bridge.py` and `.venv/bin/python tests/test_free_tier.py`.
- Tune everything in `risk.json` (human book, discovery, Scout) and `auto/policy.json` (AI book).

## Free vs paid CoinGecko API key

Choose the plan that fits how you want to run the scanner. A key is required on every plan. A CoinGecko API Demo (free) key has its own rate limit, separate from the shared limit used when no key is sent ([errors and rate limits](https://docs.coingecko.com/docs/errors-and-rate-limits?utm_source=grokbot&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=readme-rate-limits)). This scanner never calls CoinGecko without a key.

Figures below are from the [pricing](https://www.coingecko.com/en/api/pricing?utm_source=grokbot&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=readme-pricing) compare table and FAQ (checked 22 Oct 2026) and from the API docs. Dollar prices change; use the pricing page for the current ones.

| | CoinGecko API Demo (free) | CoinGecko API Basic | CoinGecko API Analyst and higher |
|---|---|---|---|
| Call credits / month | 10,000 | 100,000 | 500,000 on the CoinGecko API Analyst plan (more on Lite, Pro, Enterprise) |
| Rate limit / minute | 100 | 300 | 500 on the CoinGecko API Analyst plan |
| Price (pricing page) | $0, attribution required | from $35/mo; compare table shows $29/mo billed yearly | compare table shows the CoinGecko API Analyst plan at $103.20/mo billed yearly |
| New pools, trending pools, pool data, token info, OHLCV, recent trades | Yes | Yes | Yes |
| Top traders, top holders, holder history, wallet PnL and trades, Megafilter | No. Marked "not included with a CoinGecko API Demo (free) key" and not treated as a failed scan. | No. Those endpoints need a CoinGecko API Analyst plan or higher ([endpoint overview](https://docs.coingecko.com/reference/endpoint-overview?utm_source=grokbot&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=readme-endpoint-overview), 💼). | Yes |
| Prices for open paper positions | REST poll (`stream.poll_interval_s`, default 60s) | WebSocket (5 sockets on the CoinGecko API Basic plan) | WebSocket (10 sockets on the CoinGecko API Analyst plan) |

WebSocket availability is from [data delivery methods](https://docs.coingecko.com/docs/data-delivery-methods?utm_source=grokbot&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=readme-delivery): a CoinGecko API Demo (free) key has no WebSocket; a CoinGecko API Basic plan or higher does. Pool trades on a CoinGecko API Demo (free) key return the last 300 trades from the past 24 hours ([pool trades](https://docs.coingecko.com/demo/reference/pool-trades-contract-address?utm_source=grokbot&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=readme-pool-trades)).

Set `COINGECKO_DEMO_API_KEY` or `COINGECKO_PRO_API_KEY` (one of them). `./start.sh` detects the plan and picks the host and header. A CoinGecko API Demo (free) key placed in `COINGECKO_PRO_API_KEY` still works. Existing paid installs keep using `COINGECKO_PRO_API_KEY`.

`discovery.interval_s` in `risk.json` is the discovery poll, in seconds. You can set any value; the scanner does not change it. With the default four networks, each cycle is one new-pools call per network, plus Megafilter on a CoinGecko API Analyst plan or higher (5 calls) or trending pools on other plans (another call per network). At 20 seconds that is about 648,000 Megafilter-inclusive calls a month, which is above the CoinGecko API Analyst plan's 500,000 credits. The default is 60 seconds, about 216,000 of those listing calls a month. On a CoinGecko API Demo (free) key, follow-up reads add more: a measured run at 60 seconds and four networks used about 17 credits a minute, so 10,000 monthly credits last about 10 hours. `lib/credits.py` prints the estimate for the interval and chains in `risk.json`. When the rate limit or the monthly credits run out (HTTP 429), the scanner tells you and keeps the same schedule.

A CoinGecko API Basic plan or higher reads credit usage from CoinGecko `GET /key` (startup, about hourly, and after HTTP 429). One note is sent around 90% of the month, and one when credits are used up. A CoinGecko API Demo (free) key has no `GET /key`; a used-up month is detected from the API error, and the local call count is labeled as an estimate. `/usage` shows the same figures. Set `plan_tips.enabled` to false to hide plan-related tips. Credits used up and a rejected key still send, once per event. Other notes are at most once a day. Each note is its own message on Telegram (when `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set) and in the Grok Bot chat. See [`docs/PLANS.md`](docs/PLANS.md).

## Get your keys

1. **CoinGecko API key** (a CoinGecko API Demo (free) key or a paid key).
   - **No CoinGecko API account yet:** [sign up on the CoinGecko API pricing page](https://www.coingecko.com/en/api/pricing?utm_source=github&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=readme-signup) for a CoinGecko API Demo (free) plan or a paid plan. Sign-up opens the developer dashboard, where you copy the key.
   - **Already have a CoinGecko API account:** [copy the key from the developer dashboard](https://www.coingecko.com/en/developers/dashboard?utm_source=github&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=readme-get-key#api-keys).
   API reference: [docs](https://docs.coingecko.com/?utm_source=github&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=readme-docs).
2. **Telegram bot token**: in Telegram, message **@BotFather**, send `/newbot`, and copy the token. After starting, send `/start` to your bot from your own account to become its owner (or set `TELEGRAM_CHAT_ID`).

Save them where `start.sh` looks (never inside this repo, never committed):

```bash
mkdir -p ~/.coingecko ~/.grokbot-memecoin
echo 'COINGECKO_DEMO_API_KEY=your_demo_key_here' >> ~/.coingecko/keys.env
# or: echo 'COINGECKO_PRO_API_KEY=your_paid_key_here' >> ~/.coingecko/keys.env
echo 'TELEGRAM_BOT_TOKEN=your_token_here'  >> ~/.grokbot-memecoin/keys.env
chmod 600 ~/.coingecko/keys.env ~/.grokbot-memecoin/keys.env
```

On Grok Bot, store them as secrets instead; they arrive as environment variables. `start.sh` keeps those and uses a keys file only for names that are still empty. All optional settings are listed in [`.env.example`](.env.example).

## Quota tip

Grok Bot routines use your Grok Bot usage quota every time they run. The background services (stream, discovery polling, exits, AI book, dashboard, Telegram buttons) run on the machine and don't.

- By default, run **one** scanner: **CoinGecko-first** (new pairs on CoinGecko, then check the buzz on X) **or** **X-first** (start from the buzz on X, then use CoinGecko price, pool and wallet data to see if it's still early).
- The more often a schedule runs, the faster your quota depletes. Every 15 minutes is the default; 30 or 60 minutes saves more.
- Turn on **both** only if you're comfortable using more quota. The benefit is more frequent, two-sided coverage of the market.
- The optional Telegram webhook makes research and chat replies instant, but each forwarded message is a routine run.

## CoinGecko AI tools

CoinGecko publishes [AI integrations](https://docs.coingecko.com/ai-integration?utm_source=grokbot&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=readme-ai-tools) built for agents like this one:

- **CoinGecko MCP**: live CoinGecko data as tools, for ad-hoc lookups during research (prices, pools, tokens, wallets).
- **CoinGecko Docs MCP**: searchable, always-current API docs. When an endpoint changes or a new one ships, the agent reads the docs instead of guessing.
- **CoinGecko API agent skill (SKILL)**: a playbook that teaches agents how to call the API well.

The getting-started chat connects these. Because the agent can read current docs, it can fix a broken call or adopt a new endpoint when CoinGecko adds features (for example, a new chain or wallet endpoint) without waiting for this repo to change. Review its changes before relying on them.

## From paper to live (if you choose to)

This repo ships **paper trading only** and has no code path to real funds. If you ever consider going live, start with paper, stay there until the results and your own judgment hold up over many trades, and treat the move as its own project that you research and build responsibly.

At a high level:

- **The seam.** The paper fill engine (the buy/sell/clip functions that simulate fills) is where a real executor would plug in. Everything upstream (discovery, verdicts, sizing, risk exits) stays the same.
- **Centralized exchange route.** A trading API with keys limited to trade-only (no withdrawals) and restricted to your IP addresses.
- **Onchain (DEX) route.** A dedicated hot wallet holding only money you can afford to lose, a swap aggregator or router, transaction signing, slippage limits, MEV protection and priority fees. Memecoins add honeypots, taxes and thin liquidity on top.
- **Guardrails.** Start with tiny sizes, keep a kill switch, keep the same position and exposure limits, and log every decision and fill.

None of this is a recommendation of any exchange, wallet or tool. Live trading is risky and entirely your responsibility.

## Disclaimer

This is a demo built on the CoinGecko API. It's not a CoinGecko product, and nothing here is investment advice. All trading in this repo is simulated (paper). Verdicts, narratives and wallet labels are AI and heuristic outputs working from CoinGecko and X data, and may be wrong, late or incomplete. Memecoins are extremely risky; many are scams. Do your own research before relying on any of it.

## Links

- [Pricing](https://www.coingecko.com/en/api/pricing?utm_source=github&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=readme-links-pricing): sign up for a CoinGecko API Demo (free) plan or a paid plan, and compare tiers
- [Developer Dashboard](https://www.coingecko.com/en/developers/dashboard?utm_source=github&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=readme-links-api#api-keys): copy an API key when you already have a CoinGecko API account
- [API docs](https://docs.coingecko.com/?utm_source=grokbot&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=readme-links-docs): full reference
- [AI integrations](https://docs.coingecko.com/ai-integration?utm_source=grokbot&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=readme-links-ai-tools): CoinGecko MCP, Docs MCP, agent skill
- [GeckoTerminal](https://www.geckoterminal.com/?utm_source=grokbot&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=readme-links-geckoterminal): live DEX charts
- Docs in this folder: [`docs/PLANS.md`](docs/PLANS.md), [`docs/REALTIME.md`](docs/REALTIME.md), [`docs/XFIRST.md`](docs/XFIRST.md), [`docs/SCOUT.md`](docs/SCOUT.md), [`docs/MULTICHAIN.md`](docs/MULTICHAIN.md), [`docs/AUTO_BOOK.md`](docs/AUTO_BOOK.md)

## Maintained by

CoinGecko Growth team.
