# Options Backtest

A modular backtesting framework for simulating an ATM straddle trading strategy on NSE options data. Built as a take-home assignment to demonstrate a systematic approach to strategy simulation, portfolio accounting, and result analysis.

## What it does

The system simulates a simple straddle strategy across one month of tick-level NSE data:

1. At every second, find the strike closest to the current futures price.
2. Buy both the CE and PE at that strike (one lot each).
3. Hold until the nearest strike changes, then sell and re-enter at the new strike.
4. Close all positions at end of day.
5. Repeat across all trading days for NIFTY and BANKNIFTY.

The backtest engine is strategy-agnostic. It only passes market data in and executes whatever orders come back. The straddle logic lives in its own class and can be swapped out for any other strategy by subclassing `Strategy`.

## Project structure

```
.
├── config.py        # Paths and underlier list
├── loader.py        # CSV parsing, expiry detection, price grid construction
├── strategy.py      # Strategy base class + StraddleStrategy implementation
├── portfolio.py     # Position tracking, PnL accounting, trade log
├── backtest.py      # Engine that drives the strategy over the data
├── results.py       # CSV export and console summary
├── plots.py         # 8 visualization charts
├── run.py           # Entry point
├── requirements.txt
├── data/            # Raw tick data goes here (see data/README.md)
└── output/          # Generated CSVs and plots land here (see output/README.md)
```

## Setup

Python 3.10+ is assumed.

```bash
pip install -r requirements.txt
```

### Getting the data

The raw tick data is not included in this repo (~2 GB unzipped). See [data/README.md](data/README.md) for the exact folder structure expected.

1. Download from the provided Google Drive link.
2. Unzip the archive to get a folder called `allData`.
3. Place `allData` inside `data/` so the path is `data/allData/NSE_20221101/...`.

The code resolves all paths relative to `config.py`, so nothing is hardcoded.

## Running

```bash
python run.py
```

This runs the full pipeline: loads data, simulates day by day, exports CSVs, and generates all plots. Takes a few minutes since it iterates at 1-second granularity across 21 trading days.

Console output shows progress and finishes with a summary:

```
--- NIFTY ---
Trades: 15664
Realized PnL: -539.75
Peak MTM: 39.25
Trough MTM: -549.85
Final MTM: -539.75
```

For a full description of every output file and plot, see [output/README.md](output/README.md).

## Design decisions

**Why the PnL is negative:** the strategy unconditionally rolls the straddle every time the nearest strike changes. When the futures price hovers near a boundary, this creates rapid back-and-forth trading that bleeds capital through repeated small losses. This is the expected behavior and the assignment explicitly notes that profitability is not the objective.

**Numpy in the hot loop:** the inner simulation loop runs ~22,000 iterations per day per underlier. Option prices are pre-converted to numpy arrays before the loop to avoid pandas overhead on every tick.

**Portfolio supports shorts and scaling:** even though this strategy only ever holds 1 lot long, the ledger tracks signed quantities and weighted average prices. This keeps the door open for more complex strategies without touching the accounting layer.

## Plugging in a new strategy

Subclass `Strategy` from `strategy.py` and implement three methods:

```python
class MyStrategy(Strategy):
    def init_day(self, date_str, underlier, expiry):
        pass

    def evaluate(self, timestamp, futures_price, option_prices, positions):
        # return list of (instrument, "BUY"/"SELL", price) tuples
        return []

    def end_day(self, timestamp, option_prices, positions):
        return []
```

Then swap it into `run.py`:

```python
strategy = MyStrategy()
engine = BacktestEngine(strategy, DATA_DIR, UNDERLIERS)
```
