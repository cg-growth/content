import requests
from models.currencies import Currency
from models.currency_performance import GainersAndLosers
from utils.load_env import *


class CoinGecko:
    def __init__(self):
        self.root = "https://pro-api.coingecko.com/api/v3"
        self.headers = {
            "accept": "application/json",
            "x_cg_pro_api_key": f"{cg_api_key}",
        }

    def get_top_gainers_and_losers(
        self, vs_currency: Currency = Currency.USD
    ) -> GainersAndLosers:
        # Official SDK equivalent:
        # pip install coingecko-sdk
        # from coingecko_sdk import Coingecko
        # client = Coingecko(pro_api_key=cg_api_key, environment="pro")
        # response = client.coins.top_gainers_losers.get(vs_currency=vs_currency.value, top_coins="300")
        # return GainersAndLosers.from_dict(response.to_dict())
        request_url = (
            self.root
            + f"/coins/top_gainers_losers?vs_currency={vs_currency.value}&top_coins=300"
        )
        return GainersAndLosers.from_dict(
            requests.get(request_url, self.headers).json()
        )

    def get_vs_currencies(self):
        # Official SDK equivalent: client.simple.supported_vs_currencies.get()
        request_url = self.root + "/simple/supported_vs_currencies"
        return requests.get(request_url, self.headers).json()
