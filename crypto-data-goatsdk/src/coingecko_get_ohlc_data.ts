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

  const getOHLCData = tools.find(
    (t: { name: string }) => t.name === "coingecko_get_ohlc_data"
  );

  if (!getOHLCData || typeof getOHLCData.execute !== "function") {
    throw new Error("coingecko_get_ohlc_data tool not found or invalid");
  }

  try {
    const result = await getOHLCData.execute({
      id: "bitcoin",
      vsCurrency: "usd",
      days: 7,
    });
    console.log(result);
  } catch (error) {
    console.error("Error fetching OHLC data:", error);
  }
})();