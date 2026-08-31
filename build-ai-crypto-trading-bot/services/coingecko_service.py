import requests
from data_access.models.coin import Coin
from utils.load_env import *
from typing import List
from datetime import datetime


class CoinGecko:
    def __init__(self):
        self.root = "https://pro-api.coingecko.com/api/v3"
        self.headers = {
            "accept": "application/json",
            "x-cg-pro-api-key": f"{cg_api_key}",
        }

    def get_price_by_coin_id(self, coin_id: str):
        # Official SDK equivalent:
        # pip install coingecko-sdk
        # from coingecko_sdk import Coingecko
        # client = Coingecko(pro_api_key=cg_api_key, environment="pro")
        # response = client.simple.price.get(ids=coin_id, vs_currencies="usd")
        request_url = self.root + f"/simple/price?ids={coin_id}&vs_currencies=usd"
        response = requests.get(request_url, self.headers)
        data = response.json()
        return data.get(coin_id, {}).get("usd")

    def get_historic_ohlc_by_coin_id(
        self,
        coin_id: str,
        vs_currency: str = "usd",
        days: int = 1,
        interval: str = "hourly",
    ):
        # Official SDK equivalent: client.coins.ohlc.get(coin_id, vs_currency=vs_currency, days=days, interval=interval)
        request_url = f"{self.root}/coins/{coin_id}/ohlc?vs_currency={vs_currency}&days={days}&interval={interval}"
        response = requests.get(request_url, headers=self.headers)
        candles = response.json()
        return candles

    def get_coins(self) -> List[Coin]:
        # Official SDK equivalent: client.coins.markets.get(order="market_cap_desc", per_page=250, vs_currency="usd", price_change_percentage="1h")
        request_url = (
            self.root
            + "/coins/markets?order=market_cap_desc&per_page=250&vs_currency=usd&price_change_percentage=1h"
        )
        response = requests.get(request_url, headers=self.headers)
        data = response.json()
        coins = []
        now = datetime.now().timestamp()
        for coin_data in data:
            coin = Coin(
                coin_id=coin_data["id"],
                symbol=coin_data["symbol"],
                realized_pnl=0.0,
                price_change=coin_data.get(
                    "price_change_percentage_1h_in_currency", 0.0
                ),
            )
            coin.prices = [[now, coin_data["current_price"]]]
            coins.append(coin)
        return coins

    def search_pools(self, query: str = None, chain: str = None):
        # Official SDK equivalent: client.onchain.search.pools.get(query=query)
        request_url = f"{self.root}/onchain/search/pools?query={query}"
        response = requests.get(request_url, headers=self.headers)

        return response.json()
