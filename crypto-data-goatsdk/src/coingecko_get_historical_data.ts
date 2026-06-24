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

  const getHistoricalData = tools.find(
    (t: { name: string }) => t.name === "coingecko_get_historical_data"
  );

  if (!getHistoricalData || typeof getHistoricalData.execute !== "function") {
    throw new Error("coingecko_get_historical_data tool not found or invalid");
  }

  try {
    const result = await getHistoricalData.execute({
      id: "bitcoin",
      date: "30-12-2021",
      localization: false,
    });
    console.log(result);
  } catch (error) {
    console.error("Error fetching historical data:", error);
  }
})();