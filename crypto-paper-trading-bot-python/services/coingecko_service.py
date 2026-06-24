import requests
from data_access.models.coin import Coin, CoinPrice
from enums.currencies import Currency
from utils.load_env import *
from typing import List
from datetime import datetime


class CoinGecko:
    def __init__(self):
        self.root = "https://api.coingecko.com/api/v3"
        self.headers = {
            "accept": "application/json",
            "x-cg-demo-api-key": f"{cg_api_key}",
        }

    def get_price_by_coin_id(self, coin_id: str):
        request_url = self.root + f"/simple/price?ids={coin_id}&vs_currencies=usd"
        response = requests.get(request_url, self.headers).json()
        print(response)
        return response[coin_id]["usd"]

    def get_vs_currencies(self):
        request_url = self.root + "/simple/supported_vs_currencies"
        return requests.get(request_url, self.headers).json()

    def get_coin_list(self) -> List[Coin]:
        request_url = (
            self.root
            + f"/coins/markets?order=market_cap_desc&per_page=250&vs_currency={Currency.USD}&price_change_percentage=1h"
        )
        response = requests.get(request_url, headers=self.headers).json()

        coins = []
        for coin_data in response:
            coin = Coin(
                coin_id=coin_data["id"],
                symbol=coin_data["symbol"],
                realized_pnl=None,
            )

            price = CoinPrice(
                symbol=coin_data["symbol"],
                timestamp=datetime.now(),
                value=coin_data["current_price"],
            )

            coin.prices = [price]
            coin.price_change = coin_data["price_change_percentage_1h_in_currency"]
            coins.append(coin)

        return coins
