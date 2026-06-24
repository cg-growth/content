from tradingview_ta import TA_Handler, Interval, Analysis


class TradingView:
    def __init__(self):
        pass

    @staticmethod
    def retrieve_analysis(symbol: str, exchange: str, interval: Interval) -> Analysis:
        return TA_Handler(
            symbol=symbol,
            exchange=exchange,
            screener="crypto",
            interval=interval,
            timeout=None,
        ).get_analysis()
