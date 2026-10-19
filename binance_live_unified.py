import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Tuple
import numpy as np

import pandas as pd
import websockets

from binance_select_top import select_top20_prefer_highest_quote_volume
from binance_backfill_warmup import backfill_symbol, klines_to_df, save_csv, CSV_ROOT
from indicator_cache import compute_wavetrend as ic_compute_wavetrend


WS_BASE = "wss://fstream.binance.com/stream?streams="

# In-memory OHLCV per symbol/interval (index: ms)
SERIES: Dict[Tuple[str, str], pd.DataFrame] = {}
MAX_IN_MEMORY = 20000
MIN_WARMUP = {
    '1m': 3000,
    '5m': 1200,
    '15m': 800,
}


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def load_recent_csv(symbol: str, interval: str, max_files: int = 5) -> pd.DataFrame:
    folder = os.path.join(CSV_ROOT, symbol, interval)
    if not os.path.isdir(folder):
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])  # empty
    files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.csv')]
    files.sort()
    files = files[-max_files:]
    dfs: List[pd.DataFrame] = []
    for p in files:
        try:
            df = pd.read_csv(p)
            # Expect columns: Open,High,Low,Close,Volume with Date index already saved by pipeline
            # If missing index, reconstruct using filename date (best-effort)
            cols = {c.lower(): c for c in df.columns}
            df = df.rename(columns={
                cols.get('open', 'Open'): 'Open',
                cols.get('high', 'High'): 'High',
                cols.get('low', 'Low'): 'Low',
                cols.get('close', 'Close'): 'Close',
                cols.get('volume', 'Volume'): 'Volume',
            })
            # Create Date index from known intervals if not present
            if 'Date' not in df.columns:
                # Try recover from timestampEnd if present
                if 'timestampEnd' in df.columns:
                    dt = pd.to_datetime(df['timestampEnd'].astype('int64'), unit='s', utc=True)
                    df = df.set_index(dt)
                else:
                    # Fallback: skip
                    continue
            else:
                df['Date'] = pd.to_datetime(df['Date'], utc=True)
                df = df.set_index('Date')
            dfs.append(df[['Open', 'High', 'Low', 'Close', 'Volume']])
        except Exception:
            continue
    if not dfs:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
    out = pd.concat(dfs).sort_index()
    out = out[~out.index.duplicated(keep='last')]
    return out


