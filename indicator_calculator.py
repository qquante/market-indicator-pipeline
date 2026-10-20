"""
Multi-Strategy Backtester - Indicator Calculator v2.0
Calcula 150+ indicadores técnicos e salva junto com OHLCV em Parquet
EXPANDED: Múltiplos parâmetros para cada indicador
"""

import pandas as pd
import pandas_ta_classic as ta
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

# PATHS
DATA_DIR = Path("data/perps")
TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"]

# CUSTOM INDICATORS

def wavetrend(df: pd.DataFrame, n1: int = 10, n2: int = 21, wt2_window: int = 4) -> pd.DataFrame:
    """WaveTrend (LazyBear) - Indicator from TradingView"""
    hlc3 = (df['high'] + df['low'] + df['close']) / 3.0
    esa = hlc3.ewm(span=n1, adjust=False).mean()
    d = (hlc3 - esa).abs().ewm(span=n1, adjust=False).mean()
    denom = (0.015 * d).clip(lower=1e-12)
    ci = ((hlc3 - esa) / denom).astype('float64')
    ci = ci.replace([np.inf, -np.inf], np.nan)
    wt1 = ci.ewm(span=n2, adjust=False).mean()
    wt2 = wt1.rolling(window=wt2_window, min_periods=wt2_window).mean()
    
    wt_cross = np.where(
        (wt1 > wt2) & (wt1.shift(1) <= wt2.shift(1)), 1,
        np.where((wt1 < wt2) & (wt1.shift(1) >= wt2.shift(1)), -1, 0)
    )
    
    return pd.DataFrame({
        'wt1': wt1, 'wt2': wt2, 'wt_cross': wt_cross
    }, index=df.index)


