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

  const getTopGainersLosers = tools.find(
    (t: { name: string }) => t.name === "coingecko_get_top_gainers_losers"
  );

  if (!getTopGainersLosers || typeof getTopGainersLosers.execute !== "function") {
    throw new Error("coingecko_get_top_gainers_losers tool not found or invalid");
  }

  try {
    const result = await getTopGainersLosers.execute({
      vsCurrency: "usd",
      perPage: 10,
      page: 1,
    });
    console.log(result);
  } catch (error) {
    console.error("Error fetching top gainers and losers:", error);
  }
})();