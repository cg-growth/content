from backtesting import Strategy
import talib as ta
from utils.load_env import *


class GoldenCross(Strategy):
    short_sma_period = 50  # Short-term SMA
    long_sma_period = 200  # Long-term SMA

    def init(self):
        self.short_sma = self.I(ta.SMA, self.data.Close, self.short_sma_period)
        self.long_sma = self.I(ta.SMA, self.data.Close, self.long_sma_period)

    def next(self):
        if (
            self.short_sma[-1] > self.long_sma[-1]
            and self.short_sma[-2] <= self.long_sma[-2]
        ):
            self.buy(
                size=size,
                sl=stop_loss * self.data.Close[-1],
                tp=take_profit * self.data.Close[-1],
            )
            print(f"Golden cross detected! Bought at {self.data.Close[-1]}")
        elif (
            self.short_sma[-1] < self.long_sma[-1]
            and self.short_sma[-2] >= self.long_sma[-2]
        ):
            self.sell()
            print(f"Death cross detected! Sold at {self.data.Close[-1]}")
