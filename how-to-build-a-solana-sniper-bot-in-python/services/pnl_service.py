from data.data_manager import DataManager
from models.trade import Trade
from models.pnl import PNLSnapshot, DailyPNL
from utils.pnl_csv_serializer import PNLCSVSerializer
from collections import defaultdict
from pathlib import Path
from datetime import datetime
import csv


class PNLService:
    """Core PNL calculation and utility service"""

    CSV_FILE = Path(__file__).parent.parent / "data" / "daily_pnl.csv"
    ROLLING_CSV_FILE = Path(__file__).parent.parent / "data" / "rolling_pnl.csv"

    @staticmethod
    def _calculate_pnl_stats(trades):
        """Calculate PNL statistics from trades"""
        if not trades:
            return None

        # Only count sell trades (closed positions)
        sell_trades = [t for t in trades if t.direction == "sell"]

        if not sell_trades:
            return {
                "total_pnl": 0.0,
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
            }

        total_pnl = sum(t.pnl for t in sell_trades)
        total_trades = len(sell_trades)
        wins = len([t for t in sell_trades if t.pnl > 0])
        losses = len([t for t in sell_trades if t.pnl < 0])
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

        return {
            "total_pnl": total_pnl,
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
        }

    @staticmethod
    def _write_csv(file_path, headers, rows):
        """Generic CSV writer utility"""
        file_exists = file_path.exists()
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "a", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(headers)
            writer.writerows(rows)

    @staticmethod
    def save_rolling_pnl(config: dict):
        """Save rolling PNL snapshot after each trade closes"""
        trades = DataManager.get_all(Trade)

        if not trades:
            return

        stats = PNLService._calculate_pnl_stats(trades)

        # Use JSONWizard to automatically cast from dict
        snapshot = PNLSnapshot.from_dict(
            {
                "timestamp": datetime.now(),
                "total_pnl": stats["total_pnl"],
                "total_trades": stats["total_trades"],
                "wins": stats["wins"],
                "losses": stats["losses"],
                "win_rate": stats["win_rate"],
                "pool_pages": config["pools"]["num_pages"],
                "min_pool_age_minutes": config["pools"]["min_age_minutes"],
                "max_pool_age_minutes": config["pools"]["max_age_minutes"],
                "min_liquidity_usd": config["pools"]["min_liquidity_usd"],
                "min_volume_usd": config["pools"].get("min_volume_usd", 0),
                "amount_per_trade_usd": config["trade"]["amount_usdc"],
                "take_profit_pct": config["trade"]["take_profit"],
                "stop_loss_pct": config["trade"]["stop_loss"],
                "trailing_tp_step_pct": config["trade"].get("trailing_tp_step", 0),
                "trailing_sl_step_pct": config["trade"].get("trailing_sl_step", 0),
            }
        )

        PNLService._write_csv(
            PNLService.ROLLING_CSV_FILE,
            PNLCSVSerializer.snapshot_headers(),
            [PNLCSVSerializer.snapshot_to_row(snapshot)],
        )

    @staticmethod
    def save_daily_pnl(config: dict):
        """Save daily PNL with config to CSV file"""
        trades = DataManager.get_all(Trade)

        if not trades:
            return

        today = datetime.now().strftime("%Y-%m-%d")

        # Calculate daily PNL - only count sell trades (closed positions)
        daily = defaultdict(lambda: {"pnl": 0.0, "trades": 0})
        for trade in trades:
            if trade.direction == "sell":
                date = trade.timestamp.strftime("%Y-%m-%d")
                daily[date]["pnl"] += trade.pnl
                daily[date]["trades"] += 1

        # Use JSONWizard to automatically cast from dict
        daily_pnl_obj = DailyPNL.from_dict(
            {
                "date": today,
                "daily_pnl": daily[today]["pnl"],
                "trades_count": daily[today]["trades"],
                "pool_pages": config["pools"]["num_pages"],
                "min_pool_age_minutes": config["pools"]["min_age_minutes"],
                "max_pool_age_minutes": config["pools"]["max_age_minutes"],
                "min_liquidity_usd": config["pools"]["min_liquidity_usd"],
                "min_volume_usd": config["pools"].get("min_volume_usd", 0),
                "amount_per_trade_usd": config["trade"]["amount_usdc"],
                "take_profit_pct": config["trade"]["take_profit"],
                "stop_loss_pct": config["trade"]["stop_loss"],
                "trailing_tp_step_pct": config["trade"].get("trailing_tp_step", 0),
                "trailing_sl_step_pct": config["trade"].get("trailing_sl_step", 0),
            }
        )

        # Write to CSV
        PNLService._write_csv(
            PNLService.CSV_FILE,
            PNLCSVSerializer.daily_pnl_headers(),
            [PNLCSVSerializer.daily_pnl_to_row(daily_pnl_obj)],
        )

    @staticmethod
    def print_pnl():
        """Print current PNL statistics to console"""
        trades = DataManager.get_all(Trade)

        if not trades:
            print("\n⚠️  No trades yet\n")
            return

        stats = PNLService._calculate_pnl_stats(trades)

        print("\n" + "=" * 50)
        print("📊 TOTAL PNL")
        print("=" * 50)
        print(f"Total PNL: ${stats['total_pnl']:.2f}")
        print(f"Total Trades: {stats['total_trades']}")
        print(f"Wins: {stats['wins']} | Losses: {stats['losses']}")
        print(f"Win Rate: {stats['win_rate']:.2f}%")
        print("=" * 50)

        # Daily PNL - only count sell trades (closed positions)
        daily = defaultdict(lambda: {"pnl": 0.0, "trades": 0})
        for trade in trades:
            if trade.direction == "sell":
                date = trade.timestamp.strftime("%Y-%m-%d")
                daily[date]["pnl"] += trade.pnl
                daily[date]["trades"] += 1

        print("\n📅 DAILY PNL")
        print("=" * 50)
        for date in sorted(daily.keys()):
            print(f"{date}: ${daily[date]['pnl']:.2f} ({daily[date]['trades']} trades)")
        print("=" * 50 + "\n")
