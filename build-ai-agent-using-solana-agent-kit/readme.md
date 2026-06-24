> Read the full article: [How to Build an AI Agent with SendAI's Solana Agent Kit](https://www.coingecko.com/learn/build-ai-agent-using-solana-agent-kit)

# Solana AI Agent Kit CLI
This project uses a simple CLI Interface to interact with the Solana Agent Kit.
Through this interface you may: query wallet balances, send and swap tokens and even deploy new tokens on Solana using the AI Agent.

## Getting Started
- rename `.env.example` to `.env`
- paste in the required credentials
- run `npm i`
- run the tool with `ts-node index.ts`
- choose between `chat` and `token` mode. The `chat` option will start an AI Agent chat session, while `token` will use the CoinGecko API to fetch token information.