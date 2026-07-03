"""
Portfolio accounting: position tracking, PnL, and trade logging.

Positions are stored as {instrument: {"qty": int, "avg_price": float}}.
Supports long and short positions, weighted average costing, and
per-tick mark-to-market snapshots for downstream analysis.
"""


class Portfolio:
    """Tracks open positions, realized PnL, and historical snapshots.

    Each instrument key is a (strike, option_type) tuple.
    """

    def __init__(self):
        self.positions = {}
        self.realized_pnl = 0.0
        self.trade_log = []
        self.snapshots = []

    def buy(self, instrument, price, timestamp):
        """Add a long unit. Covers a short if one exists, otherwise
        accumulates with weighted average cost."""
        if instrument in self.positions:
            pos = self.positions[instrument]
            if pos["qty"] > 0:
                total_cost = pos["avg_price"] * pos["qty"] + price
                pos["qty"] += 1
                pos["avg_price"] = total_cost / pos["qty"]
            elif pos["qty"] < 0:
                cover_pnl = (pos["avg_price"] - price) * 1
                self.realized_pnl += cover_pnl
                pos["qty"] += 1
                if pos["qty"] == 0:
                    del self.positions[instrument]
            else:
                del self.positions[instrument]
                self.positions[instrument] = {"qty": 1, "avg_price": price}
        else:
            self.positions[instrument] = {"qty": 1, "avg_price": price}

        self.trade_log.append({
            "timestamp": timestamp,
            "strike": instrument[0],
            "type": instrument[1],
            "side": "BUY",
            "price": price,
        })

    def sell(self, instrument, price, timestamp):
        """Remove a long unit (realizing PnL), or open a short if flat."""
        pnl = 0.0
        if instrument in self.positions:
            pos = self.positions[instrument]
            if pos["qty"] > 0:
                pnl = (price - pos["avg_price"]) * 1
                self.realized_pnl += pnl
                pos["qty"] -= 1
                if pos["qty"] == 0:
                    del self.positions[instrument]
            elif pos["qty"] < 0:
                total_cost = pos["avg_price"] * abs(pos["qty"]) + price
                pos["qty"] -= 1
                pos["avg_price"] = total_cost / abs(pos["qty"])
            else:
                del self.positions[instrument]
                self.positions[instrument] = {"qty": -1, "avg_price": price}
        else:
            self.positions[instrument] = {"qty": -1, "avg_price": price}

        self.trade_log.append({
            "timestamp": timestamp,
            "strike": instrument[0],
            "type": instrument[1],
            "side": "SELL",
            "price": price,
            "trade_pnl": pnl,
        })

    def get_positions(self):
        """Return {instrument: avg_price} view for strategy consumption."""
        return {
            inst: pos["avg_price"]
            for inst, pos in self.positions.items()
        }

    def get_position_qty(self, instrument):
        """Return the signed quantity held for a given instrument."""
        pos = self.positions.get(instrument)
        if pos is None:
            return 0
        return pos["qty"]

    def mtm(self, option_prices):
        """Compute total PnL (realized + unrealized) at current prices."""
        unrealized = 0.0
        for inst, pos in self.positions.items():
            current = option_prices.get(inst)
            if current is not None:
                unrealized += (current - pos["avg_price"]) * pos["qty"]
        return self.realized_pnl + unrealized

    def take_snapshot(self, timestamp, option_prices):
        """Record the current state for later analysis and plotting."""
        held = []
        for (s, t), pos in self.positions.items():
            label = f"{s}{t}"
            if pos["qty"] != 1:
                label += f"x{pos['qty']}"
            held.append(label)
        self.snapshots.append({
            "timestamp": timestamp,
            "mtm_pnl": self.mtm(option_prices),
            "realized_pnl": self.realized_pnl,
            "positions": "|".join(held) if held else "",
        })

    def execute_orders(self, orders, timestamp):
        """Process a list of (instrument, side, price) tuples."""
        for instrument, side, price in orders:
            if side == "BUY":
                self.buy(instrument, price, timestamp)
            elif side == "SELL":
                self.sell(instrument, price, timestamp)
