# Build a Multi-Chain Crypto Wallet with Python and CoinGecko API

Companion code for the CoinGecko Learn guide [How to Build a Multi-Chain Crypto Wallet with Python and CoinGecko API](https://www.coingecko.com/learn/build-crypto-wallet-python).

A non-custodial wallet app in Python (Flask) that shows:

- **Portfolio:** every token a wallet holds across networks such as Ethereum, Base, BNB Chain and Robinhood, with USD value, 24h change and logos, from one call
- **Token detail:** a 30-day price chart
- **Activity:** trades labelled buy or sell, and transfers labelled in or out
- **Profit and loss:** realized and unrealized PnL per network and per token
- **Send and receive** on the Ethereum Sepolia testnet

The private key is created and kept in your browser (ethers.js). The Flask server never sees it. The server holds your API keys, calls CoinGecko API and forwards already-signed transactions to Sepolia.

## CoinGecko endpoints used

| Feature | Endpoint | Plan |
|---|---|---|
| Portfolio | [`/onchain/wallets/{address}/balances`](https://docs.coingecko.com/reference/wallet-token-balances) | Analyst and above |
| Activity | [`/onchain/networks/{network}/wallets/{address}/trades`](https://docs.coingecko.com/reference/wallet-trades), [`/transfers`](https://docs.coingecko.com/reference/wallet-token-transfers) | Analyst and above |
| PnL | [`/onchain/wallets/{address}/pnl`](https://docs.coingecko.com/reference/wallet-pnl) | Analyst and above |
| Logos | [`/coins/markets`](https://docs.coingecko.com/reference/coins-markets) | All plans |
| Price chart | [`/coins/{id}/market_chart`](https://docs.coingecko.com/reference/coins-id-market-chart) | All plans |

All calls use the official [CoinGecko Python SDK](https://docs.coingecko.com/docs/sdk-python) (`coingecko-sdk`).

With a free Demo key (`COINGECKO_PLAN=demo`), wallet creation, send and receive, and the price chart work. The portfolio, activity and PnL panels show an upgrade note instead.

## Quick start

Requires Python 3.9 or higher.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp env.example .env   # then fill in your keys
python app.py
```

Open http://localhost:5000. On macOS, if AirPlay Receiver already uses port 5000, run `PORT=5001 python app.py` and open http://localhost:5001.

The app loads a public sample address with activity on BNB Chain, Base, Robinhood and Ethereum. Enter any EVM address and click **Load wallet** to see your own.

## Configuration (`.env`)

| Variable | What it's for |
|---|---|
| `COINGECKO_API_KEY` | Your CoinGecko API key |
| `COINGECKO_PLAN` | `pro` for Analyst plan keys and above (default), `demo` for a Demo key |
| `INFURA_API_KEY` | Connects to Ethereum Sepolia for send and receive |
| `ETH_RPC_URL` | Optional: any Sepolia RPC URL, overrides `INFURA_API_KEY` |

Never commit your `.env` file.

**Troubleshooting:** the SDK also reads `COINGECKO_PRO_API_KEY` and `COINGECKO_DEMO_API_KEY` from your shell. If both are set, requests can go out with the wrong key and fail with a 400 "If you are using Demo API key…" error. Unset them, or use only `COINGECKO_API_KEY` in `.env`.

## Testing send and receive

1. Click **Create new wallet** and back up the private key it shows. It's kept only in that browser tab.
2. Fund the address with free Sepolia ETH from a faucet, such as the [Google Cloud Sepolia faucet](https://cloud.google.com/application/web3/faucet/ethereum/sepolia).
3. Enter a recipient and amount, then click **Sign and send**. The transaction is signed in the browser and the hash links to Sepolia Etherscan.

This is a learning project. Don't use it to hold real funds.

## Files

```
app.py                Flask back end: CoinGecko API calls and Sepolia relay
static/wallet.js      Front end: key creation and signing (ethers.js), UI
templates/index.html  Page layout
requirements.txt
env.example
```

## License

Apache 2.0
