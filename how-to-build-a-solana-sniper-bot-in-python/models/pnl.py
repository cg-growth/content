from dataclasses import dataclass, field
from datetime import datetime
from dataclass_wizard import JSONWizard


@dataclass
class PNLSnapshot(JSONWizard):
    """PNL snapshot at a point in time with config"""

    timestamp: datetime = field(default_factory=datetime.now)
    total_pnl: float = 0.0
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    # Config fields
    pool_pages: int = 0
    min_pool_age_minutes: int = 0
    max_pool_age_minutes: int = 0
    min_liquidity_usd: float = 0.0
    min_volume_usd: float = 0.0
    amount_per_trade_usd: float = 0.0
    take_profit_pct: float = 0.0
    stop_loss_pct: float = 0.0
    trailing_tp_step_pct: float = 0.0
    trailing_sl_step_pct: float = 0.0


@dataclass
class DailyPNL(JSONWizard):
    """Daily PNL with configuration"""

    date: str = ""
    daily_pnl: float = 0.0
    trades_count: int = 0
    pool_pages: int = 0
    min_pool_age_minutes: int = 0
    max_pool_age_minutes: int = 0
    min_liquidity_usd: float = 0.0
    amount_per_trade_usd: float = 0.0
    take_profit_pct: float = 0.0
    stop_loss_pct: float = 0.0
    trailing_tp_step_pct: float = 0.0
    trailing_sl_step_pct: float = 0.0
