> Read the full article: [How to Build a Comprehensive Crypto Token Search Engine](https://www.coingecko.com/learn/build-crypto-token-search-engine)

# Crypto Token Search Engine

A SvelteKit + TypeScript web app that lets users search for crypto tokens and on-chain liquidity pools in real time using the CoinGecko Pro API.

## What's inside

- **`src/providers/CoinGecko.ts`** — API client wrapping `/search` (coins) and `/onchain/search/pools` (DEX pools)
- **`src/lib/CoinList.svelte`** — renders coin search results
- **`src/lib/OnchainPoolList.svelte`** — renders on-chain pool results with network filtering
- **`src/routes/+page.svelte`** — main search UI

## Requirements

- Node.js 18+
- CoinGecko Pro API key ([get one here](https://www.coingecko.com/en/api))

## Getting started

```bash
npm install
```

Create a `.env` file:

```
CG_API_KEY=your_api_key_here
```

```bash
npm run dev
```

Open `http://localhost:5173` in your browser.

## Stack

- [SvelteKit](https://kit.svelte.dev/) + TypeScript
- [Tailwind CSS](https://tailwindcss.com/) + Flowbite
- [CoinGecko Pro API](https://www.coingecko.com/en/api)
