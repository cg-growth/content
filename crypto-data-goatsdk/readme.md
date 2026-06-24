> Read the full article: [How to Fetch Crypto Market Data Using GOATSDK](https://www.coingecko.com/learn/crypto-data-goatsdk)

# GOATSDK CoinGecko Tool

A TypeScript toolkit for fetching cryptocurrency market data using [GOATSDK](https://www.npmjs.com/package/@goat-sdk/core) and the [CoinGecko plugin](https://www.npmjs.com/package/@goat-sdk/plugin-coingecko). This repository provides modular scripts for accessing CoinGecko endpoints such as trending coins, top gainers/losers, historical data, OHLC candlestick data, and coin categories.

---

## Features

- Fetch trending coins and NFTs
- Get top gainers and losers
- Retrieve historical price and market data
- Access OHLC (candlestick) data for technical analysis
- List and analyze coin categories
- Modular, reusable wallet logic
- TypeScript-first, easy to extend

---

## Prerequisites

- **Node.js** (v16 or later)
- **TypeScript**
- **CoinGecko API Key** (Pro key required for some endpoints)
- [Goat SDK](https://www.npmjs.com/package/@goat-sdk/core) and [CoinGecko Plugin](https://www.npmjs.com/package/@goat-sdk/plugin-coingecko)

---

## Getting Started

1. **Clone the repository**
   ```sh
   git clone https://github.com/rollendxavier/goat-gecko-tool.git
   cd goat-gecko-tool
   ```

2. **Install dependencies**
   ```sh
   npm install
   ```

3. **Set up environment variables**

   Create a `.env` file in the root directory:
   ```
   COINGECKO_API_KEY=your_pro_api_key_here
   ```

4. **Build the project**
   ```sh
   npm run build
   ```

5. **Run an endpoint script**

   For example, to fetch top gainers and losers:
   ```sh
   node dist/getTopGainersLosers.js
   ```

   Or to fetch trending coins:
   ```sh
   node dist/getTrendingCoins.js
   ```

---

## Project Structure

```
src/
  wallet.ts
  getTopGainersLosers.ts
  getTrendingCoins.ts
  getHistoricalData.ts
  getOHLCData.ts
  coingecko_get_coin_categories.ts
.env
package.json
tsconfig.json
```

---

## Example Usage

Each script in the `src/` directory demonstrates how to call a specific CoinGecko endpoint using GOATSDK.  
All scripts share a reusable wallet module (`wallet.ts`) and a consistent initialization pattern.

**Example: Fetch Coin Categories**

```typescript
import { coingecko } from "@goat-sdk/plugin-coingecko";
import { getTools } from "@goat-sdk/core";
import dotenv from "dotenv";
import { wallet } from "./wallet.js";

dotenv.config();

(async () => {
  const tools = await getTools({
    wallet,
    plugins: [
      coingecko({
        apiKey: process.env.COINGECKO_API_KEY || "",
        isPro: true,
      }),
    ],
  });

  const getCoinCategories = tools.find(
    (t: { name: string }) => t.name === "coingecko_get_coin_categories"
  );

  if (!getCoinCategories || typeof getCoinCategories.execute !== "function") {
    throw new Error("coingecko_get_coin_categories tool not found or invalid");
  }

  try {
    const result = await getCoinCategories.execute({});
    console.log(result);
  } catch (error) {
    console.error("Error fetching coin categories:", error);
  }
})();
```

---

## Full Blog & Documentation

A comprehensive blog post is available in [`blog.md`](./blog.md), covering:

- Project setup and prerequisites
- How to use each endpoint
- Detailed input/output explanations
- Sample outputs for each API call
- Tips for extending and customizing the toolkit

You can read the full guide in [blog.md](./blog.md) or on [CoinGecko's Community Blog](https://coingecko.com/en/blog) (if published).

---

## License

MIT

---

## Contributing

Pull requests and suggestions are welcome! Please open an issue or submit a PR to contribute.

---

## Acknowledgements

- [CoinGecko API](https://www.coingecko.com/en/api/documentation)
- [GOATSDK](https://www.npmjs.com/package/@goat-sdk/core)

## Support the Project

If you find this project helpful, consider supporting it by donating cryptocurrency. Your support helps keep the project alive and maintained!

### Donation Wallets

- **Bitcoin (BTC):** `34rqfUFenX2EMvDfpn7phgiKdHbxTJ5Wuw`
- **Ethereum (ETH):** `0x0bB11fD9a3B8EfBd899325c2EA574e28E6E87cB2`
- **USDT (ERC-20):** `0x679c5733F4109283B46158AaD3a2C8981425c951`

Thank you for your support! 🙏