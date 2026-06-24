from dataclasses import dataclass
from models.trade import Trade


@dataclass
class Order(Trade):
    tp: float = 0.0
    sl: float = 0.0
