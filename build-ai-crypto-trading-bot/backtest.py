import os
from data_access.DAL.coins_DAL import CoinsDAL
from services.coingecko_service import CoinGecko
from services.openai_service import OpenAIService
from utils.load_env import *
from utils.load_env import prompt_template


COINS_FILE = os.path.join(os.path.dirname(__file__), "data_access/data/coins.json")

coins_dal = CoinsDAL(COINS_FILE)
ai = OpenAIService()
cg = CoinGecko()


def run_backtest_single_coin(prompt_template, symbol):
    coin = coins_dal.get_coin_by_symbol(symbol)
    if not coin:
        print(f"Coin with symbol '{symbol}' not found.")
        return []

    results = []
    buy_entries = []
    for i, price_entry in enumerate(coin.prices, start=1):
        price_slice = coin.prices[:i]
        timestamp = price_entry[0]
        close = price_entry[-1]

        recommendation = ai.get_chat_completion(price_slice, prompt_template)
        print(f"recommendation: {recommendation}")
        if "BUY" in recommendation.upper():
            buy_entries.append({"timestamp": timestamp, "buy_price": close})
        results.append(
            {
                "symbol": coin.symbol,
                "timestamp": timestamp,
                "close": close,
                "recommendation": recommendation,
            }
        )
    # Calculate PNL for each buy entry using the final price in the price list
    final_price = coin.prices[-1][-1] if coin.prices else None
    for entry in buy_entries:
        entry["final_price"] = final_price
        entry["pnl"] = (
            (final_price - entry["buy_price"]) / entry["buy_price"] * 100
            if final_price is not None
            else None
        )
    return results, buy_entries


if __name__ == "__main__":

    symbol = input("Enter coin symbol to backtest: ").strip()
    results, buy_entries = run_backtest_single_coin(prompt_template, symbol)
    print("\nAll recommendations:")
    for r in results:
        print(r)
    print("\nBuy signals and PNL:")
    for b in buy_entries:
        print(b)
