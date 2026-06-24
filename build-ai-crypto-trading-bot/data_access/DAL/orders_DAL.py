from ..models.paper_order import PaperOrder
from .Base_JSON_DAL import Base_JSON_DAL
from typing import List, Literal, Optional
from datetime import datetime


class OrdersDAL:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def get_all_orders(
        self, direction: Optional[Literal["BUY", "SELL"]] = None
    ) -> List[PaperOrder]:
        orders = PaperOrder.from_list(Base_JSON_DAL.get_all(self.file_path))
        if direction:
            orders = [o for o in orders if o.direction == direction]
        return orders

    def insert_order(
        self,
        timestamp: datetime,
        buy_price: float,
        quantity: float,
        symbol: str,
        direction: str,
    ) -> PaperOrder:
        orders = self.get_all_orders()
        new_order = PaperOrder(
            timestamp=timestamp,
            buy_price=buy_price,
            quantity=quantity,
            symbol=symbol,
            direction=direction,
        )
        orders.append(new_order)
        Base_JSON_DAL.write_data(self.file_path, [o.to_dict() for o in orders])
        return new_order
