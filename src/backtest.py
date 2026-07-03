"""
Strategy-agnostic backtest engine.

Loads each trading day's data, builds a 1-second price grid, and drives
the strategy's evaluate() method at every tick. The engine never knows
what the strategy is doing internally; it only passes market state in
and executes the orders that come back.
"""

import numpy as np
from .loader import load_day_data, get_trading_dates, build_price_grid
from .portfolio import Portfolio


class BacktestEngine:
    """Runs a strategy across all trading days for a list of underliers.

    Args:
        strategy:   an instance of a Strategy subclass.
        data_dir:   path to the allData directory.
        underliers: list of underlier names to simulate.
    """

    def __init__(self, strategy, data_dir, underliers):
        self.strategy = strategy
        self.data_dir = data_dir
        self.underliers = underliers

    def run(self):
        """Execute the backtest and return {underlier: Portfolio} results."""
        dates = get_trading_dates(self.data_dir)
        results = {}

        for underlier in self.underliers:
            print(f"Running {underlier}...")
            portfolio = Portfolio()

            for date_str in dates:
                self._run_day(date_str, underlier, portfolio)

            results[underlier] = portfolio

        return results

    def _run_day(self, date_str, underlier, portfolio):
        """Simulate a single trading day at 1-second resolution."""
        futures_df, options, expiry = load_day_data(
            self.data_dir, date_str, underlier
        )

        if futures_df is None or not options or expiry is None:
            return

        print(f"  {date_str} (exp: {expiry})")

        self.strategy.init_day(date_str, underlier, expiry)

        time_index, fut_prices, opt_arrays, opt_valid = build_price_grid(
            futures_df, options
        )

        n = len(time_index)
        instruments = list(opt_arrays.keys())

        for i in range(n):
            fut_price = fut_prices[i]
            if np.isnan(fut_price):
                continue

            current_opt = {}
            for inst in instruments:
                if opt_valid[inst][i]:
                    current_opt[inst] = opt_arrays[inst][i]

            ts = time_index[i]
            orders = self.strategy.evaluate(
                ts, fut_price, current_opt, portfolio.get_positions()
            )
            portfolio.execute_orders(orders, ts)
            portfolio.take_snapshot(ts, current_opt)

        last_opt = {}
        for inst in instruments:
            if opt_valid[inst][-1]:
                last_opt[inst] = opt_arrays[inst][-1]

        eod_orders = self.strategy.end_day(
            time_index[-1], last_opt, portfolio.get_positions()
        )
        portfolio.execute_orders(eod_orders, time_index[-1])
        portfolio.take_snapshot(time_index[-1], last_opt)
