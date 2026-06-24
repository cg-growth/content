from services.coingecko_service import CoinGecko
from services.notification_service import Notification
from services.tradingview_service import TradingView
from tradingview_ta import Interval
from utils.util import Utils
import time

cg = CoinGecko()


def main():
    coins = cg.get_all_coins()
    for coin in coins:
        print(coin.symbol)

        try:
            icon_path = Utils.download_image(coin.image)
            analysis = TradingView.retrieve_analysis(
                (coin.symbol + "USDT").capitalize(), "Binance", Interval.INTERVAL_1_HOUR
            )

            if (
                analysis.oscillators["RECOMMENDATION"] == "NEUTRAL"
                and analysis.moving_averages["RECOMMENDATION"] == "NEUTRAL"
            ):
                Notification.send(
                    f"Buy signal for {coin.symbol.upper()}",
                    "Both Oscillators and Moving averages have generated a buy signal.",
                    icon_path,
                )

        except Exception as e:
            print(e)

        finally:
            time.sleep(1)
            Utils.delete_image(icon_path)


if __name__ == "__main__":
    while True:
        main()
        time.sleep(300)
