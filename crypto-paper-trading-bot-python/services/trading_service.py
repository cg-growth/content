from datetime import datetime
from data_access.models.paper_order import PaperOrder


class TradingService:
    def __init__(self):
        pass

    @staticmethod
    def buy(symbol: str, current_price: float, quantity: float) -> PaperOrder:
        return PaperOrder(
            timestamp=datetime.now(),
            buy_price=current_price,
            quantity=quantity,
            symbol=symbol,
            direction="BUY",
        )

    @staticmethod
    def sell(symbol: str, current_price: float, quantity: float) -> PaperOrder:
        return PaperOrder(
            timestamp=datetime.now(),
            buy_price=current_price,
            quantity=quantity,
            symbol=symbol,
            direction="SELL",
        )

    @staticmethod
    def calculate_cost_basis(
        current_cost_basis: float,
        total_qty: float,
        new_order_qty: float,
        new_order_price: float,
    ) -> float:
        new_total_quantity = total_qty + new_order_qty

        if new_total_quantity == 0:
            return 0  # If all quantities are sold, cost basis resets

        return (
            (current_cost_basis * total_qty) + (new_order_price * new_order_qty)
        ) / new_total_quantity
