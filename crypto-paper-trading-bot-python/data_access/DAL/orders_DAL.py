from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound
from typing import List, Literal, Optional, Union
from datetime import datetime
from ..models.paper_order import PaperOrder


class OrdersDAL:
    def __init__(self, session: Session):
        self.session = session

    def insert_order(
        self,
        timestamp: datetime,
        buy_price: float,
        quantity: float,
        symbol: str,
        direction: str,
    ) -> PaperOrder:
        new_order = PaperOrder(
            timestamp=timestamp,
            buy_price=buy_price,
            quantity=quantity,
            symbol=symbol,
            direction=direction,
        )
        self.session.add(new_order)
        self.session.commit()
        return new_order

    def get_order_by_symbol(self, symbol: str) -> Optional[PaperOrder]:
        try:
            return (
                self.session.query(PaperOrder)
                .filter(PaperOrder.symbol == symbol)
                .order_by(PaperOrder.timestamp.desc())
                .first()
            )
        except NoResultFound:
            return None

    def get_all_orders(
        self, direction: Optional[Literal["BUY", "SELL"]] = None
    ) -> List[PaperOrder]:
        query = self.session.query(PaperOrder)

        if direction:
            query = query.filter(PaperOrder.direction == direction)

        return query.all()
