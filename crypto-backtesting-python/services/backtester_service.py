import pandas as pd
from backtesting import Backtest, Strategy
from typing import Type, Optional, Any, Union


class BackTester:
    def __init__(
        self,
        data: pd.DataFrame,
        strategy: Type[Strategy],
        cash: float = 10000,
        commission: float = 0.0,
        spread: float = 0.0,
        trade_on_close: bool = False,
        **kwargs
    ):

        if not self.validate_data(data):
            raise ValueError("Invalid data format. Missing required OHLC columns.")

        self._backtest = Backtest(
            data=data,
            strategy=strategy,
            cash=cash,
            commission=commission,
            spread=spread,
            trade_on_close=trade_on_close,
            **kwargs
        )
        self._results: Optional[pd.Series] = None

    @staticmethod
    def validate_data(data: pd.DataFrame) -> bool:
        """Validate DataFrame contains required OHLC columns"""
        required = {"Open", "High", "Low", "Close"}
        return required.issubset(data.columns)

    def run(self, **strategy_params: Any) -> pd.Series:
        self._results = self._backtest.run(**strategy_params)
        return self._results

    def optimize(
        self,
        maximize: Union[str, callable] = "SQN",
        method: str = "grid",
        max_tries: Optional[Union[int, float]] = None,
        constraint: Optional[callable] = None,
        **params: Any
    ) -> pd.Series:
        return self._backtest.optimize(
            maximize=maximize,
            method=method,
            max_tries=max_tries,
            constraint=constraint,
            **params
        )

    def plot(
        self,
        results: Optional[pd.Series] = None,
        filename: Optional[str] = None,
        plot_width: Optional[int] = None,
        **plot_kwargs: Any
    ) -> None:
        if results is None and self._results is None:
            raise ValueError("No results to plot. Run backtest first.")

        self._backtest.plot(
            results=results or self._results,
            filename=filename,
            plot_width=plot_width,
            **plot_kwargs
        )

    @property
    def results(self) -> Optional[pd.Series]:
        """Get latest backtest results"""
        return self._results

    @property
    def trades(self) -> Optional[pd.DataFrame]:
        """Get detailed trades DataFrame"""
        return self._results._trades if self._results else None

    @property
    def equity_curve(self) -> Optional[pd.DataFrame]:
        """Get equity curve DataFrame"""
        return self._results._equity_curve if self._results else None
