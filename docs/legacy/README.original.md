> Historical project notes. Paths, operational status, badges and test claims below are retained as archival reference and have not all been revalidated. Use the root README and docs/REVIEW.md for this review snapshot.

# Market Indicator Pipeline

A Python market-data pipeline for OHLCV collection, gap handling and technical-indicator calculation.

![review](https://img.shields.io/badge/review-private-374151) ![primary](https://img.shields.io/badge/primary-Python-2563EB) 



## Overview

- Collection scripts cover exchange candles and live updates.
- Gap-handling scripts repair incomplete time-series ranges.
- Indicator functions compute parameterized features over aligned OHLCV data.

**Technology:** Python · pandas · NumPy · pandas-ta-classic · Parquet · exchange HTTP/WebSocket clients

**Persistence and data:** OHLCV and derived indicators are written to Parquet paths. Original market datasets are not bundled.

## Architecture

```text
Exchange candles → normalization and gap checks → pandas indicator calculations → Parquet datasets
```

| Location | Review focus |
| --- | --- |
| [`indicator_calculator.py`](indicator_calculator.py) | Source/configuration inspected for scope and structure |
| [`backpack_klines.py`](backpack_klines.py) | Source/configuration inspected for scope and structure |
| [`binance_live_unified.py`](binance_live_unified.py) | Source/configuration inspected for scope and structure |
| [`fill_gaps.py`](fill_gaps.py) | Source/configuration inspected for scope and structure |
| [`verify_indicators.py`](verify_indicators.py) | Source/configuration inspected for scope and structure |

Internal package and module names are retained where changing them would affect imports or compatibility. This descriptive repository name does not imply a completed package/API migration.

## Setup

Inspect imports before building an isolated Python environment. Pin pandas, NumPy, pandas-ta-classic and the selected Parquet engine; the original data/ paths must be supplied locally.

Start from an isolated environment. Use `.env.example` when present and inspect the configuration loader: an example file is not necessarily loaded automatically. Runtime databases, real account sessions and private credentials are not bundled. Live integration prerequisites are separate from local tests.

## Validation

Static parsing checked 10 Python files and 0 strict JSON files. Python syntax errors: 0; JSON errors: 0. No functional test/build result is claimed for this preparation.



These results apply to the selected checks on the preparation copy. They do not establish deployment readiness, full coverage, live provider availability or measured performance. CI definitions, when present under `docs/ci-templates/`, are inactive review templates; no remote CI badge is claimed.

## Limits and current status

No pinned dependency manifest was present at the selected root. The number of documented indicators is not a measured correctness or strategy-performance result. Live data scripts were not run.



## Roadmap

- [ ] Create a pinned dependency manifest and small OHLCV fixture.
- [ ] Add numerical regression tests for warm-up, NaN and zero denominators.
- [ ] Document timeframe alignment and gap-repair policy.

## History and attribution

No recoverable original Git history was verified for this snapshot. Import and preparation commits use their actual current dates; filesystem timestamps are not treated as development dates.

No open-source license is granted by this preparation. A license and attribution review is required before public redistribution.

## Maintainer and feedback

Douglas de Oliveira Silva · [GitHub](https://github.com/qquante) · 

For this private review, report reproducible issues with a minimal fixture and the exact check output. Keep account data, credentials and generated sensitive reports out of issues and commits. Existing contribution guidelines apply where present.

**Topics:** `python`, `pandas`, `numpy`, `parquet`, `time-series`, `technical-analysis`, `data-engineering`
