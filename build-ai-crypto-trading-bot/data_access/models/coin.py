from dataclasses import dataclass, field
from typing import List
from dataclass_wizard import JSONWizard


@dataclass
class Coin(JSONWizard):
    coin_id: str
    symbol: str
    realized_pnl: float = 0.0
    price_change: float = 0.0
    prices: List[list] = field(default_factory=list)
