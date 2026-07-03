"""
Visualization suite for backtest output.

Generates 8 PNG plots covering cumulative PnL, daily breakdown, drawdown,
intraday behaviour, strategy action, roll frequency, trade PnL distribution,
and the relationship between trade count and capital erosion.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path

PALETTE = {"NIFTY": "#1976D2", "BANKNIFTY": "#F57C00"}


def generate_plots(results, output_dir, data_dir):
    """Entry point: build all plots from the backtest results.

    Args:
        results:    dict of {underlier: Portfolio}.
        output_dir: pathlib.Path for saving PNGs.
        data_dir:   pathlib.Path to allData (needed for futures overlay).
    """
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "#FAFAFA",
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.color": "#CCCCCC",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
    })

    pnl_data = {}
    for underlier, portfolio in results.items():
        if portfolio.snapshots:
            df = pd.DataFrame(portfolio.snapshots)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            pnl_data[underlier] = df

    if not pnl_data:
        return

    trade_data = {}
    for underlier, portfolio in results.items():
        if portfolio.trade_log:
            tdf = pd.DataFrame(portfolio.trade_log)
            tdf["timestamp"] = pd.to_datetime(tdf["timestamp"])
            trade_data[underlier] = tdf

    _cumulative_pnl(pnl_data, output_dir)
    _daily_pnl(pnl_data, output_dir)
    _drawdown(pnl_data, output_dir)
    _intraday_pnl(pnl_data, output_dir)
    _strategy_action(pnl_data, output_dir, data_dir)
    _roll_heatmap(trade_data, output_dir)
    _trade_pnl_distribution(trade_data, output_dir)
    _trades_vs_pnl(pnl_data, trade_data, output_dir)

    plt.close("all")
    print(f"\nPlots saved to {output_dir}")


# ---------------------------------------------------------------------------
# Individual plot functions
# ---------------------------------------------------------------------------

def _cumulative_pnl(pnl_data, output_dir):
    """Month-long MTM PnL for all underliers, resampled to 1 min."""
    fig, ax = plt.subplots(figsize=(14, 5.5))

    for underlier, df in pnl_data.items():
        resampled = df.set_index("timestamp").resample("1min").last()
        resampled = resampled.dropna(subset=["mtm_pnl"])
        color = PALETTE.get(underlier, "gray")
        ax.plot(resampled.index, resampled["mtm_pnl"],
                label=underlier, color=color, linewidth=1.2, alpha=0.9)
        ax.fill_between(resampled.index, 0, resampled["mtm_pnl"],
                        alpha=0.07, color=color)

    ax.axhline(0, color="#999", linestyle="--", linewidth=0.7)
    ax.set_ylabel("MTM PnL (points)")
    ax.set_title("Cumulative Mark-to-Market PnL")
    ax.legend(framealpha=0.9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "cumulative_pnl.png", dpi=150, bbox_inches="tight")
    print("  - cumulative_pnl.png")


def _daily_pnl(pnl_data, output_dir):
    """Bar chart of each day's realized PnL contribution."""
    fig, ax = plt.subplots(figsize=(14, 5))

    daily = {}
    for underlier, df in pnl_data.items():
        df = df.copy()
        df["date"] = df["timestamp"].dt.date
        eod = df.groupby("date")["realized_pnl"].last()
        dpnl = eod.diff()
        dpnl.iloc[0] = eod.iloc[0]
        daily[underlier] = dpnl

    daily_df = pd.DataFrame(daily)
    x = np.arange(len(daily_df))
    width = 0.35

    for i, underlier in enumerate(daily_df.columns):
        vals = daily_df[underlier].values
        color = PALETTE.get(underlier, "gray")
        ax.bar(x + i * width - width / 2, vals, width,
               label=underlier, color=color, alpha=0.85,
               edgecolor="white", linewidth=0.5)

    ax.axhline(0, color="#999", linestyle="-", linewidth=0.7)
    ax.set_ylabel("PnL (points)")
    ax.set_title("Daily Realized PnL")
    ax.set_xticks(x)
    labels = [d.strftime("%d %b") for d in daily_df.index]
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.legend(framealpha=0.9)
    fig.tight_layout()
    fig.savefig(output_dir / "daily_pnl.png", dpi=150, bbox_inches="tight")
    print("  - daily_pnl.png")