def preload_series(symbols: List[str], intervals: List[str], max_files: int = 20) -> None:
    for sym in symbols:
        for iv in intervals:
            df = load_recent_csv(sym, iv, max_files=max_files)
            if df is None or df.empty:
                continue
            df_ms = df.copy()
            # Ensure datetime index exists and convert to ms int index
            if not isinstance(df_ms.index, pd.DatetimeIndex):
                df_ms.index = pd.to_datetime(df_ms.index, utc=True)
            ms_index = (df_ms.index.view('int64') // 10**6)
            internal = df_ms.rename(columns={'Open':'open','High':'high','Low':'low','Close':'close','Volume':'volume'})
            internal.index = ms_index
            internal.index.name = 'timestampMs'
            key = (sym, iv)
            SERIES[key] = internal[['open','high','low','close','volume']].sort_index().tail(MAX_IN_MEMORY)


def compute_wavetrend_lb(df: pd.DataFrame, n1: int = 10, n2: int = 21, wt2_window: int = 4) -> pd.DataFrame:
    # LazyBear WaveTrend on hlc3 with factor 0.015
    hlc3 = (df['High'] + df['Low'] + df['Close']) / 3.0
    esa = hlc3.ewm(span=n1, adjust=False).mean()
    d = (hlc3 - esa).abs().ewm(span=n1, adjust=False).mean()
    denom = (0.015 * d).clip(lower=1e-12)
    ci = ((hlc3 - esa) / denom).astype('float64')
    ci = ci.replace([np.inf, -np.inf], np.nan)
    tci = ci.ewm(span=n2, adjust=False).mean()
    wt1 = tci
    wt2 = wt1.rolling(window=wt2_window, min_periods=wt2_window).mean()
    return pd.DataFrame({'wt1': wt1, 'wt2': wt2}, index=df.index)


def append_candle(symbol: str, interval: str, end_ms: int, o: float, h: float, l: float, c: float, v: float):
    key = (symbol, interval)
    series = SERIES.get(key)
    if series is None:
        series = pd.DataFrame(columns=["open", "high", "low", "close", "volume"]).astype({
            'open': float, 'high': float, 'low': float, 'close': float, 'volume': float
        })
        series.index.name = 'timestampMs'
    series.loc[end_ms, ["open", "high", "low", "close", "volume"]] = [o, h, l, c, v]
    SERIES[key] = series[~series.index.duplicated(keep='last')].sort_index().tail(MAX_IN_MEMORY)


def persist_single(symbol: str, interval: str, end_ms: int, o: float, h: float, l: float, c: float, v: float):
    dt = datetime.utcfromtimestamp(end_ms / 1000)
    df = pd.DataFrame([[o, h, l, c, v]], columns=["Open", "High", "Low", "Close", "Volume"], index=[pd.Timestamp(dt, tz=timezone.utc)])
    df.index.name = 'Date'
    save_csv(symbol, interval, df)


def compute_and_log_wavetrend(symbol: str, interval: str, tail_count: int = 2000):
    key = (symbol, interval)
    series = SERIES.get(key)
    if series is None or series.empty:
        return
    # Warm-up guard
    min_need = int(MIN_WARMUP.get(interval, 200))
    if len(series) < min_need:
        return
    tail = series.tail(tail_count).copy()
    df = tail.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'})
    # Ensure datetime index for logging/indicators
    df.index = pd.to_datetime(df.index, unit='ms', utc=True)

    wt = compute_wavetrend_lb(df, n1=10, n2=21, wt2_window=4)
    last = wt.iloc[-1]
    wt1 = float(last.get('wt1', float('nan')))
    wt2 = float(last.get('wt2', float('nan')))
    if pd.isna(wt1) or pd.isna(wt2):
        return
    price = float(df['Close'].iloc[-1])
    ts = df.index[-1].isoformat()
    state = 'Normal'
    if wt1 > 60:
        state = 'Overbought'
    elif wt1 < -60:
        state = 'Oversold'
    print(f"[WT] {symbol} {interval} [{ts}] Price={price:.4f} WT1={wt1:.2f} WT2={wt2:.2f} State={state}")


async def stream_ws(symbols: List[str], intervals: List[str]):
    streams = '/'.join([f"{s.lower()}@kline_{iv}" for s in symbols for iv in intervals])
    url = WS_BASE + streams
    print(f"Connecting WS: {url}")
    async with websockets.connect(url, ping_interval=55, ping_timeout=30) as ws:
        while True:
            msg = await ws.recv()
            try:
                obj = json.loads(msg)
            except Exception:
                continue
            data = obj.get('data') or obj
            if not isinstance(data, dict):
                continue
            if data.get('e') != 'kline':
                continue
            k = data.get('k', {})
            if not k.get('x', False):
                continue  # only on closed candle
            sym = k.get('s')
            end_ms = int(k.get('T'))
            iv = str(k.get('i'))
            o = float(k.get('o'))
            h = float(k.get('h'))
            l = float(k.get('l'))
            c = float(k.get('c'))
            v = float(k.get('v'))
            append_candle(sym, iv, end_ms, o, h, l, c, v)
            persist_single(sym, iv, end_ms, o, h, l, c, v)
            compute_and_log_wavetrend(sym, iv)


def do_backfill_1m_concurrent(symbols: List[str], candles_needed: int = 10_000, max_workers: int = 4):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    tasks = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for sym in symbols:
            tasks.append(ex.submit(backfill_symbol, sym, '1m', candles_needed))
        for fut in as_completed(tasks):
            try:
                fut.result()
            except Exception:
                pass


def do_backfill_concurrent(symbols: List[str], intervals: List[str], candles_needed: Dict[str, int], max_workers: int = 4):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    tasks = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for sym in symbols:
            for iv in intervals:
                need = int(candles_needed.get(iv, 0))
                if need <= 0:
                    continue
                tasks.append(ex.submit(backfill_symbol, sym, iv, need))
        for fut in as_completed(tasks):
            try:
                fut.result()
            except Exception:
                pass


async def stream_top20_with_backfill():
    # 1) Select top 20 symbols
    symbols = select_top20_prefer_highest_quote_volume()
    print(f"Selected {len(symbols)} symbols: {', '.join(symbols)}")
    # 2) Start WS for 1m/5m/15m immediately and run backfill in parallel
    intervals = ['1m', '5m', '15m']
    ws_task = asyncio.create_task(stream_ws(symbols, intervals))
    need = {'1m': 10_000, '5m': 1_000, '15m': 500}
    await asyncio.to_thread(do_backfill_concurrent, symbols, intervals, need, 4)
    preload_series(symbols, intervals, max_files=30)
    await ws_task


def main():
    asyncio.run(stream_top20_with_backfill())


if __name__ == '__main__':
    main()


