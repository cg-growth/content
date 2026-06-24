> Read the full article: [Python Guide: Create Crypto Trading Signals with TradingView Indicators](https://www.coingecko.com/learn/crypto-trading-signals-tradingview-indicators)

This is a cryptocurrency signal bot that uses the TradingView and CoinGecko to notify you when a custom signal of your choice has been generated. It uses notify py to generate OS level notifications in real time.

### Features
- Fetch cryptocurrency data using the CoinGecko API.
- Analyze market data using TradingView indicators (Oscillators and Moving Averages).
- Trigger OS notifications when a buy signal is detected.

### Prerequisites
- Python 3.10+
- CoinGecko Demo API Key

### Running it
- rename `.env.example` to `.env` and paste your CoinGecko Demo API key in.
- install dependencies with `pip install -r requirements.txt`.
- run it with `python main.py`

### Note
The signal logic currently lives in `main.py` but I'll make a PR in the future to add it to a `.yml` file for easy modification.