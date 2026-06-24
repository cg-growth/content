> Read the full article: [How to Export Crypto OHLC Chart Data: A Python, Google Sheets and Excel Guide](https://www.coingecko.com/learn/download-crypto-ohlcv-data)

# Export Crypto OHLC & OHLCV Data

A Jupyter notebook for fetching OHLC and OHLCV candlestick data from the CoinGecko API and exporting it to CSV or Excel — ready to open in Google Sheets or Excel.

## What's inside

- `CG_export.ipynb` — full notebook covering:
  - Fetching OHLC data for standard coins (e.g. Bitcoin, Ethereum)
  - Fetching OHLCV data for on-chain DEX pools (e.g. top Ethereum pools)
  - Exporting results to `.csv` and `.xlsx`

## Requirements

- Python 3.8+
- Jupyter Notebook or JupyterLab
- CoinGecko API key ([get one here](https://www.coingecko.com/en/api))

## Getting started

```bash
pip install jupyter requests polars openpyxl
jupyter notebook CG_export.ipynb
```

Update the API key section in the notebook before running. The notebook supports both Demo and Pro API keys.

## Output formats

| Format | Use case |
|--------|---------|
| `.csv` | General data analysis, Python/pandas workflows |
| `.xlsx` | Google Sheets, Microsoft Excel |
