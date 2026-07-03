# data/

This folder holds the raw tick data downloaded from the provided Google Drive link. It is not tracked in git. (File size and Privacy concerns)

## Expected structure

After unzipping the archive, place the `allData` folder here so the layout looks like this:

```
data/
└── allData/
    ├── NSE_20221101/
    │   ├── Futures (Continuous)/
    │   │   ├── NIFTY-I.csv
    │   │   ├── NIFTY-II.csv
    │   │   ├── BANKNIFTY-I.csv
    │   │   └── ...
    │   └── Options/
    │       ├── NIFTY22110317500CE.csv
    │       ├── NIFTY22110317500PE.csv
    │       └── ...
    ├── NSE_20221102/
    └── ...
```

## File format

All CSV files have no header row. The five columns are:

| Column | Description |
| --- | --- |
| Date | Trading date in YYYYMMDD format |
| Time | Timestamp in HH:MM:SS format |
| Price | Last traded price |
| Volume | Volume traded in that tick |
| Open Interest | Open interest at that moment |

## Option filename convention

Option filenames encode the full instrument identity:

```
NIFTY  221103  17500  CE  .csv
  ^       ^      ^    ^
  |       |      |    option type (CE or PE)
  |       |      strike price
  |       expiry date (YYMMDD)
  underlier
```

The code in `src/loader.py` parses this automatically.

## Futures files

Only the front-month contract (`-I.csv`) is used. The `-II.csv` and `-III.csv` files (second and third month) are loaded but ignored by the simulation.
