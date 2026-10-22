# Grok Bot template: what it sets up

The **CoinGecko Memecoin Scanner** Grok Bot template is a packaged bot: a getting-started chat, a few skills (playbooks),
starting memories and three routines (scheduled or webhook prompts). It does **not** ship files or keys. On first run the
getting-started chat clones this folder onto the bot's computer, asks the new owner for their own keys through secure
inputs and turns the routines on.

This folder holds the plain-text versions of those prompts so you can see exactly what the template does,
or recreate it by hand in any agent that can run shell commands on a schedule.

| File | Grok Bot piece | Default |
|---|---|---|
| [`getting-started.md`](getting-started.md) | First chat after importing the template | runs once |
| [`routine-coingecko-first-scanner.md`](routine-coingecko-first-scanner.md) | Scheduled routine: new pools on CoinGecko → wallet checks → X buzz → Telegram card | **ON**, every 15 min |
| [`routine-x-first-scanner.md`](routine-x-first-scanner.md) | Scheduled routine: X buzz → contract address → CoinGecko pool → same gates → card | off (turn on to scan both ways) |
| [`routine-telegram-handler.md`](routine-telegram-handler.md) | Webhook routine: free-form Telegram questions/voice the local parser can't handle (+ instant research) | optional |
| [`template/`](template/) | Same prompts, worded for pasting into the Grok Bot template (`utm_source=grokbot`) | — |

## Quota tip
Every routine run uses Grok Bot quota. The background services (price stream, discovery polling, stop-loss/trailing
exits, the AI book, the dashboard and Telegram buttons) run on the bot's computer and cost **no** Grok Bot quota;
only the AI steps (X searches, narratives, verdicts, chat replies) do.

- Run **one** scanner by default: CoinGecko-first *or* X-first.
- The more often a schedule runs, the faster quota depletes. 15 minutes is a balanced default; 30–60 minutes saves more.
- Turn on **both** scanners only if you're comfortable using more quota. The benefit is more frequent, two-sided coverage of the market.
- The webhook (`TELEGRAM_FORWARD_URL`) makes research instant, but every forwarded candidate or chat message is a routine run.

## Connectors the bot uses
- **CoinGecko MCP** and **CoinGecko Docs MCP**: live data lookups and up-to-date endpoint docs (https://docs.coingecko.com/ai-integration?utm_source=grokbot&utm_medium=referral&utm_campaign=grokbot-memecoin-scanner&utm_content=grokbot-readme-ai-tools). The remote MCP `https://mcp.pro-api.coingecko.com/mcp` needs a paid API key. Connect it only for a paid key. On a CoinGecko API Demo (free) key the scanner runs without it. The optional local `@coingecko/coingecko-mcp` package works with `COINGECKO_DEMO_API_KEY` and `COINGECKO_ENVIRONMENT=demo`. Do not use a keyless MCP server.
- A CoinGecko API Demo (free) key runs the core scan. Top-trader and wallet checks (spotting smart money vs bots) and Megafilter need a CoinGecko API Analyst plan or higher. The WebSocket price stream needs a CoinGecko API Basic plan or higher. See [`docs/PLANS.md`](../docs/PLANS.md).
- **X (Twitter)**: buzz checks by exact contract address. Only the agent calls X; scripts on the box never do.
- **Telegram**: through the bot token in env (the box talks to the Telegram Bot API directly).
