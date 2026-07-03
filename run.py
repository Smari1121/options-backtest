"""Entry point for the backtest pipeline."""

from config import DATA_DIR, OUTPUT_DIR, UNDERLIERS
from strategy import StraddleStrategy
from backtest import BacktestEngine
from results import export_results
from plots import generate_plots


def main():
    strategy = StraddleStrategy()
    engine = BacktestEngine(strategy, DATA_DIR, UNDERLIERS)
    results = engine.run()
    export_results(results, OUTPUT_DIR)
    generate_plots(results, OUTPUT_DIR, DATA_DIR)


if __name__ == "__main__":
    main()
