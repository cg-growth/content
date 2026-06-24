from typing import Literal
import requests
from utils.load_env import *


class CoinGecko:
    def __init__(self):
        self.root = "https://pro-api.coingecko.com/api/v3"
        self.headers = {
            "accept": "application/json",
            "x_cg_pro_api_key": f"{cg_api_key}",
        }

    def get_historical_prices(
        self,
        coin_id: str,
        vs_currency: str,
        from_unix: int,
        to_unix: int,
        interval: Literal["daily", "hourly"],
    ):
        request_url = (
            self.root
            + f"/coins/{coin_id}/ohlc/range?vs_currency={vs_currency}&from={from_unix}&to={to_unix}&interval={interval}"
        )

        return requests.get(request_url, self.headers).json()
