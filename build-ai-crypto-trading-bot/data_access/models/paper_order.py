from typing import Literal
from dataclasses import dataclass
from datetime import datetime
from dataclass_wizard import JSONWizard


@dataclass
class PaperOrder(JSONWizard):
    timestamp: datetime
    buy_price: float
    quantity: float
    symbol: str
    direction: Literal["BUY", "SELL"]
