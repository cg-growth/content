# CoinGecko Agent SKILL

An installable package that gives AI agents built-in knowledge of the [CoinGecko API](https://www.coingecko.com/en/api), including endpoints, parameters, and common workflows.

- Instead of manually explaining the API to your agent every time, the **SKILL lets your agent understand CoinGecko data instantly** and respond with accurate queries and code.
- Works with popular AI coding agents and tools such as **Claude Code**, **Gemini CLI**, **Codex CLI**, and other SKILL-compatible agents. Setup takes less than 3 minutes.

📖 Full documentation: [docs.coingecko.com/docs/skills](https://docs.coingecko.com/docs/skills)

---

## Installation

### Claude.ai

1. Download the SKILL package: [skills-main.zip](https://github.com/coingecko/skills/archive/refs/heads/main.zip)
2. Go to [claude.ai/customize/skills](https://claude.ai/customize/skills)
3. Click **+** → **Upload a skill**
4. Upload the `skills-main.zip` file

> [!NOTE]
> Claude.ai users on paid plans should add `api.coingecko.com` and `pro-api.coingecko.com` to their domain allowlist at [claude.ai/settings/capabilities](https://claude.ai/settings/capabilities).<br/><br/>
> Follow this guide here: http://docs.coingecko.com/docs/skills#allowlist-coingecko-domains-claude-paid-plans-only

### Agents / LLMs

*Such as Claude Code, Gemini CLI, Codex CLI*

#### Via [skills.sh](https://skills.sh/)

```bash
npm install -g skills
npx skills add coingecko/skills -g -y
```

*`-g` flag installs globally for all agents. See [npmjs/skills](https://www.npmjs.com/package/skills) for more details.*

#### Via GitHub

```bash
git clone https://github.com/coingecko/skills.git coingecko-skills

# Move to your agent's skills directory (example: Claude Code on Mac/Linux)
mv coingecko-skills ~/.claude/skills/coingecko
```

*The exact path may vary based on your agent and operating system.*

---

## What's Inside

```
SKILL.md                     # Main entry point — workflow, reference index
references/
  ├── core.md                    # Auth, rate limits, methodology (always read)
  ├── claude-env.md              # Claude-specific constraints & workarounds
  ├── common-use-cases.md        # Common workflows for price queries, historical data, etc.
  ├── coins.md                   # Prices, market data, metadata, gainers/losers
  ├── coin-history.md            # Historical charts, OHLC, time-range queries
  ├── coin-supply.md             # Circulating/total supply charts
  ├── contract.md                # Lookup by token contract address
  ├── asset-platforms.md         # Supported blockchains for token contracts, token lists
  ├── categories.md              # Coin categories & sector market data
  ├── exchanges.md               # Spot & DEX exchange data, volume charts
  ├── derivatives.md             # Derivatives exchanges & tickers
  ├── treasury.md                # Public company crypto treasury holdings
  ├── nfts.md                    # NFT collections, market data, charts
  ├── global.md                  # Global market stats & DeFi data
  ├── utils.md                   # Search, trending, exchange rates, API status
  ├── onchain-networks.md        # Supported networks and DEXes (ID mapping)
  ├── onchain-pools.md           # Pool discovery, trending/new pools
  ├── onchain-tokens.md          # Token data, holders, traders
  ├── onchain-ohlcv-trades.md    # Onchain OHLCV and trade data
  └── onchain-categories.md      # Onchain category data (GeckoTerminal specific)
```

---

## Try It Out

Once installed, try asking your agent questions like:

> *"If I invested $100 in Bitcoin back in December 2018, how much would it be worth today?"*

> *"What was the ATH of XPL?"*

> *"What is the current market cap of DZnQi17HFgSM8mJ4nhVicz32B97XyTsd6MUVuDJgP9Jo from Solana?"*

> *"What if I only left $50 in my wallet? Which coins should I buy to maximize my returns based on the current market?"*

> *"What are the top NFT collections this week?"*

Have fun experimenting!

---

## Feedback

Tell us how you're using the CoinGecko SKILL and what we should improve — reach out to `eason.lim@coingecko[dot]com`.

or open a GitHub issue: [coingecko/skills/issues](https://github.com/coingecko/skills/issues/new?labels=community)

---

## License

[MIT](LICENSE)