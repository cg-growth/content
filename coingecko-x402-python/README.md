# CoinGecko X402 Python Test Scripts (Production)

<div align="center">

![CoinGecko](https://mintcdn.com/coingecko/i9l2MT4etZGYjSx8/assets/logos/dark.png?fit=max&auto=format&n=i9l2MT4etZGYjSx8&q=85&s=f5bfd88b8b98c4f45b6a1738bd7d8e44)

**Production-ready X402 test scripts for CoinGecko's pay-per-use API endpoints**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

---

## What is X402?

**X402** is an open payment protocol developed by Coinbase that enables instant, automatic stablecoin payments directly over HTTP. It allows applications to access paid APIs without subscriptions or API keys.

**How it works:**
1. Your app makes a request to an X402-enabled endpoint
2. The server returns a `402 Payment Required` response with payment details
3. Your wallet signs a USDC authorization for the requested amount
4. The request is retried with the payment signature
5. You receive the data you requested

Learn more: [X402 Documentation](https://docs.cdp.coinbase.com/x402/welcome)

---

## Prerequisites

Before running these scripts, you'll need:

- **Python 3.9+** installed
- **An EVM wallet** with USDC on Base network
- **Private key** for the wallet (use a test wallet with minimal funds)

### Getting USDC on Base

1. Bridge USDC from Ethereum to Base using [Base Bridge](https://bridge.base.org/)
2. Or purchase USDC directly on Base via [Coinbase](https://www.coinbase.com/)

> 💵 **Cost**: Each API call costs **$0.01 USDC**. Running all tests will cost approximately **$0.05 USDC**.

---

## Installation

### Option 1: Run on Replit (Recommended for Testing)

1. Fork this repository to your GitHub
2. Import into [Replit](https://replit.com/) from GitHub
3. Add your `EVM_PRIVATE_KEY` to Replit Secrets
4. Click "Run"

### Option 2: Local Installation

```bash
# Clone the repository
git clone https://github.com/cg-brianlsh/coingecko-x402-python-v3.git
cd coingecko-x402-python-v3

# Install dependencies (IMPORTANT: must use x402[evm,httpx])
pip install -r requirements.txt

# Set up your environment
cp .env.example .env
# Edit .env and add your EVM_PRIVATE_KEY

# Run the main test suite
python main.py
```

---

## Important: Correct Dependencies

The `requirements.txt` must include `x402[evm,httpx]` (not just `x402[httpx]`).

The `[evm]` extra is **required** to enable the `x402.mechanisms.evm` module. Without it, you'll see this error:

```
EVM signers require eth_account and web3. Install with: pip install x402[evm]
```

If you encounter this error, run:

```bash
pip install "x402[evm,httpx]>=0.1.0"
```

---

## Project Structure

```
coingecko-x402-python-v3/
├── main.py                 # Main test script (runs all endpoints)
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── README.md               # This file
└── examples/               # Individual endpoint test scripts
    ├── test_simple_price.py
    ├── test_simple_token_price.py
    ├── test_search_pools.py
    ├── test_trending_pools.py
    └── test_token_data.py
```

---

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `EVM_PRIVATE_KEY` | Your Base/EVM wallet private key | Yes (for EVM) |
| `SOLANA_PRIVATE_KEY` | Your Solana wallet private key | Yes (for Solana) |
| `NETWORK` | Force network: `evm` or `solana` | No (auto-detects) |

### Supported Networks

| Network | Private Key Env | Package Extra |
|---------|----------------|---------------|
| Base (EVM) | `EVM_PRIVATE_KEY` | `x402[evm]` |
| Solana | `SOLANA_PRIVATE_KEY` | `x402[svm]` |

---

## Available Endpoints

| Endpoint | Description | Example Parameters |
|----------|-------------|-------------------|
| `/simple/price` | Get prices for CoinGecko-listed coins | BTC, ETH, SOL |
| `/onchain/simple/networks/{network}/token_price/{address}` | Get token price by contract | WETH on ETH |
| `/onchain/search/pools` | Search pools by query | "pump" on Solana |
| `/onchain/networks/{network}/trending_pools` | Get trending pools | Base network |
| `/onchain/networks/{network}/tokens/{address}` | Get token data | USDT on ETH |

### URL Format

X402 endpoints use the path `/x402/` in the URL:

```
https://pro-api.coingecko.com/api/v3/x402/{endpoint}
```

Example:
```
https://pro-api.coingecko.com/api/v3/x402/simple/price?vs_currencies=usd&ids=bitcoin
```

---

## Usage

### Run All Tests

```bash
python main.py
```

### Run a Specific Test

```bash
python main.py simple_price
python main.py token_price
python main.py search_pools
python main.py trending_pools
python main.py token_data
```

---

## Payment Flow

This implementation follows the standard X402 flow using payment requirements returned in the response headers.

---

## License

MIT License - see [LICENSE](LICENSE) file.

---

## Links

- [CoinGecko x402 API Documentation](https://docs.coingecko.com/docs/x402)
- [X402 Protocol Documentation](https://docs.cdp.coinbase.com/x402/welcome)
- [x402 Python Package](https://pypi.org/project/x402/)
