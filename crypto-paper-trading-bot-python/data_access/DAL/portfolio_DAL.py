from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound
from typing import List, Optional
from datetime import datetime
from ..models.portfolio_item import PortfolioItem, PnLEntry


class PortfolioDAL:
    def __init__(self, session: Session):
        self.session = session

    def get_portfolio_item_by_symbol(self, symbol: str) -> Optional[PortfolioItem]:
        try:
            return (
                self.session.query(PortfolioItem)
                .filter(PortfolioItem.symbol == symbol)
                .one()
            )
        except NoResultFound:
            return None

    def insert_portfolio_item(
        self, symbol: str, cost_basis: float, total_quantity: float
    ) -> PortfolioItem:
        new_item = PortfolioItem(
            symbol=symbol, cost_basis=cost_basis, total_quantity=total_quantity
        )
        self.session.add(new_item)
        self.session.commit()
        return new_item

    def update_portfolio_item_by_symbol(
        self,
        symbol: str,
        cost_basis: float,
        additional_quantity: float,
    ) -> Optional[PortfolioItem]:
        portfolio_item = self.get_portfolio_item_by_symbol(symbol)
        if portfolio_item is None:
            return None

        portfolio_item.cost_basis = cost_basis
        portfolio_item.total_quantity += additional_quantity
        self.session.commit()
        return portfolio_item

    def add_pnl_entry_by_symbol(
        self, symbol: str, date: datetime, value: float
    ) -> Optional[PnLEntry]:
        portfolio_item = self.get_portfolio_item_by_symbol(symbol)

        if portfolio_item is None:
            return None

        pnl_entry = PnLEntry(
            date=date, value=value, portfolio_item_id=portfolio_item.id
        )
        self.session.add(pnl_entry)
        self.session.commit()
        return pnl_entry
