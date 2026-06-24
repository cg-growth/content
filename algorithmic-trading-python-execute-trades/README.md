> Read the full article: [Algorithmic Trading with Python: How to Execute Trades on a DEX](https://www.coingecko.com/learn/algorithmic-trading-python-execute-trades)

# Algorithmic Trading with Python: DEX Execution

A Jupyter notebook walkthrough for tracking trading activity across DEX pools using CoinGecko's on-chain API and executing swaps on Uniswap.

## What's inside

- `Trade_on_uniswap.ipynb` — end-to-end notebook covering on-chain pool discovery, trade analysis, and swap execution on Uniswap via Python

## What it covers

- Fetching DEX pool data and trade history using CoinGecko's on-chain API
- Filtering pools by volume, liquidity, and price change
- Executing token swaps programmatically on Uniswap

## Requirements

- Python 3.8+
- Jupyter Notebook or JupyterLab
- CoinGecko API key ([get one here](https://www.coingecko.com/en/api))

## Getting started

```bash
pip install jupyter requests pandas web3
jupyter notebook Trade_on_uniswap.ipynb
```

Set your CoinGecko API key in the notebook before running.
