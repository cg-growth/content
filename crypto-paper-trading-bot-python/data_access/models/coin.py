from sqlalchemy import Column, Float, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship, declarative_base
from data_access.models.base import Base


class Coin(Base):
    __tablename__ = "coins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    coin_id = Column(String, unique=True, nullable=False)
    symbol = Column(String, unique=True, nullable=False)
    realized_pnl = Column(Float, nullable=True)

    prices = relationship(
        "CoinPrice", back_populates="coin", cascade="all, delete-orphan"
    )


class CoinPrice(Base):
    __tablename__ = "coins_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, ForeignKey("coins.symbol"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    value = Column(Float, nullable=False)

    coin = relationship("Coin", back_populates="prices")
