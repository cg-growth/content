from typing import List, Optional
from data_access.models.coin import Coin
from .Base_JSON_DAL import Base_JSON_DAL


class CoinsDAL:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def get_all_coins(self) -> List[Coin]:
        return Coin.from_list(Base_JSON_DAL.get_all(self.file_path))

    def get_coin_by_symbol(self, symbol: str) -> Optional[Coin]:
        return next((c for c in self.get_all_coins() if c.symbol == symbol), None)

    def update_coin_pnl(self, symbol: str, new_realized_pnl: float) -> Optional[Coin]:
        coins = self.get_all_coins()
        for coin in coins:
            if coin.symbol == symbol:
                coin.realized_pnl = new_realized_pnl
                break
        else:
            return None
        Base_JSON_DAL.write_data(self.file_path, [c.to_dict() for c in coins])
        return coin

    def add_prices_to_coin(
        self, symbol: str, prices: List[list]
    ) -> Optional[List[list]]:
        coins = self.get_all_coins()
        for coin in coins:
            if coin.symbol == symbol:
                coin.prices.extend(prices)
                Base_JSON_DAL.write_data(self.file_path, [c.to_dict() for c in coins])
                return prices
        return None

    def add_coin(
        self,
        symbol: str,
        coin_id: str,
        realized_pnl: float = 0.0,
        price_change: float = 0.0,
    ) -> Optional[Coin]:
        coins = self.get_all_coins()
        if any(c.symbol == symbol for c in coins):
            return None
        new_coin = Coin(
            symbol=symbol,
            coin_id=coin_id,
            realized_pnl=realized_pnl,
            prices=[],
            price_change=price_change,
        )
        coins.append(new_coin)
        Base_JSON_DAL.write_data(self.file_path, [c.to_dict() for c in coins])
        return new_coin

    def update_coin_price_change(
        self, symbol: str, price_change: float
    ) -> Optional[Coin]:
        coins = self.get_all_coins()
        for coin in coins:
            if coin.symbol == symbol:
                coin.price_change = price_change
                Base_JSON_DAL.write_data(self.file_path, [c.to_dict() for c in coins])
                return coin
        return None
