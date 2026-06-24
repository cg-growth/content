from backtesting import Strategy
from utils.load_env import *


class BuyTheDip(Strategy):
    def init(self):
        pass

    def next(self):
        current_close = self.data.Close[-1]  # Current candle's close
        previous_close = self.data.Close[-2]  # Previous candle's close
        price_difference = (current_close - previous_close) / previous_close * 100

        if price_difference <= -0.5:
            self.buy(
                size=0.1, sl=stop_loss * current_close, tp=take_profit * current_close
            )
            print(
                f"Bought at {current_close}, which is a {price_difference}% from previous close ({previous_close})"
            )
        else:
            print(f"Did not buy, price difference is only {price_difference}%")
