import os
from data_access.DAL.orders_DAL import OrdersDAL
from data_access.DAL.portfolio_DAL import PortfolioDAL
from data_access.DAL.coins_DAL import CoinsDAL
from data_access.models.coin import Coin
from services.coingecko_service import CoinGecko
from services.openai_service import OpenAIService
from services.trading_service import TradingService
from workers.initializer import initialize_coin_data
from utils.load_env import *
from datetime import datetime
import time


COINS_FILE = os.path.join(os.path.dirname(__file__), "data_access/data/coins.json")
ORDERS_FILE = os.path.join(os.path.dirname(__file__), "data_access/data/orders.json")
PORTFOLIO_FILE = os.path.join(
    os.path.dirname(__file__), "data_access/data/portfolio.json"
)

# Initialize DALs
coins_dal = CoinsDAL(COINS_FILE)
orders_dal = OrdersDAL(ORDERS_FILE)
portfolio_dal = PortfolioDAL(PORTFOLIO_FILE)

# Initialize services
cg = CoinGecko()
ai = OpenAIService()


def initialize_coin_data(coins_file):
    print(f"Initializing {coins_file}...")
    if not os.path.exists(coins_file):
        with open(coins_file, "w") as f:
            f.write("[]")
    if coins_dal.get_all_coins():
        print("JSON already initialized, skipping...")
        return
    all_coins = cg.get_coins()
    for coin in all_coins:
        coins_dal.add_coin(coin.symbol, coin.coin_id)
        ohlc_data = cg.get_historic_ohlc_by_coin_id(
            coin.coin_id, days=180, interval="hourly"
        )
        coins_dal.add_prices_to_coin(coin.symbol, ohlc_data)
    print(f"Added {len(all_coins)} coins.")
    print(f"Added historical prices to {len(all_coins)} coins.")


def check_pools(coin: Coin):
    pools = cg.search_pools(coin.symbol)
    filtered_pools = []
    for pool in pools["data"]:
        reserve = pool.get("reserve_in_usd", 0)
        volume = pool.get("volume_in_usd", {}).get("h24", 0)
        buys = pool.get("buys_24h", 0)
        if (
            reserve >= min_reserves_usd
            and volume >= min_volume_24h
            and buys >= min_buys_24h
        ):
            filtered_pools.append(pool)
    return filtered_pools


# Populate JSON files with initial data
coins = initialize_coin_data(COINS_FILE)


# Function to handle buy logic
def handle_buy(coin: Coin, current_price: float):
    safe_pools = check_pools(coin)
    context = str(coin) + str(safe_pools)
    recommendation = ai.get_chat_completion(context, prompt_template)
    if "BUY" not in recommendation:
        print(f"NOT buying {coin.symbol} as per AI recommendation: {recommendation}")
        # return
    print(f" Buying {coin.symbol} as per AI recommendation: {recommendation}")
    order = TradingService.buy(coin.symbol, current_price, qty)
    existing_portfolio = portfolio_dal.get_portfolio_item_by_symbol(order.symbol)
    if existing_portfolio is None:
        portfolio_dal.insert_portfolio_item(
            order.symbol, order.buy_price, order.quantity
        )
        print(
            f"Bought {order.symbol} and inserted new portfolio item for {order.symbol}"
        )
    else:
        cost_basis = TradingService.calculate_cost_basis(
            existing_portfolio.cost_basis,
            existing_portfolio.total_quantity,
            order.quantity,
            order.buy_price,
        )
        portfolio_dal.update_portfolio_item_by_symbol(
            order.symbol, cost_basis, order.quantity
        )
        print(
            f"Bought {order.symbol}. We already hold {order.symbol}, updating existing portfolio with new order data."
        )
    orders_dal.insert_order(
        order.timestamp, order.buy_price, order.quantity, order.symbol, order.direction
    )


# Function to handle sell logic
def handle_sell(coin, current_price):
    buy_orders = orders_dal.get_all_orders("BUY")

    # Filter buy orders for the current symbol
    filtered_buy_orders = [order for order in buy_orders if order.symbol == coin.symbol]

    if not filtered_buy_orders:
        return

    for order in filtered_buy_orders:
        stop_loss_price = order.buy_price * (1 - sl / 100)
        take_profit_price = order.buy_price * (1 + tp / 100)
        current_pnl = (current_price - order.buy_price) / order.buy_price * 100

        if current_price <= stop_loss_price:
            sell_order = TradingService.sell(
                order.symbol, current_price, order.quantity
            )
            print(
                f"Stop Loss Triggered: Sold {order.quantity} of {order.symbol} at ${current_price}"
            )

        elif current_price >= take_profit_price:
            sell_order = TradingService.sell(
                order.symbol, current_price, order.quantity
            )
            print(
                f"Take Profit Triggered: Sold {order.quantity} of {order.symbol} at ${current_price}"
            )
        else:
            continue
        orders_dal.insert_order(
            sell_order.timestamp,
            sell_order.buy_price,
            sell_order.quantity,
            sell_order.symbol,
            sell_order.direction,
        )
        coins_dal.update_coin_pnl(order.symbol, current_pnl)


# Main execution logic
def main():
    print("Starting up JSON data...")
    time.sleep(5)
    while True:
        coins_with_historical_data = coins_dal.get_all_coins()

        for coin in coins_with_historical_data:
            current_price = cg.get_price_by_coin_id(coin.coin_id)
            coins_dal.update_coin_price_change(coin.symbol, coin.price_change)

            handle_buy(coin, current_price)
            # handle_sell(coin, current_price)
            portfolio_dal.add_pnl_entry_by_symbol(
                coin.symbol, datetime.now(), coin.prices[-1][1]
            )
            break
        print("Engine cycle complete, sleeping for 1 hour.")
        time.sleep(3600)


if __name__ == "__main__":
    main()
