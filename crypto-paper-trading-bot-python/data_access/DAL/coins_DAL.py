from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound
from typing import List, Optional, Union
from datetime import datetime
from ..models.coin import Coin, CoinPrice


class CoinsDAL:
    def __init__(self, session: Session):
        self.session = session

    def get_all_coins(self) -> List[Coin]:
        return self.session.query(Coin).all()

    def get_coin_by_symbol(self, symbol: str) -> Optional[Coin]:
        try:
            return self.session.query(Coin).filter(Coin.symbol == symbol).one()
        except NoResultFound:
            return None

    def update_coin_pnl(
        self, symbol: str, new_realized_pnl: Optional[float]
    ) -> Optional[Coin]:
        coin = self.get_coin_by_symbol(symbol)
        if coin:
            coin.realized_pnl = new_realized_pnl
            self.session.commit()
            return coin
        return None

    def add_price_to_coin(
        self, symbol: str, timestamp: datetime, value: float
    ) -> Optional[CoinPrice]:
        coin = self.get_coin_by_symbol(symbol)
        if coin:
            new_price = CoinPrice(timestamp=timestamp, value=value, symbol=coin.symbol)
            self.session.add(new_price)
            self.session.commit()
            return new_price
        return None

    def get_coin_prices_by_symbol(self, symbol: str) -> List[CoinPrice]:
        coin = self.get_coin_by_symbol(symbol)
        if coin:
            return (
                self.session.query(CoinPrice)
                .filter(CoinPrice.symbol == coin.id)
                .order_by(CoinPrice.timestamp)
                .all()
            )
        return []

    def get_current_price_for_coin(self, symbol: str) -> Optional[CoinPrice]:
        coin: Union[Coin, CoinPrice] = self.get_coin_by_symbol(symbol)
        if coin and coin.prices:

            # Get the most recent price directly from the related prices
            return max(coin.prices, key=lambda price: price.timestamp)
        return None

    def add_coin(
        self, symbol: str, coin_id: str, realized_pnl: Optional[float] = None
    ) -> Optional[Coin]:
        existing_coin = self.get_coin_by_symbol(symbol)
        if existing_coin:
            return None

        new_coin = Coin(
            symbol=symbol, coin_id=coin_id, realized_pnl=realized_pnl or 0.0, prices=[]
        )
        self.session.add(new_coin)
        self.session.commit()
        return new_coin
