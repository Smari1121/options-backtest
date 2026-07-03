"""
Trading strategy interface and implementations.

The Strategy ABC defines the contract that the backtest engine relies on.
Any new strategy just needs to subclass it and implement three methods:
init_day, evaluate, and end_day.
"""

from abc import ABC, abstractmethod


class Strategy(ABC):
    """Base class for all trading strategies.

    The engine calls init_day() at the start of each trading day,
    evaluate() at every tick, and end_day() to force-close positions.
    """

    @abstractmethod
    def init_day(self, date_str, underlier, expiry):
        """Reset any day-level state before the simulation loop begins."""
        pass

    @abstractmethod
    def evaluate(self, timestamp, futures_price, option_prices, positions):
        """Decide what to trade at the current timestamp.

        Args:
            timestamp:     current datetime.
            futures_price: float, the underlying futures price right now.
            option_prices: dict of {(strike, type): price} for available options.
            positions:     dict of {(strike, type): avg_entry_price} currently held.

        Returns:
            List of (instrument, side, price) order tuples. Can be empty.
        """
        pass

    @abstractmethod
    def end_day(self, timestamp, option_prices, positions):
        """Generate orders to flatten all positions at end of day."""
        pass


class StraddleStrategy(Strategy):
    """Buy ATM CE + PE, roll when the nearest strike changes, flatten at EOD.

    At every second, the closest strike to the futures price is selected.
    If it differs from the currently held strike, existing positions are
    sold and a new straddle is purchased at the new strike.
    """

    def __init__(self):
        self.current_strike = None

    def init_day(self, date_str, underlier, expiry):
        self.current_strike = None

    def evaluate(self, timestamp, futures_price, option_prices, positions):
        strikes_with_both = set()
        for (strike, opt_type) in option_prices:
            if opt_type == "CE" and (strike, "PE") in option_prices:
                strikes_with_both.add(strike)

        if not strikes_with_both:
            return []

        nearest = min(strikes_with_both, key=lambda s: abs(s - futures_price))

        if nearest == self.current_strike:
            return []

        ce_price = option_prices.get((nearest, "CE"))
        pe_price = option_prices.get((nearest, "PE"))
        if ce_price is None or pe_price is None:
            return []

        orders = []

        for inst in list(positions):
            price = option_prices.get(inst)
            if price is not None:
                orders.append((inst, "SELL", price))

        orders.append(((nearest, "CE"), "BUY", ce_price))
        orders.append(((nearest, "PE"), "BUY", pe_price))
        self.current_strike = nearest

        return orders

    def end_day(self, timestamp, option_prices, positions):
        """Flatten everything. Falls back to entry price if no market tick."""
        orders = []
        for inst, entry_price in positions.items():
            price = option_prices.get(inst, entry_price)
            orders.append((inst, "SELL", price))
        self.current_strike = None
        return orders
