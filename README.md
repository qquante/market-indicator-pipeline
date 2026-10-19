# Market Indicator Pipeline

A Python market-data pipeline for OHLCV collection, gap handling and technical-indicator calculation.

## Features

- Collection scripts cover exchange candles and live updates.
- Gap-handling scripts repair incomplete time-series ranges.
- Indicator functions compute parameterized features over aligned OHLCV data.

## Stack

Python · pandas · NumPy · pandas-ta-classic · Parquet · exchange HTTP/WebSocket clients

OHLCV and derived indicators are written to Parquet paths. Original market datasets are not bundled.

## Getting started

Inspect imports before building an isolated Python environment. Pin pandas, NumPy, pandas-ta-classic and the selected Parquet engine; the original data/ paths must be supplied locally.

## How it works

```text
Exchange candles → normalization and gap checks → pandas indicator calculations → Parquet datasets
```

## Current limitations

No pinned dependency manifest was present at the selected root. The number of documented indicators is not a measured correctness or strategy-performance result. Live data scripts were not run.

## License

No open-source license has been granted. Redistribution terms remain to be defined.
