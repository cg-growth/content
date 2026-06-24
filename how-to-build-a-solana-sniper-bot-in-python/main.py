from data.data_manager import DataManager
from models.order import Order
from services.coingecko import CoinGecko
from services.trade_service import TradeService
from services.pnl_service import PNLService
from utils.load_env import cg_api_key, load_config
from utils.formatting import format_exit_message
import asyncio
from datetime import datetime


def _get_monitored_tokens(data_manager: DataManager) -> list[str]:
    """Get list of tokens currently being monitored."""
    return [
        f"solana:{o.token_address.replace('solana_', '')}"
        for o in data_manager.get_all(Order)
        if o.token_address
    ]


def _find_matching_order(orders: list[Order], token_id: str) -> Order | None:
    """Find order matching the given token ID."""
    for order in orders:
        if (
            order.token_address
            and order.token_address.replace("solana_", "") == token_id
        ):
            return order
    return None


async def monitor_prices(
    cg: CoinGecko,
    trade_service: TradeService,
    data_manager: DataManager,
    config: dict,
):
    """Monitor price stream and handle TP/SL exits with trailing logic."""
    max_open_trades = config["portfolio"]["max_open_trades"]
    trailing_tp_pct = config["trade"].get("trailing_tp_step", 2) / 100
    trailing_sl_pct = config["trade"].get("trailing_sl_step", 2) / 100
    use_trailing = trailing_tp_pct > 0 or trailing_sl_pct > 0

    # Stale asset config
    stale_config = config.get("stale_assets", {})
    stale_timeout_minutes = stale_config.get("timeout_minutes", 10)
    stale_min_move_pct = stale_config.get("min_move_pct", 5)

    trailing_state = {}
    stale_tracking = {}  # Track when we started monitoring each order

    while True:
        orders = data_manager.get_all(Order)

        if not orders:
            print("⚠️ No open positions to monitor")
            await asyncio.sleep(5)
            continue

        tokens = _get_monitored_tokens(data_manager)
        print(f"📊 Monitoring {len(tokens)}/{max_open_trades} open trades")
        print(f"📋 Tokens to monitor: {tokens}")
        print("🎧 Listening for price updates...")

        try:
            subscribed_tokens = set(tokens)

            async for price_data in cg.stream_token_prices(
                tokens, subscribed_tokens, data_manager, _get_monitored_tokens
            ):
                if price_data.get("_reconnect"):
                    print("📌 Token list changed, re-subscribing to price stream...")
                    break

                orders = data_manager.get_all(Order)
                token_id = price_data["token"].replace("solana:", "")

                order = _find_matching_order(orders, token_id)
                if not order:
                    continue

                current_price = price_data["price"]
                pnl_pct = ((current_price - order.price) / order.price) * 100

                # Initialize trailing state for new orders
                if order.id not in trailing_state:
                    trailing_state[order.id] = {
                        "trailing_active": False,
                        "initial_tp_pct": order.tp,
                        "initial_sl_pct": order.sl,
                        "trailing_tp": None,
                        "trailing_sl": None,
                    }

                # Initialize stale tracking for new orders
                if order.id not in stale_tracking:
                    stale_tracking[order.id] = {
                        "first_seen": datetime.now(),
                        "highest_pnl_pct": pnl_pct,
                    }

                # Update highest PnL seen
                if pnl_pct > stale_tracking[order.id]["highest_pnl_pct"]:
                    stale_tracking[order.id]["highest_pnl_pct"] = pnl_pct

                state = trailing_state[order.id]

                # === TRAILING NOT YET ACTIVE ===
                if not state["trailing_active"]:
                    if pnl_pct >= state["initial_tp_pct"]:
                        if use_trailing:
                            # Activate trailing - create pincer around current price
                            state["trailing_active"] = True
                            state["trailing_tp"] = current_price * (1 + trailing_tp_pct)
                            state["trailing_sl"] = current_price * (1 - trailing_sl_pct)

                            tp_pnl = (
                                (state["trailing_tp"] - order.price) / order.price
                            ) * 100
                            sl_pnl = (
                                (state["trailing_sl"] - order.price) / order.price
                            ) * 100

                            print(
                                f"  📈 Initial TP hit for {order.symbol} at ${current_price:.10f} ({pnl_pct:+.2f}%)"
                            )
                            print(
                                f"  🎯 Trailing activated - TP: ${state['trailing_tp']:.10f} ({tp_pnl:+.2f}%) | SL: ${state['trailing_sl']:.10f} ({sl_pnl:+.2f}%)"
                            )
                        else:
                            # No trailing - sell immediately at TP
                            print(
                                f"  🎯 TP hit for {order.symbol} at ${current_price:.10f} ({pnl_pct:+.2f}%)"
                            )
                            trade_service.sell(order, current_price)
                            await asyncio.to_thread(PNLService.print_pnl)
                            await asyncio.to_thread(PNLService.save_rolling_pnl, config)
                            del trailing_state[order.id]
                            if order.id in stale_tracking:
                                del stale_tracking[order.id]
                            break
                    else:
                        # Show initial TP/SL targets
                        print(
                            f"💰 {order.symbol}: Buy: ${order.price:.10f} | Current: ${current_price:.10f} ({pnl_pct:+.2f}%) | Target: +{state['initial_tp_pct']}% | Stop: -{state['initial_sl_pct']}%"
                        )

                        # Check for stale asset (hasn't moved enough in time window)
                        time_elapsed = (
                            datetime.now() - stale_tracking[order.id]["first_seen"]
                        ).total_seconds() / 60
                        highest_move = stale_tracking[order.id]["highest_pnl_pct"]

                        if (
                            time_elapsed >= stale_timeout_minutes
                            and highest_move < stale_min_move_pct
                        ):
                            print(
                                f"  ⏰ STALE: {order.symbol} only moved {highest_move:+.2f}% in {time_elapsed:.1f} min (need {stale_min_move_pct}% in {stale_timeout_minutes} min)"
                            )
                            trade_service.sell(order, current_price)
                            await asyncio.to_thread(PNLService.print_pnl)
                            await asyncio.to_thread(PNLService.save_rolling_pnl, config)
                            del trailing_state[order.id]
                            del stale_tracking[order.id]
                            break

                        # Check initial stop loss
                        if pnl_pct <= -state["initial_sl_pct"]:
                            print(
                                format_exit_message(
                                    order.symbol, pnl_pct, state["initial_tp_pct"]
                                )
                            )
                            trade_service.sell(order, current_price)
                            await asyncio.to_thread(PNLService.print_pnl)
                            await asyncio.to_thread(PNLService.save_rolling_pnl, config)
                            del trailing_state[order.id]
                            if order.id in stale_tracking:
                                del stale_tracking[order.id]
                            break
                        continue

                # === TRAILING IS ACTIVE ===
                tp_pnl = ((state["trailing_tp"] - order.price) / order.price) * 100
                sl_pnl = ((state["trailing_sl"] - order.price) / order.price) * 100

                print(
                    f"🔄 {order.symbol}: Buy: ${order.price:.10f} | Current: ${current_price:.10f} ({pnl_pct:+.2f}%) | Trail TP: ${state['trailing_tp']:.10f} ({tp_pnl:+.2f}%) | Trail SL: ${state['trailing_sl']:.10f} ({sl_pnl:+.2f}%)"
                )

                if current_price >= state["trailing_tp"]:
                    # Move pincer up
                    state["trailing_tp"] = current_price * (1 + trailing_tp_pct)
                    state["trailing_sl"] = current_price * (1 - trailing_sl_pct)
                    new_tp_pnl = (
                        (state["trailing_tp"] - order.price) / order.price
                    ) * 100
                    new_sl_pnl = (
                        (state["trailing_sl"] - order.price) / order.price
                    ) * 100
                    print(
                        f"  ⬆️  {order.symbol} - Pincer moved up! New TP: ${state['trailing_tp']:.10f} ({new_tp_pnl:+.2f}%) | New SL: ${state['trailing_sl']:.10f} ({new_sl_pnl:+.2f}%)"
                    )

                elif current_price <= state["trailing_sl"]:
                    # Trailing stop hit - close trade
                    print(
                        f"  🛑 Trailing stop hit for {order.symbol} at ${current_price:.10f} ({pnl_pct:+.2f}%)"
                    )
                    trade_service.sell(order, current_price)
                    await asyncio.to_thread(PNLService.print_pnl)
                    await asyncio.to_thread(PNLService.save_rolling_pnl, config)
                    del trailing_state[order.id]
                    if order.id in stale_tracking:
                        del stale_tracking[order.id]
                    break

        except Exception as e:
            print(f"❌ Error in price stream: {e}")
            await asyncio.sleep(2)


