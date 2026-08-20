# WebSocket vs REST API: How to Stream Real-Time Crypto Prices in Python

Companion code for the CoinGecko Learn guide: [WebSocket vs REST API: How to Stream Real-Time Crypto Prices in Python](https://www.coingecko.com/learn/websocket-vs-rest-api-real-time-crypto-prices-python)

## Setup

```bash
cd content/websocket-vs-rest-api-real-time-crypto-prices-python
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp example.env .env  # then add your CoinGecko API key
```

`rest_poller.py` works with a free Demo API key. The WebSocket scripts (`ws_stream.py`, `ws_candlestick.py`, `ws_resilient.py`) require a Basic plan or higher.

## Files

- `rest_poller.py` — polls `/simple/price` for coin prices at a fixed interval.
- `ws_stream.py` — streams real-time coin prices via the `CGSimplePrice` WebSocket channel.
- `ws_candlestick.py` — streams OHLCV candle data via the `OnchainOHLCV` WebSocket channel.
- `ws_resilient.py` — `CGSimplePrice` streaming with automatic reconnection and re-subscription.

## Run

```bash
python rest_poller.py
python ws_stream.py
python ws_candlestick.py
python ws_resilient.py
```
