# output/

Everything the backtest generates lands here. PNGs and trade CSVs are tracked in git so results are visible without running the code. The second-by-second PnL snapshots (`*_pnl.csv`) are excluded because they are ~40 MB each.

## CSVs

Two files per underlier are written after each run.

### `{UNDERLIER}_trades.csv`

One row per individual trade execution.

| Column | Description |
| --- | --- |
| timestamp | Exact second the trade was executed |
| strike | Strike price of the option traded |
| type | CE or PE |
| side | BUY or SELL |
| price | Execution price |
| trade_pnl | Realized PnL on this trade (SELL rows only) |
| underlier | NIFTY or BANKNIFTY |

### `{UNDERLIER}_pnl.csv`

One row per second throughout the simulation.

| Column | Description |
| --- | --- |
| timestamp | The second being recorded |
| mtm_pnl | Total PnL including unrealized (mark-to-market) |
| realized_pnl | Cumulative locked-in PnL from closed trades |
| positions | Pipe-separated list of instruments currently held |
| underlier | NIFTY or BANKNIFTY |

## Plots

| File | What it shows |
| --- | --- |
| `cumulative_pnl.png` | MTM PnL across the full month for both underliers |
| `daily_pnl.png` | Each day's realized PnL contribution as a bar chart |
| `drawdown.png` | Drawdown from the running peak of cumulative MTM |
| `intraday_pnl.png` | Second-level PnL for the most volatile day (NIFTY) |
| `strategy_action.png` | Futures price vs the held strike, showing roll points |
| `roll_heatmap.png` | When during the day the strategy rolls most |
| `trade_pnl_dist.png` | Histogram of per-trade realized PnL with mean and median |
| `trades_vs_pnl.png` | Dual-axis view: cumulative trade count vs cumulative PnL |
