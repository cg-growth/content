import requests
from models.coin_markets import MarketCoin
from models.currencies import Currency
from utils.load_env import *
from typing import List


class CoinGecko:
    def __init__(self):
        self.root = "https://api.coingecko.com/api/v3"
        self.headers = {
            "accept": "application/json",
            "x-cg-demo-api-key": f"{cg_api_key}",
        }

    def get_all_coins(self, vs_currency: Currency = Currency.USD) -> List[MarketCoin]:
        exclude_symbols = ["usdt", "usdc", "steth"]  # Coins to exclude

        request_url = self.root + f"/coins/markets?vs_currency={vs_currency.value}"
        response = requests.get(request_url, self.headers).json()

        return [
            MarketCoin(
                id=coin_data["id"], symbol=coin_data["symbol"], image=coin_data["image"]
            )
            for coin_data in response
            if coin_data["symbol"] not in exclude_symbols
        ]

    def get_vs_currencies(self):
        request_url = self.root + "/simple/supported_vs_currencies"
        return requests.get(request_url, self.headers).json()