async def scan_and_buy(
    cg: CoinGecko,
    trade_service: TradeService,
    data_manager: DataManager,
    config: dict,
):
    """Continuously scan for new pools and buy when below max open trades."""
    pools_config = config["pools"]
    trade_config = config["trade"]
    max_open_trades = config["portfolio"]["max_open_trades"]

    while True:
        open_count = len(data_manager.get_all(Order))

        if open_count < max_open_trades:
            print("🔍 Scanning for new pools...")
            pools = cg.get_new_pools(pools_config["num_pages"])
            filtered_pools = cg.filter_pools(
                pools,
                min_pool_age_minutes=pools_config["min_age_minutes"],
                max_pool_age_minutes=pools_config["max_age_minutes"],
                min_liquidity_usd=pools_config["min_liquidity_usd"],
                min_volume_usd=pools_config.get("min_volume_usd", 0),
            )
            print(f"✅ Found {len(filtered_pools)} pools matching criteria.")

            for pool in filtered_pools:
                if len(data_manager.get_all(Order)) >= max_open_trades:
                    print(f"📊 Reached max open trades limit ({max_open_trades})")
                    break

                trade_service.buy(
                    pool,
                    amount_usdc=trade_config["amount_usdc"],
                    tp=trade_config["take_profit"],
                    sl=trade_config["stop_loss"],
                )

        await asyncio.sleep(5)


async def main():
    """Main entry point - runs all trading tasks concurrently."""
    config = load_config()
    cg = CoinGecko(cg_api_key)
    trade_service = TradeService()
    data_manager = DataManager()

    await asyncio.gather(
        scan_and_buy(cg, trade_service, data_manager, config),
        monitor_prices(cg, trade_service, data_manager, config),
    )


if __name__ == "__main__":
    asyncio.run(main())
