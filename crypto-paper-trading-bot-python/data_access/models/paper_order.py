from typing import Literal
from sqlalchemy import Column, Float, String, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from data_access.models.base import Base


class PaperOrder(Base):
    __tablename__ = "paper_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)
    buy_price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    symbol = Column(String, nullable=False)
    direction = Column(String, nullable=False)
    direction: Literal[
        "BUY", "SELL"
    ]  # Type hinting for Python-side checking, not affecting DB schema
