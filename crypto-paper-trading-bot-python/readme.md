> Read the full article: [How to Build a Crypto Paper Trading Bot](https://www.coingecko.com/learn/crypto-paper-trading-bot-python)

# Paper Trading Crypto Trading Bot in Python

Simple paper trading crypto trading bot written in Python. The bot uses postgreSQL to store trading data and is fully dockerised.

The bot trades based on CoinGecko's market data - specifically price change. This is hardcoded to 1hour price change percentage but can easily be adjusted to fit other requirements.

## To get started

You will need Docker to run this tool.
To get started, simply `run docker compose -t "paper_bot" up -d --build`

You can see log outputs inside the `app` container.

## To Develop

To add features or change the bot's logic you will need to install the python requirements locally with `pip install -r requirements.txt`.
the bot is configured to run locally as well, so long as your db container is running in docker.
