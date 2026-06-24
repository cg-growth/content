> Read the full article: [How to Build a Crypto Prediction Market App](https://www.coingecko.com/learn/build-a-crypto-prediction-market-app)

**Prediction Markets (CoinGecko)**

A lightweight Svelte app showcasing on-chain token cards and simple prediction market data powered by CoinGecko data and local sample data.

**Features**
- **Overview:** Displays token info and prediction markets in a compact UI.
- **Local data:** Uses sample markets in `src/lib/data/prediction_markets.json`.
- **Services:** API logic lives in `src/lib/services` and provider in `src/providers`.

**Quick Start**
- **Install dependencies:**
```bash
npm install
```
- **Run development server:**
```bash
npm run dev
```
- **Build for production:**
```bash
npm run build
```
- **Preview production build:**
```bash
npm run preview
```

**Project Structure**
- **Components & UI:** `src/lib/` contains Svelte components such as `OnChainTokenCard.svelte` and `MarketCard.svelte`.
- **Data:** Sample prediction markets: [src/lib/data/prediction_markets.json](src/lib/data/prediction_markets.json)
- **Services:** API wrappers in `src/lib/services` (e.g. `OddsService.ts`, `PredictionMarketService.ts`).
- **Provider:** CoinGecko provider: [src/providers/CoinGecko.ts](src/providers/CoinGecko.ts)

**Environment & Notes**
- This project requires a `.env` file for runtime configuration. Environment variables are loaded via `src/loadEnv.ts`.

- Create a `.env` at the project root with Vite-compatible keys (prefix with `VITE_` to expose to the client). Example:
COINGECKO_API_KEY = "KEY_HERE"

**Development**
- Code style and tooling are configured via `tsconfig.json`, `vite.config.ts`, and `svelte.config.js`.
- To run TypeScript checks or linters, use your local editor tooling or run the configured scripts if present in `package.json`.

**Contributing**
- Open an issue or submit a PR. Small, focused changes are preferred.

**License**
- See the project root for license details (add one if missing).