def _drawdown(pnl_data, output_dir):
    """Drawdown from running peak of cumulative MTM PnL."""
    fig, ax = plt.subplots(figsize=(14, 5))

    for underlier, df in pnl_data.items():
        resampled = df.set_index("timestamp").resample("1min").last()
        resampled = resampled.dropna(subset=["mtm_pnl"])
        cumul = resampled["mtm_pnl"]
        peak = cumul.cummax()
        dd = cumul - peak

        color = PALETTE.get(underlier, "gray")
        ax.fill_between(resampled.index, 0, dd,
                        alpha=0.25, color=color, label=underlier)
        ax.plot(resampled.index, dd, color=color, linewidth=0.8, alpha=0.7)

    ax.axhline(0, color="#999", linestyle="-", linewidth=0.7)
    ax.set_ylabel("Drawdown (points)")
    ax.set_title("Drawdown from Peak MTM")
    ax.legend(framealpha=0.9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "drawdown.png", dpi=150, bbox_inches="tight")
    print("  - drawdown.png")


def _pick_sample_day(pnl_data, underlier="NIFTY"):
    """Select the trading day with the widest intraday PnL swing."""
    df = pnl_data[underlier].copy()
    df["date"] = df["timestamp"].dt.date
    daily_range = df.groupby("date")["mtm_pnl"].agg(
        lambda s: s.max() - s.min()
    )
    return daily_range.idxmax()


def _intraday_pnl(pnl_data, output_dir):
    """Second-by-second PnL for the most volatile day (NIFTY)."""
    underlier = "NIFTY"
    df = pnl_data[underlier].copy()
    sample_day = _pick_sample_day(pnl_data, underlier)

    df["date"] = df["timestamp"].dt.date
    day_df = df[df["date"] == sample_day].copy()

    base = day_df["mtm_pnl"].iloc[0]
    day_df["intraday_pnl"] = day_df["mtm_pnl"] - base

    fig, ax = plt.subplots(figsize=(14, 5))

    color = PALETTE[underlier]
    ax.plot(day_df["timestamp"], day_df["intraday_pnl"],
            color=color, linewidth=0.8, alpha=0.9)
    ax.fill_between(day_df["timestamp"], 0, day_df["intraday_pnl"],
                    where=day_df["intraday_pnl"] >= 0,
                    alpha=0.1, color="#43A047", interpolate=True)
    ax.fill_between(day_df["timestamp"], 0, day_df["intraday_pnl"],
                    where=day_df["intraday_pnl"] < 0,
                    alpha=0.1, color="#E53935", interpolate=True)

    ax.axhline(0, color="#999", linestyle="--", linewidth=0.7)
    ax.set_ylabel("Intraday PnL (points)")
    ax.set_title(
        f"Intraday MTM PnL - {underlier} ({sample_day.strftime('%d %b %Y')})"
    )
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "intraday_pnl.png", dpi=150, bbox_inches="tight")
    print("  - intraday_pnl.png")


def _parse_strike(pos):
    """Extract the strike number from a position string like '17500CE'."""
    if pd.isna(pos) or pos == "":
        return np.nan
    part = pos.split("|")[0]
    if "x" in part:
        part = part[:part.index("x")]
    return int(part[:-2])


def _strategy_action(pnl_data, output_dir, data_dir):
    """Overlay futures price and the held strike for a sample day."""
    underlier = "NIFTY"
    df = pnl_data[underlier].copy()
    sample_day = _pick_sample_day(pnl_data, underlier)

    df["date"] = df["timestamp"].dt.date
    day_df = df[df["date"] == sample_day].copy()
    day_df["strike"] = day_df["positions"].apply(_parse_strike)

    from .loader import read_ticks, FUTURES_FOLDER
    date_str = sample_day.strftime("%Y%m%d")
    fut_file = (
        Path(data_dir) / f"NSE_{date_str}" / FUTURES_FOLDER
        / f"{underlier}-I.csv"
    )
    fut_df = read_ticks(fut_file)

    fig, ax = plt.subplots(figsize=(14, 5.5))

    ax.plot(fut_df["datetime"], fut_df["price"],
            color="#90A4AE", linewidth=0.5, alpha=0.7, label="Futures Price")
    ax.step(day_df["timestamp"], day_df["strike"],
            color=PALETTE[underlier], linewidth=2, where="post",
            label="Held Strike", alpha=0.9)

    ax.set_ylabel("Price / Strike")
    ax.set_title(
        f"Strategy Action - {underlier} ({sample_day.strftime('%d %b %Y')})"
    )
    ax.legend(framealpha=0.9, loc="upper left")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "strategy_action.png", dpi=150, bbox_inches="tight")
    print("  - strategy_action.png")


