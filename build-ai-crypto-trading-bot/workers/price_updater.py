import os
from typing import List
from data_access.DAL.coins_DAL import CoinsDAL
from data_access.models.coin import Coin
from services.coingecko_service import CoinGecko
from datetime import datetime


def fetch_and_add_historic_prices(symbol, ohlc_data, coins_file):
    """Add [timestamp, close] prices for a coin from OHLC data directly to JSON file."""
    from data_access.DAL.coins_DAL import CoinsDAL

    coins_dal = CoinsDAL(coins_file)
    prices = []
    for candle in ohlc_data:
        timestamp = candle[0] / 1000  # Convert ms to s
        close = candle[4]
        prices.append([timestamp, close])
    coins_dal.add_prices_to_coin(symbol, prices)


def add_new_coin_with_history(symbol, coin_id, coins_file, ohlc_data):
    from data_access.DAL.coins_DAL import CoinsDAL

    coins_dal = CoinsDAL(coins_file)
    coins_dal.add_coin(symbol, coin_id)
    fetch_and_add_historic_prices(symbol, ohlc_data, coins_file)


def update_coin_prices(coins_file: str) -> List[Coin]:
    coins_dal = CoinsDAL(coins_file)
    local_coins = coins_dal.get_all_coins()
    local_coins_ids = [coin.coin_id for coin in local_coins]

    if len(local_coins) == 0:
        print("There are no coins in the JSON file, cannot add prices")
        return []

    cg = CoinGecko()
    coin_list = cg.get_coins()
    new_coins = 0
    for coin in coin_list:
        if coin.coin_id not in local_coins_ids:
            new_coins += 1
            ohlc_data = cg.get_historic_ohlc_by_coin_id(coin.coin_id, days=1)
            add_new_coin_with_history(
                coin.symbol,
                coin.coin_id,
                coins_file,
                ohlc_data,
            )
        if len(coin.prices) > 0:
            coins_dal.add_prices_to_coin(coin.symbol, coin.prices)
        coins_dal.update_coin_price_change(coin.symbol, coin.price_change)
    print(f"Price updated for {len(coin_list)} coins")
    print(
        f"Inserted {new_coins} coins to the coins JSON file likely due movements in the top 250."
    )
    return coin_list
