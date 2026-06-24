from ..models.portfolio_item import PortfolioItem, PnLEntry
from .Base_JSON_DAL import Base_JSON_DAL
from typing import List, Optional
from datetime import datetime


class PortfolioDAL:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def get_all_portfolio_items(self) -> List[PortfolioItem]:
        return PortfolioItem.from_list(Base_JSON_DAL.get_all(self.file_path))

    def get_portfolio_item_by_symbol(self, symbol: str) -> Optional[PortfolioItem]:
        return next(
            (item for item in self.get_all_portfolio_items() if item.symbol == symbol),
            None,
        )

    def insert_portfolio_item(
        self, symbol: str, cost_basis: float, total_quantity: float
    ) -> PortfolioItem:
        items = self.get_all_portfolio_items()
        new_item = PortfolioItem(
            symbol=symbol, cost_basis=cost_basis, total_quantity=total_quantity
        )
        items.append(new_item)
        Base_JSON_DAL.write_data(self.file_path, [i.to_dict() for i in items])
        return new_item

    def update_portfolio_item_by_symbol(
        self, symbol: str, cost_basis: float, additional_quantity: float
    ) -> Optional[PortfolioItem]:
        items = self.get_all_portfolio_items()
        for item in items:
            if item.symbol == symbol:
                item.cost_basis = cost_basis
                item.total_quantity += additional_quantity
                Base_JSON_DAL.write_data(self.file_path, [i.to_dict() for i in items])
                return item
        return None

    def add_pnl_entry_by_symbol(
        self, symbol: str, date: datetime, value: float
    ) -> Optional[PnLEntry]:
        items = self.get_all_portfolio_items()
        for item in items:
            if item.symbol == symbol:
                pnl_entry = PnLEntry(date=date, value=value)
                item.pnl_entries.append(pnl_entry)
                Base_JSON_DAL.write_data(self.file_path, [i.to_dict() for i in items])
                return pnl_entry
        return None