def pivot_points(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot Points classicos"""
    pp = (df['high'] + df['low'] + df['close']) / 3
    r1 = 2 * pp - df['low']
    s1 = 2 * pp - df['high']
    r2 = pp + (df['high'] - df['low'])
    s2 = pp - (df['high'] - df['low'])
    r3 = df['high'] + 2 * (pp - df['low'])
    s3 = df['low'] - 2 * (df['high'] - pp)
    
    return pd.DataFrame({
        'pivot_pp': pp, 'pivot_r1': r1, 'pivot_r2': r2, 'pivot_r3': r3,
        'pivot_s1': s1, 'pivot_s2': s2, 'pivot_s3': s3
    }, index=df.index)


def rsi_divergence(df: pd.DataFrame, rsi_col: str = 'rsi_14', lookback: int = 5) -> pd.DataFrame:
    """Detecta divergencias de RSI"""
    if rsi_col not in df.columns:
        return pd.DataFrame({'rsi_bull_div': 0, 'rsi_bear_div': 0}, index=df.index)
    
    price = df['close']
    rsi = df[rsi_col]
    
    price_lower_low = (price < price.rolling(lookback).min().shift(1))
    rsi_higher_low = (rsi > rsi.rolling(lookback).min().shift(1))
    bullish_div = (price_lower_low & rsi_higher_low).astype(int)
    
    price_higher_high = (price > price.rolling(lookback).max().shift(1))
    rsi_lower_high = (rsi < rsi.rolling(lookback).max().shift(1))
    bearish_div = (price_higher_high & rsi_lower_high).astype(int)
    
    return pd.DataFrame({
        'rsi_bull_div': bullish_div, 'rsi_bear_div': bearish_div
    }, index=df.index)


def monday_range(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula o range de segunda-feira (high/low) + sweep_direction.
    Usa o range da ultima segunda-feira disponivel (propagado via ffill).
    sweep_direction: 1 = swept high, -1 = swept low, 0 = no sweep
    """
    if 'start' not in df.columns:
        return pd.DataFrame({
            'monday_high': np.nan, 'monday_low': np.nan, 'monday_sweep': 0
        }, index=df.index)
    
    df_temp = df.copy()
    df_temp['datetime'] = pd.to_datetime(df_temp['start'])
    df_temp['weekday'] = df_temp['datetime'].dt.weekday
    
    # Inicializar com NaN
    df_temp['monday_high'] = np.nan
    df_temp['monday_low'] = np.nan
    
    # Nas segundas-feiras, preencher com high/low daquele candle
    monday_mask = df_temp['weekday'] == 0
    df_temp.loc[monday_mask, 'monday_high'] = df_temp.loc[monday_mask, 'high']
    df_temp.loc[monday_mask, 'monday_low'] = df_temp.loc[monday_mask, 'low']
    
    # Forward fill para todos os dias
    df_temp['monday_high'] = df_temp['monday_high'].ffill()
    df_temp['monday_low'] = df_temp['monday_low'].ffill()
    
    # Calcular sweep_direction
    # 1 = price swept above monday_high
    # -1 = price swept below monday_low
    # 0 = no sweep
    high_sweep = (df_temp['high'] > df_temp['monday_high']).astype(int)
    low_sweep = (df_temp['low'] < df_temp['monday_low']).astype(int) * -1
    sweep = high_sweep + low_sweep  # Will be 1, -1, or 0 (or 0 if both, rare)
    
    return pd.DataFrame({
        'monday_high': df_temp['monday_high'].values,
        'monday_low': df_temp['monday_low'].values,
        'monday_sweep': sweep.values
    }, index=df.index)


def fibonacci_retracement(df: pd.DataFrame, lookback: int = 50) -> pd.DataFrame:
    """Calcula niveis de Fibonacci Retracement"""
    rolling_high = df['high'].rolling(lookback).max()
    rolling_low = df['low'].rolling(lookback).min()
    diff = rolling_high - rolling_low
    
    return pd.DataFrame({
        'fib_236': rolling_high - 0.236 * diff,
        'fib_382': rolling_high - 0.382 * diff,
        'fib_500': rolling_high - 0.500 * diff,
        'fib_618': rolling_high - 0.618 * diff,
        'fib_786': rolling_high - 0.786 * diff,
    }, index=df.index)


def fibonacci_extension(df: pd.DataFrame, lookback: int = 50) -> pd.DataFrame:
    """
    Calcula niveis de Fibonacci Extension.
    Usa o swing high/low dos ultimos 'lookback' periodos.
    Extension levels: 127.2%, 161.8%, 200%, 261.8%
    """
    rolling_high = df['high'].rolling(lookback).max()
    rolling_low = df['low'].rolling(lookback).min()
    diff = rolling_high - rolling_low
    
    return pd.DataFrame({
        'fib_ext_1272': rolling_low + 1.272 * diff,
        'fib_ext_1618': rolling_low + 1.618 * diff,
        'fib_ext_2000': rolling_low + 2.000 * diff,
        'fib_ext_2618': rolling_low + 2.618 * diff,
    }, index=df.index)


def zigzag(df: pd.DataFrame, deviation: float = 5.0) -> pd.DataFrame:
    """
    Implementa ZigZag indicator para detectar swing highs/lows.
    deviation: porcentagem minima de movimento para considerar um swing (default 5%)
    
    Retorna:
    - zigzag_pivot: 1 = swing high, -1 = swing low, 0 = no pivot
    - zigzag_value: valor do pivot (preco) ou NaN
    """
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    n = len(df)
    
    pivot = np.zeros(n)
    pivot_value = np.full(n, np.nan)
    
    # Threshold em decimal
    threshold = deviation / 100.0
    
    # Encontrar primeiro ponto
    last_pivot_type = 0  # 1 = high, -1 = low
    last_pivot_price = close[0]
    last_pivot_idx = 0
    
    for i in range(1, n):
        if last_pivot_type == 0:
            # Inicializar
            if high[i] >= last_pivot_price * (1 + threshold):
                last_pivot_type = 1
                last_pivot_price = high[i]
                last_pivot_idx = i
            elif low[i] <= last_pivot_price * (1 - threshold):
                last_pivot_type = -1
                last_pivot_price = low[i]
                last_pivot_idx = i
        
        elif last_pivot_type == 1:  # Ultimo pivot foi high
            if high[i] > last_pivot_price:
                # Novo high, atualizar
                last_pivot_price = high[i]
                last_pivot_idx = i
            elif low[i] <= last_pivot_price * (1 - threshold):
                # Reversao para baixo, marcar o ultimo high como pivot
                pivot[last_pivot_idx] = 1
                pivot_value[last_pivot_idx] = last_pivot_price
                # Agora procurar low
                last_pivot_type = -1
                last_pivot_price = low[i]
                last_pivot_idx = i
        
        elif last_pivot_type == -1:  # Ultimo pivot foi low
            if low[i] < last_pivot_price:
                # Novo low, atualizar
                last_pivot_price = low[i]
                last_pivot_idx = i
            elif high[i] >= last_pivot_price * (1 + threshold):
                # Reversao para cima, marcar o ultimo low como pivot
                pivot[last_pivot_idx] = -1
                pivot_value[last_pivot_idx] = last_pivot_price
                # Agora procurar high
                last_pivot_type = 1
                last_pivot_price = high[i]
                last_pivot_idx = i
    
    return pd.DataFrame({
        'zigzag_pivot': pivot,
        'zigzag_value': pivot_value
    }, index=df.index)


# MAIN INDICATOR CALCULATOR v2.0

def calculate_all_indicators(df: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """
    Calcula TODOS os indicadores para um DataFrame OHLCV
    v2.0: Agora com 150+ colunas de indicadores
    """
    
    result = df.copy()
    result.columns = result.columns.str.lower()
    original_cols = set(result.columns)
    
    if verbose:
        print(f"  Calculando indicadores para {len(result)} candles...")
    
    # MOMENTUM - EXPANDED
    if verbose:
        print("    [1/7] Momentum indicators...")
    
    # RSI - 10 periodos
    for period in [5, 7, 9, 10, 12, 14, 21, 25, 30, 50]:
        result[f'rsi_{period}'] = ta.rsi(result['close'], length=period)
    
    # MACD - 3 configs
    for fast, slow, signal in [(12, 26, 9), (8, 17, 9), (5, 35, 5)]:
        macd = ta.macd(result['close'], fast=fast, slow=slow, signal=signal)
        if macd is not None:
            macd.columns = [f'macd_{fast}_{slow}_{signal}', f'macdh_{fast}_{slow}_{signal}', f'macds_{fast}_{slow}_{signal}']
            result = pd.concat([result, macd], axis=1)
    
    # Stochastic - 3 configs
    for k, d, smooth in [(14, 3, 3), (5, 3, 3), (21, 5, 5)]:
        stoch = ta.stoch(result['high'], result['low'], result['close'], k=k, d=d, smooth_k=smooth)
        if stoch is not None:
            stoch.columns = [f'stochk_{k}_{d}_{smooth}', f'stochd_{k}_{d}_{smooth}']
            result = pd.concat([result, stoch], axis=1)
    
    # Stochastic RSI
    stochrsi = ta.stochrsi(result['close'], length=14)
    if stochrsi is not None:
        result = pd.concat([result, stochrsi], axis=1)
    
    # Williams %R - 3 periodos
    for period in [10, 14, 21]:
        result[f'willr_{period}'] = ta.willr(result['high'], result['low'], result['close'], length=period)
    
    # CCI - 3 periodos
    for period in [14, 20, 50]:
        result[f'cci_{period}'] = ta.cci(result['high'], result['low'], result['close'], length=period)
    
    # MFI - 3 periodos
    for period in [9, 14, 21]:
        result[f'mfi_{period}'] = ta.mfi(result['high'], result['low'], result['close'], result['volume'], length=period)
    
    # ROC - 3 periodos
    for period in [9, 12, 21]:
        result[f'roc_{period}'] = ta.roc(result['close'], length=period)
    
    # Momentum - 3 periodos
    for period in [10, 14, 21]:
        result[f'mom_{period}'] = ta.mom(result['close'], length=period)
    
    # TSI
    tsi = ta.tsi(result['close'], fast=13, slow=25)
    if tsi is not None:
        result = pd.concat([result, tsi], axis=1)
    
    # Ultimate Oscillator
    result['uo'] = ta.uo(result['high'], result['low'], result['close'])
    
    # Awesome Oscillator
    result['ao'] = ta.ao(result['high'], result['low'])
    
    # PPO
    ppo = ta.ppo(result['close'], fast=12, slow=26, signal=9)
    if ppo is not None:
        result = pd.concat([result, ppo], axis=1)
    
    # CMO - 2 periodos
    for period in [14, 21]:
        result[f'cmo_{period}'] = ta.cmo(result['close'], length=period)
    
    # Fisher Transform
    fisher = ta.fisher(result['high'], result['low'], length=9)
    if fisher is not None:
        result = pd.concat([result, fisher], axis=1)
    
    # TREND - EXPANDED
    if verbose:
        print("    [2/7] Trend indicators...")
    
    # SMA - 10 periodos
    for period in [5, 8, 10, 13, 20, 21, 34, 50, 100, 200]:
        result[f'sma_{period}'] = ta.sma(result['close'], length=period)
    
    # EMA - 10 periodos
    for period in [5, 8, 9, 12, 13, 21, 34, 50, 100, 200]:
        result[f'ema_{period}'] = ta.ema(result['close'], length=period)
    
    # WMA
    for period in [10, 20, 50]:
        result[f'wma_{period}'] = ta.wma(result['close'], length=period)
    
    # HMA
    for period in [9, 14, 21]:
        result[f'hma_{period}'] = ta.hma(result['close'], length=period)
    
    # TEMA
    result['tema_9'] = ta.tema(result['close'], length=9)
    
    # KAMA
    result['kama_10'] = ta.kama(result['close'], length=10)
    
    # DEMA
    result['dema_9'] = ta.dema(result['close'], length=9)
    
    # ADX - 3 periodos
    for period in [7, 14, 25]:
        adx = ta.adx(result['high'], result['low'], result['close'], length=period)
        if adx is not None:
            adx.columns = [f'adx_{period}', f'dmp_{period}', f'dmn_{period}']
            result = pd.concat([result, adx], axis=1)
    
    # Ichimoku
    ichimoku = ta.ichimoku(result['high'], result['low'], result['close'])
    if ichimoku is not None and isinstance(ichimoku, tuple):
        result = pd.concat([result, ichimoku[0]], axis=1)
    
    # Parabolic SAR
    psar = ta.psar(result['high'], result['low'], result['close'])
    if psar is not None:
        result = pd.concat([result, psar], axis=1)
    
    # Supertrend - 3 configs
    for length, mult in [(7, 2.0), (10, 3.0), (14, 3.5)]:
        supertrend = ta.supertrend(result['high'], result['low'], result['close'], length=length, multiplier=mult)
        if supertrend is not None:
            supertrend.columns = [f'supert_{length}_{mult}', f'supertd_{length}_{mult}', f'supertl_{length}_{mult}', f'superts_{length}_{mult}']
            result = pd.concat([result, supertrend], axis=1)
    
    # Aroon
    aroon = ta.aroon(result['high'], result['low'], length=25)
    if aroon is not None:
        result = pd.concat([result, aroon], axis=1)
    
    # STC
    stc = ta.stc(result['close'])
    if stc is not None:
        result = pd.concat([result, stc], axis=1)
    
    # Vortex
    vortex = ta.vortex(result['high'], result['low'], result['close'], length=14)
    if vortex is not None:
        result = pd.concat([result, vortex], axis=1)
    
    # DPO (Detrended Price Oscillator) - FALTAVA
    result['dpo_20'] = ta.dpo(result['close'], length=20)
    
    # VWMA (Volume Weighted MA) - FALTAVA
    result['vwma_20'] = ta.vwma(result['close'], result['volume'], length=20)
    
    # VOLATILITY - EXPANDED
    if verbose:
        print("    [3/7] Volatility indicators...")
    
    # ATR - 3 periodos
    for period in [7, 14, 21]:
        result[f'atr_{period}'] = ta.atr(result['high'], result['low'], result['close'], length=period)
    
    # NATR
    result['natr_14'] = ta.natr(result['high'], result['low'], result['close'], length=14)
    
    # True Range
    result['true_range'] = ta.true_range(result['high'], result['low'], result['close'])
    
    # Bollinger Bands - 3 configs
    for length, std in [(20, 1.5), (20, 2.0), (20, 2.5)]:
        bbands = ta.bbands(result['close'], length=length, std=std)
        if bbands is not None:
            bbands.columns = [f'bbl_{length}_{std}', f'bbm_{length}_{std}', f'bbu_{length}_{std}', f'bbb_{length}_{std}', f'bbp_{length}_{std}']
            result = pd.concat([result, bbands], axis=1)
    
    # Keltner Channels
    kc = ta.kc(result['high'], result['low'], result['close'], length=20)
    if kc is not None:
        result = pd.concat([result, kc], axis=1)
    
    # Donchian Channels
    donchian = ta.donchian(result['high'], result['low'], lower_length=20, upper_length=20)
    if donchian is not None:
        result = pd.concat([result, donchian], axis=1)
    
    # Standard Deviation - 2 periodos
    for period in [10, 20]:
        result[f'stdev_{period}'] = ta.stdev(result['close'], length=period)
    
    # VOLUME - EXPANDED
    if verbose:
        print("    [4/7] Volume indicators...")
    
    # OBV
    result['obv'] = ta.obv(result['close'], result['volume'])
    
    # CMF - 2 periodos
    for period in [10, 20]:
        result[f'cmf_{period}'] = ta.cmf(result['high'], result['low'], result['close'], result['volume'], length=period)
    
    # ADL
    result['adl'] = ta.ad(result['high'], result['low'], result['close'], result['volume'])
    
    # Chaikin Oscillator
    result['adosc'] = ta.adosc(result['high'], result['low'], result['close'], result['volume'])
    
    # Force Index - 2 periodos
    for period in [7, 13]:
        result[f'efi_{period}'] = ta.efi(result['close'], result['volume'], length=period)
    
    # NVI / PVI
    result['nvi'] = ta.nvi(result['close'], result['volume'])
    result['pvi'] = ta.pvi(result['close'], result['volume'])
    
    # PVT
    result['pvt'] = ta.pvt(result['close'], result['volume'])
    
    # VWAP (Volume Weighted Average Price) - FALTAVA
    # VWAP precisa de indice datetime
    try:
        if 'start' in result.columns:
            temp_df = result.copy()
            temp_df.index = pd.to_datetime(temp_df['start'])
            vwap = ta.vwap(temp_df['high'], temp_df['low'], temp_df['close'], temp_df['volume'])
            if vwap is not None:
                result['vwap'] = vwap.values
    except Exception as e:
        pass
    
    # Klinger Volume Oscillator - FALTAVA
    try:
        kvo = ta.kvo(result['high'], result['low'], result['close'], result['volume'])
        if kvo is not None:
            result = pd.concat([result, kvo], axis=1)
    except:
        pass
    
    # Elder Ray - FALTAVA
    try:
        elder = ta.eri(result['high'], result['low'], result['close'])
        if elder is not None:
            result = pd.concat([result, elder], axis=1)
    except:
        pass
    
    # CUSTOM INDICATORS
    if verbose:
        print("    [5/7] Custom indicators...")
    
    # WaveTrend
    wt = wavetrend(result)
    result = pd.concat([result, wt], axis=1)
    
    # Pivot Points
    pivots = pivot_points(result)
    result = pd.concat([result, pivots], axis=1)
    
    # RSI Divergence
    div = rsi_divergence(result, 'rsi_14', lookback=5)
    result = pd.concat([result, div], axis=1)
    
    # Monday Range (FIXED)
    mr = monday_range(result)
    result = pd.concat([result, mr], axis=1)
    
    # Fibonacci Retracement
    fib = fibonacci_retracement(result, lookback=50)
    result = pd.concat([result, fib], axis=1)
    
    # Fibonacci Extension - FALTAVA
    fib_ext = fibonacci_extension(result, lookback=50)
    result = pd.concat([result, fib_ext], axis=1)
    
    # ZigZag - FALTAVA (detecta swing highs/lows)
    zz = zigzag(result, deviation=5.0)
    result = pd.concat([result, zz], axis=1)
    
    # DERIVED SIGNALS
    if verbose:
        print("    [6/7] Derived signals...")
    
    # OBOS flags - para varios RSI
    result['is_oversold_14'] = (result['rsi_14'] < 30).astype(int)
    result['is_overbought_14'] = (result['rsi_14'] > 70).astype(int)
    result['is_oversold_9'] = (result['rsi_9'] < 30).astype(int)
    result['is_overbought_9'] = (result['rsi_9'] > 70).astype(int)
    
    # MA Crossover signals
    result['ema_cross_9_21'] = np.where(
        (result['ema_9'] > result['ema_21']) & (result['ema_9'].shift(1) <= result['ema_21'].shift(1)), 1,
        np.where((result['ema_9'] < result['ema_21']) & (result['ema_9'].shift(1) >= result['ema_21'].shift(1)), -1, 0)
    )
    
    result['sma_cross_20_50'] = np.where(
        (result['sma_20'] > result['sma_50']) & (result['sma_20'].shift(1) <= result['sma_50'].shift(1)), 1,
        np.where((result['sma_20'] < result['sma_50']) & (result['sma_20'].shift(1) >= result['sma_50'].shift(1)), -1, 0)
    )
    
    # CLEANUP
    if verbose:
        print("    [7/7] Cleanup...")
    
    # Normalizar TODAS as colunas para lowercase e remover duplicatas
    result.columns = result.columns.str.lower()
    result = result.loc[:, ~result.columns.duplicated()]
    
    if verbose:
        print(f"  [OK] Total colunas: {len(result.columns)}")
    
    return result


def process_symbol(symbol: str, timeframes: List[str] = None, verbose: bool = True):
    """Processa um simbolo: calcula indicadores para todos timeframes"""
    if timeframes is None:
        timeframes = TIMEFRAMES
    
    symbol_dir = DATA_DIR / symbol
    if not symbol_dir.exists():
        print(f"[ERROR] {symbol} nao encontrado")
        return
    
    print(f"\n{'='*60}")
    print(f"[PROCESSING] {symbol}")
    print(f"{'='*60}")
    
    for tf in timeframes:
        parquet_file = symbol_dir / f"{tf}.parquet"
        if not parquet_file.exists():
            print(f"  [WARN] {tf}.parquet not found")
            continue
        
        print(f"\n  [{tf}] Carregando dados...")
        df = pd.read_parquet(parquet_file)
        
        min_candles = 250
        if len(df) < min_candles:
            print(f"  [WARN] {tf}: Only {len(df)} candles (min: {min_candles})")
        
        df_with_indicators = calculate_all_indicators(df, verbose=verbose)
        
        df_with_indicators.to_parquet(parquet_file, index=False)
        print(f"  [SAVED] {parquet_file.name} ({len(df_with_indicators.columns)} columns)")


def main():
    """Entry point"""
    import sys
    
    if len(sys.argv) > 1:
        symbols = sys.argv[1:]
    else:
        symbols = ["BTC_USDC_PERP"]
    
    for symbol in symbols:
        process_symbol(symbol)
    
    print("\n" + "="*60)
    print("[DONE] PROCESSING COMPLETE!")
    print("="*60)


if __name__ == "__main__":
    main()
