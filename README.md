# Market Indicator Pipeline

![Language: Python](https://img.shields.io/badge/Language-Python-3776AB?style=flat-square&logo=python) ![Output: Parquet](https://img.shields.io/badge/Output-Parquet-555555?style=flat-square) [![License: MIT](https://img.shields.io/badge/License-MIT-555555?style=flat-square)](LICENSE)

Prepare OHLCV time series and derive parameterized technical-indicator columns into Parquet datasets for research.

The repository is a collection of data scripts: candle acquisition, gap handling and feature calculation. Its output is a research dataset, not an order-execution strategy.

## Work from candles to features

1. [backpack_klines.py](backpack_klines.py) supplies the candle-collection path.
2. [fill_gaps.py](fill_gaps.py) examines incomplete time ranges.
3. [indicator_calculator.py](indicator_calculator.py) adds indicator families and writes the derived dataset.

The calculator includes custom WaveTrend, pivot points, RSI-divergence, Monday-range and Fibonacci calculations alongside pandas-ta-classic functions. Its configured timeframes range from `1m` through `1d`; local datasets are expected under `data/perps`.

### Example: calculate WaveTrend on your own candle frame

```python
from indicator_calculator import wavetrend

# candles is your pandas DataFrame with high, low and close columns.
features = wavetrend(candles, n1=10, n2=21, wt2_window=4)
```

The returned columns are `wt1`, `wt2` and `wt_cross`. Warm-up periods and missing values remain relevant to downstream research; adding a feature column does not validate a trading rule.

## Environment and current gaps

```console
python -m venv .venv
python -m pip install -r requirements.txt
python -m py_compile backpack_klines.py fill_gaps.py indicator_calculator.py
```

NumPy, pandas, pandas-ta-classic, PyArrow, requests and websockets are declared but not locked as a compatibility-tested environment. Historical datasets are not bundled.

`binance_live_unified.py` imports three helpers absent from this snapshot: `binance_select_top.py`, `binance_backfill_warmup.py` and `indicator_cache.py`. Use the separate scripts as the documented source surface; the unified entrypoint is incomplete. Files named `test_*` include provider diagnostics and should not be treated as a fully offline unit suite.

**Technology:** Python · pandas · NumPy · pandas-ta-classic · Parquet · exchange HTTP/WebSocket clients

Project-authored source: [MIT](LICENSE). Third-party components retain their own notices and terms.
