from services.backtester_service import BackTester
from services.coingecko_service import CoinGecko
from utils.load_env import *
import pandas as pd
from strategies.buy_the_dip_strategy import BuyTheDip
from strategies.golden_cross_strategy import GoldenCross

cg = CoinGecko()
data = cg.get_historical_prices("bitcoin", "usd", 1736424000, 1738152000, "hourly")

# Define column names
columns = ["Timestamp", "Open", "High", "Low", "Close"]

# Convert to DataFrame
df = pd.DataFrame(data, columns=columns)

# Initialize backtester
backtester = BackTester(
    data=df,
    strategy=BuyTheDip,
    cash=total_amount,
    commission=0.001,
)
output = backtester.run()
print(output)
backtester.plot()
