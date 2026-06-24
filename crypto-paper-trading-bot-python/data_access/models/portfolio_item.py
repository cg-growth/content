from sqlalchemy import Column, Float, String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from data_access.models.base import Base


class PnLEntry(Base):
    __tablename__ = "pnl_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False)
    value = Column(Float, nullable=False)

    portfolio_item_id = Column(
        Integer, ForeignKey("portfolio_items.id"), nullable=False
    )


class PortfolioItem(Base):
    __tablename__ = "portfolio_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cost_basis = Column(Float, nullable=False)
    total_quantity = Column(Float, nullable=False)
    symbol = Column(String, nullable=False)

    # Relationship with PnLEntry (One-to-Many: One PortfolioItem can have many PnLEntries)
    pnl_entries = relationship(
        "PnLEntry", backref="portfolio_item", cascade="all, delete"
    )
