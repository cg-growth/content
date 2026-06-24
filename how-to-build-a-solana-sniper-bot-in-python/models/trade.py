from dataclasses import dataclass, field
from datetime import datetime
import uuid
from dataclass_wizard import JSONWizard


@dataclass
class Trade(JSONWizard):
    symbol: str
    direction: str  # "buy" or "sell"
    price: float
    amount: float
    amount_usdc: float
    pool_address: str
    token_address: str
    timestamp: datetime = field(default_factory=datetime.now)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pnl: float = 0.0
    pnl_percentage: float = 0.0
