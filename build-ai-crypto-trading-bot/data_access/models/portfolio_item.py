from dataclasses import dataclass, field
from typing import List
from datetime import datetime
from dataclass_wizard import JSONWizard


@dataclass
class PnLEntry(JSONWizard):
    date: datetime
    value: float


@dataclass
class PortfolioItem(JSONWizard):
    cost_basis: float
    total_quantity: float
    symbol: str
    pnl_entries: List[PnLEntry] = field(default_factory=list)
