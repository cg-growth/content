import { SolanaAgentKit, createSolanaTools } from "solana-agent-kit";
import { ChatOpenAI } from "@langchain/openai";
import { createReactAgent } from "@langchain/langgraph/prebuilt";
import { MemorySaver } from "@langchain/langgraph";
import * as dotenv from "dotenv";
import * as bs58 from "bs58";

dotenv.config();

// Ensure the private key is Base58 encoded and decode it if necessary
const privateKeyBase58 = process.env.SOLANA_PRIVATE_KEY!;
let decodedPrivateKey: Uint8Array;

// Attempt to decode the private key to ensure it's in the correct format
try {
  decodedPrivateKey = bs58.default.decode(privateKeyBase58);
  if (decodedPrivateKey.length !== 64) {
    throw new Error(
      "Invalid Solana private key length. It should be 64 bytes."
    );
  }
} catch (error) {
  console.error("Error decoding private key:", error);
  throw error;
}

// We export this so that we can access CoinGecko through the Agent Kit
export const solanaKit = new SolanaAgentKit(
  privateKeyBase58,
  process.env.RPC_URL!,
  {
    OPENAI_API_KEY: process.env.OPENAI_API_KEY,
    COINGECKO_PRO_API_KEY: process.env.COINGECKO_PRO_API_KEY,
    COINGECKO_DEMO_API_KEY: process.env.COINGECKO_DEMO_API_KEY,
    PERPLEXITY_API_KEY: process.env.PERPLEXITY_API_KEY,
  }
);

export async function initializeAgent() {
  const llm = new ChatOpenAI({
    modelName: "gpt-4o", // Adjust as needed, depending on the model you are using
    temperature: 0.7, // Adjust the temperature for creativity/variance in responses
  });

  const memory = new MemorySaver();
  const config = { configurable: { thread_id: "Solana Agent Kit!" } };
  const tools = createSolanaTools(solanaKit);

  return createReactAgent({
    llm,
    tools,
    checkpointSaver: memory,
  });
}
