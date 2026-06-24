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