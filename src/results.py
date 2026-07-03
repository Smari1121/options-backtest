"""
Result export and console summary.

Writes per-underlier trade logs and PnL snapshot CSVs to the output
directory, and prints a quick summary to stdout.
"""

import pandas as pd


def export_results(results, output_dir):
    """Write trade logs and PnL snapshots as CSVs, then print a summary.

    Args:
        results:    dict of {underlier: Portfolio}.
        output_dir: pathlib.Path to the output folder.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    for underlier, portfolio in results.items():
        if portfolio.trade_log:
            trades_df = pd.DataFrame(portfolio.trade_log)
            trades_df["underlier"] = underlier
            trades_df.to_csv(
                output_dir / f"{underlier}_trades.csv", index=False
            )

        if portfolio.snapshots:
            pnl_df = pd.DataFrame(portfolio.snapshots)
            pnl_df["underlier"] = underlier
            pnl_df.to_csv(
                output_dir / f"{underlier}_pnl.csv", index=False
            )

    print_summary(results)


def print_summary(results):
    """Print key metrics for each underlier to stdout."""
    for underlier, portfolio in results.items():
        print(f"\n--- {underlier} ---")
        print(f"Trades: {len(portfolio.trade_log)}")
        print(f"Realized PnL: {portfolio.realized_pnl:.2f}")

        if not portfolio.snapshots:
            continue

        mtm_values = [s["mtm_pnl"] for s in portfolio.snapshots]
        print(f"Peak MTM: {max(mtm_values):.2f}")
        print(f"Trough MTM: {min(mtm_values):.2f}")
        print(f"Final MTM: {mtm_values[-1]:.2f}")
