from dataclasses import asdict
from models.order import Order
from models.pool import Pool
from models.trade import Trade
from data.data_manager import DataManager


class TradeService:

    def buy(self, pool: Pool, amount_usdc: float, tp: float, sl: float) -> Order:
        # Check if we already have an open order for this token
        existing_orders = DataManager.get_all(Order)
        token_address = pool.relationships.base_token.data.id

        for order in existing_orders:
            if order.token_address == token_address:
                print(
                    f"⏭️  SKIPPED: {pool.attributes.name} - Already have open position for this token"
                )
                return None

        price = float(pool.attributes.base_token_price_usd)
        token_amount = amount_usdc / price

        trade = Trade(
            symbol=pool.attributes.name,
            direction="buy",
            price=price,
            amount=token_amount,
            amount_usdc=amount_usdc,
            pool_address=pool.attributes.address,
            token_address=token_address,
        )

        order = Order(
            **asdict(trade),
            tp=tp,
            sl=sl,
        )
        DataManager.save(order)
        DataManager.save(trade)

        print(
            f"🚀 BOUGHT: {trade.symbol} @ ${trade.price:.10f} | Amount: ${amount_usdc:.2f}"
        )
        return order

    def sell(self, order: Order, current_price: float) -> Trade:
        pnl = (current_price - order.price) * order.amount
        pnl_pct = ((current_price - order.price) / order.price) * 100

        trade = Trade(
            symbol=order.symbol,
            direction="sell",
            price=current_price,
            amount=order.amount,
            amount_usdc=current_price * order.amount,
            pnl=pnl,
            pnl_percentage=pnl_pct,
            pool_address=order.pool_address,
            token_address=order.token_address,
        )

        DataManager.delete_by_id(Order, order.id)
        DataManager.save(trade)

        emoji = "📈" if pnl >= 0 else "📉"
        print(
            f"{emoji} SELL: {order.symbol} @ ${current_price:.10f} | PnL: ${pnl:.2f} ({pnl_pct:.2f}%)"
        )
        return trade
