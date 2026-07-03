"""
Data loading and price grid construction for NSE tick data.

Handles the directory layout (NSE_YYYYMMDD/Options, Futures (Continuous)),
parses option instrument names into their components, and builds a
second-by-second price grid suitable for event-driven backtesting.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime


KNOWN_UNDERLIERS = ["BANKNIFTY", "FINNIFTY", "NIFTY"]

OPTIONS_FOLDER = "Options"
FUTURES_FOLDER = "Futures (Continuous)"


def parse_option_name(name):
    """Break an option filename into (underlier, expiry, strike, opt_type).

    For example, "NIFTY22110314550PE" becomes ("NIFTY", "221103", 14550, "PE").
    Returns None if the name does not match any known underlier format.
    """
    for ul in KNOWN_UNDERLIERS:
        if not name.startswith(ul):
            continue
        rest = name[len(ul):]
        expiry = rest[:6]
        remainder = rest[6:]
        opt_type = remainder[-2:]
        try:
            strike = int(remainder[:-2])
        except ValueError:
            continue
        return ul, expiry, strike, opt_type
    return None


def read_ticks(filepath):
    """Read a headerless tick CSV into a DataFrame with a parsed datetime column.

    Expected CSV columns: Date, Time, Price, Volume, Open Interest.
    Rows with unparseable timestamps or prices are dropped.
    """
    df = pd.read_csv(
        filepath, header=None,
        names=["date", "time", "price", "volume", "oi"]
    )
    df["datetime"] = pd.to_datetime(
        df["date"].astype(str) + " " + df["time"].astype(str),
        errors="coerce"
    )
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=["datetime", "price"])
    return df


def get_trading_dates(data_dir):
    """Return a sorted list of date strings from the NSE_YYYYMMDD folders."""
    dates = []
    for folder in sorted(Path(data_dir).iterdir()):
        if folder.is_dir() and folder.name.startswith("NSE_"):
            dates.append(folder.name.split("_")[1])
    return dates


def find_nearest_expiry(options_dir, underlier, trade_date):
    """Find the closest expiry on or after trade_date for the given underlier.

    Scans all option files in the directory and returns the expiry code
    (e.g. "221103") of the nearest future expiry. Returns None if no
    valid expiry is found.
    """
    expiries = set()
    for f in Path(options_dir).glob(f"{underlier}*.csv"):
        parsed = parse_option_name(f.stem)
        if parsed and parsed[0] == underlier:
            expiries.add(parsed[1])

    trade_dt = datetime.strptime(trade_date, "%Y%m%d")
    valid = []
    for exp in expiries:
        try:
            exp_dt = datetime.strptime(exp, "%y%m%d")
        except ValueError:
            continue
        if exp_dt >= trade_dt:
            valid.append((exp, exp_dt))

    if not valid:
        return None
    valid.sort(key=lambda x: x[1])
    return valid[0][0]


def load_day_data(data_dir, date_str, underlier):
    """Load futures and nearest-expiry option tick data for a single trading day.

    Returns:
        futures_df: DataFrame of futures ticks, or None if missing.
        options:    dict mapping (strike, opt_type) to tick DataFrames.
        expiry:     the expiry code string, or None.
    """
    day_dir = Path(data_dir) / f"NSE_{date_str}"
    options_dir = day_dir / OPTIONS_FOLDER
    futures_dir = day_dir / FUTURES_FOLDER

    futures_file = futures_dir / f"{underlier}-I.csv"
    if not futures_file.exists():
        return None, {}, None

    futures_df = read_ticks(futures_file)

    expiry = find_nearest_expiry(options_dir, underlier, date_str)
    if expiry is None:
        return futures_df, {}, None

    options = {}
    for f in options_dir.glob(f"{underlier}{expiry}*.csv"):
        parsed = parse_option_name(f.stem)
        if parsed:
            _, _, strike, opt_type = parsed
            options[(strike, opt_type)] = read_ticks(f)

    return futures_df, options, expiry


def build_price_grid(futures_df, options_dict):
    """Align all tick data onto a uniform 1-second time grid.

    Prices are forward-filled so every second has a value (or NaN if
    no tick has occurred yet for that instrument). Returns numpy arrays
    instead of DataFrames to keep the hot loop in the backtest engine fast.

    Returns:
        time_index: DatetimeIndex at 1-second frequency.
        fut_prices: numpy array of futures prices.
        opt_arrays: dict of {(strike, type): numpy array of prices}.
        opt_valid:  dict of {(strike, type): boolean mask where price is not NaN}.
    """
    start = futures_df["datetime"].min().floor("s")
    end = futures_df["datetime"].max().ceil("s")
    time_index = pd.date_range(start, end, freq="s")

    fut_series = futures_df.set_index("datetime")["price"]
    fut_series = fut_series[~fut_series.index.duplicated(keep="last")]
    fut_prices = fut_series.reindex(time_index, method="ffill").to_numpy()

    instruments = list(options_dict.keys())
    opt_arrays = {}
    opt_valid = {}

    for key in instruments:
        df = options_dict[key]
        series = df.set_index("datetime")["price"]
        series = series[~series.index.duplicated(keep="last")]
        filled = series.reindex(time_index, method="ffill")
        arr = filled.to_numpy()
        opt_arrays[key] = arr
        opt_valid[key] = ~np.isnan(arr)

    return time_index, fut_prices, opt_arrays, opt_valid