def _roll_heatmap(trade_data, output_dir):
    """Heatmap of roll frequency by hour of day and trading date."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True,
                              layout="constrained")

    for idx, (underlier, tdf) in enumerate(trade_data.items()):
        buys = tdf[tdf["side"] == "BUY"].copy()
        buys["date"] = buys["timestamp"].dt.date
        buys["hour"] = buys["timestamp"].dt.hour

        rolls = buys.drop_duplicates(subset=["timestamp"]).copy()
        pivot = rolls.groupby(["date", "hour"]).size().unstack(fill_value=0)

        ax = axes[idx]
        im = ax.imshow(
            pivot.values, aspect="auto", cmap="YlOrRd",
            interpolation="nearest"
        )
        ax.set_title(underlier)
        ax.set_xlabel("Hour of Day")
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels([f"{h}:00" for h in pivot.columns], rotation=45, ha="right")
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels([d.strftime("%d %b") for d in pivot.index], fontsize=9)

    axes[0].set_ylabel("Trading Day")
    fig.suptitle("Roll Frequency by Hour", fontsize=14, fontweight="bold")
    fig.colorbar(im, ax=axes, label="Rolls", shrink=0.8)
    fig.savefig(output_dir / "roll_heatmap.png", dpi=150, bbox_inches="tight")
    print("  - roll_heatmap.png")


def _trade_pnl_distribution(trade_data, output_dir):
    """Histogram of per-trade realized PnL with mean/median markers."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)

    for idx, (underlier, tdf) in enumerate(trade_data.items()):
        sells = tdf[tdf["side"] == "SELL"].copy()
        pnl_vals = sells["trade_pnl"].dropna()

        color = PALETTE.get(underlier, "gray")
        ax = axes[idx]
        ax.hist(pnl_vals, bins=80, color=color, alpha=0.8,
                edgecolor="white", linewidth=0.3)
        ax.axvline(0, color="#999", linestyle="--", linewidth=0.8)
        ax.axvline(pnl_vals.mean(), color="#E53935", linestyle="-",
                   linewidth=1.2, label=f"Mean: {pnl_vals.mean():.2f}")
        ax.axvline(pnl_vals.median(), color="#43A047", linestyle="-",
                   linewidth=1.2, label=f"Median: {pnl_vals.median():.2f}")
        ax.set_title(underlier)
        ax.set_xlabel("Per-Trade PnL (points)")
        ax.legend(fontsize=9, framealpha=0.9)

    axes[0].set_ylabel("Frequency")
    fig.suptitle("Trade PnL Distribution", fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(output_dir / "trade_pnl_dist.png", dpi=150, bbox_inches="tight")
    print("  - trade_pnl_dist.png")


def _trades_vs_pnl(pnl_data, trade_data, output_dir):
    """Dual-axis chart: cumulative trade count vs cumulative realized PnL."""
    fig, ax1 = plt.subplots(figsize=(14, 5.5))
    ax2 = ax1.twinx()

    for underlier in pnl_data:
        if underlier not in trade_data:
            continue
        color = PALETTE.get(underlier, "gray")

        tdf = trade_data[underlier].copy()
        buys = tdf[tdf["side"] == "BUY"].copy()
        buys["date"] = buys["timestamp"].dt.date
        daily_trades = buys.groupby("date").size().cumsum()

        pdf = pnl_data[underlier].copy()
        pdf["date"] = pdf["timestamp"].dt.date
        daily_pnl = pdf.groupby("date")["realized_pnl"].last()

        ax1.plot(daily_pnl.index, daily_pnl.values,
                 color=color, linewidth=2, alpha=0.9,
                 label=f"{underlier} PnL")
        ax2.plot(daily_trades.index, daily_trades.values,
                 color=color, linewidth=1.5, alpha=0.5,
                 linestyle="--", label=f"{underlier} Trades")

    ax1.set_ylabel("Cumulative Realized PnL (points)")
    ax2.set_ylabel("Cumulative Trade Count")
    ax1.axhline(0, color="#999", linestyle="-", linewidth=0.5)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2,
              loc="lower left", framealpha=0.9)

    fig.suptitle("Cumulative Trades vs Realized PnL", fontsize=14, fontweight="bold")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "trades_vs_pnl.png", dpi=150, bbox_inches="tight")
    print("  - trades_vs_pnl.png")
