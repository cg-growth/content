"""CSV serialization utilities for PNL data"""

from models.pnl import PNLSnapshot, DailyPNL


class PNLCSVSerializer:
    """Handles CSV serialization for PNL objects"""

    @staticmethod
    def snapshot_to_row(snapshot: PNLSnapshot):
        """Convert PNLSnapshot to CSV row format"""
        return [
            snapshot.timestamp.isoformat(),
            f"{snapshot.total_pnl:.2f}",
            snapshot.total_trades,
            snapshot.wins,
            snapshot.losses,
            f"{snapshot.win_rate:.2f}",
            snapshot.pool_pages,
            snapshot.min_pool_age_minutes,
            snapshot.max_pool_age_minutes,
            f"{snapshot.min_liquidity_usd:.2f}",
            f"{snapshot.min_volume_usd:.2f}",
            f"{snapshot.amount_per_trade_usd:.2f}",
            f"{snapshot.take_profit_pct:.1f}",
            f"{snapshot.stop_loss_pct:.1f}",
            f"{snapshot.trailing_tp_step_pct:.1f}",
            f"{snapshot.trailing_sl_step_pct:.1f}",
        ]

    @staticmethod
    def snapshot_headers():
        """Get CSV headers for PNLSnapshot"""
        return [
            "Timestamp",
            "Total PNL",
            "Total Trades",
            "Wins",
            "Losses",
            "Win Rate %",
            "Pool Pages",
            "Min Pool Age (min)",
            "Max Pool Age (min)",
            "Min Liquidity USD",
            "Min Volume USD",
            "Amount per Trade USD",
            "Take Profit %",
            "Stop Loss %",
            "Trailing TP Step %",
            "Trailing SL Step %",
        ]

    @staticmethod
    def daily_pnl_to_row(daily_pnl: DailyPNL):
        """Convert DailyPNL to CSV row format"""
        return [
            daily_pnl.date,
            f"{daily_pnl.daily_pnl:.2f}",
            daily_pnl.trades_count,
            daily_pnl.pool_pages,
            daily_pnl.min_pool_age_minutes,
            daily_pnl.max_pool_age_minutes,
            f"{daily_pnl.min_liquidity_usd:.2f}",
            f"{daily_pnl.min_volume_usd:.2f}",
            f"{daily_pnl.amount_per_trade_usd:.2f}",
            f"{daily_pnl.take_profit_pct:.1f}",
            f"{daily_pnl.stop_loss_pct:.1f}",
            f"{daily_pnl.trailing_tp_step_pct:.1f}",
            f"{daily_pnl.trailing_sl_step_pct:.1f}",
        ]

    @staticmethod
    def daily_pnl_headers():
        """Get CSV headers for DailyPNL"""
        return [
            "Date",
            "Daily PNL",
            "Number of Trades",
            "Pool Pages",
            "Min Pool Age (min)",
            "Max Pool Age (min)",
            "Min Liquidity USD",
            "Min Volume USD",
            "Amount per Trade USD",
            "Take Profit %",
            "Stop Loss %",
            "Trailing TP Step %",
            "Trailing SL Step %",
        ]
