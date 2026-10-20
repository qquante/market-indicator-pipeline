"""
Verificacao Extensiva de Indicadores - Testa CADA indicador do task.md
Verifica: presenca, valores validos, ranges esperados, formulas matematicas
"""
import pandas as pd
import numpy as np
from pathlib import Path

def load_data(timeframe: str = "1h") -> pd.DataFrame:
    """Carrega dados do BTC"""
    return pd.read_parquet(f"data/perps/BTC_USDC_PERP/{timeframe}.parquet")

def test_column_exists(df, col_name: str) -> bool:
    """Verifica se coluna existe"""
    return col_name in df.columns

def test_no_all_nan(df, col_name: str) -> bool:
    """Verifica se coluna nao esta toda NaN"""
    if col_name not in df.columns:
        return False
    return not df[col_name].isna().all()

def test_range(df, col_name: str, min_val: float, max_val: float) -> bool:
    """Verifica se valores estao dentro do range esperado"""
    if col_name not in df.columns:
        return False
    valid = df[col_name].dropna()
    if len(valid) == 0:
        return False
    return valid.min() >= min_val and valid.max() <= max_val

def test_formula(df, col_name: str, expected_series: pd.Series, tolerance: float = 0.01) -> bool:
    """Verifica se os valores correspondem a formula esperada"""
    if col_name not in df.columns:
        return False
    actual = df[col_name].dropna()
    expected = expected_series.dropna()
    if len(actual) == 0 or len(expected) == 0:
        return False
    # Alinhar indices e comparar
    common = actual.index.intersection(expected.index)
    if len(common) < 10:
        return False
    diff = (actual.loc[common] - expected.loc[common]).abs()
    return (diff / expected.loc[common].abs().clip(lower=1e-10)).mean() < tolerance

def run_tests():
    print("=" * 70)
    print("VERIFICACAO EXTENSIVA DE INDICADORES")
    print("=" * 70)
    
    df = load_data("1h")
    print(f"\nDados carregados: {len(df)} candles, {len(df.columns)} colunas\n")
    
    results = {"PASSED": 0, "FAILED": 0, "WARNINGS": 0}
    
    def log_result(category: str, test_name: str, passed: bool, warning: str = ""):
        status = "PASS" if passed else "FAIL"
        if warning:
            status = "WARN"
            results["WARNINGS"] += 1
        elif passed:
            results["PASSED"] += 1
        else:
            results["FAILED"] += 1
        
        icon = "[OK]" if passed else "[!!]" if not warning else "[??]"
        print(f"  {icon} {category:20} | {test_name:30} | {status}")
        if warning:
            print(f"      -> {warning}")
    
    # 2.1.1 MOMENTUM (15)
    print("\n" + "=" * 70)
    print("2.1.1 MOMENTUM")
    print("=" * 70)
    
    # RSI (9, 14, 21)
    for period in [9, 14, 21]:
        col = f"rsi_{period}"
        exists = test_column_exists(df, col)
        log_result("RSI", f"rsi_{period} existe", exists)
        if exists:
            in_range = test_range(df, col, 0, 100)
            log_result("RSI", f"rsi_{period} range [0-100]", in_range)
    
    # MACD (12/26/9, 8/17/9)
    for fast, slow, sig in [(12, 26, 9), (8, 17, 9)]:
        col = f"macd_{fast}_{slow}_{sig}"
        exists = test_column_exists(df, col)
        log_result("MACD", f"macd_{fast}_{slow}_{sig} existe", exists)
        col_h = f"macdh_{fast}_{slow}_{sig}"
        exists_h = test_column_exists(df, col_h)
        log_result("MACD", f"macdh_{fast}_{slow}_{sig} existe", exists_h)
        col_s = f"macds_{fast}_{slow}_{sig}"
        exists_s = test_column_exists(df, col_s)
        log_result("MACD", f"macds_{fast}_{slow}_{sig} existe", exists_s)
    
    # Stochastic (14/3/3)
    for col in ["stochk_14_3_3", "stochd_14_3_3"]:
        exists = test_column_exists(df, col)
        log_result("Stochastic", f"{col} existe", exists)
        if exists:
            in_range = test_range(df, col, 0, 100)
            log_result("Stochastic", f"{col} range [0-100]", in_range)
    
    # Stochastic RSI
    for col in ["stochrsik_14_14_3_3", "stochrsid_14_14_3_3"]:
        exists = test_column_exists(df, col)
        log_result("StochRSI", f"{col} existe", exists)
    
    # Williams %R
    col = "willr_14"
    exists = test_column_exists(df, col)
    log_result("Williams %R", f"{col} existe", exists)
    if exists:
        in_range = test_range(df, col, -100, 0)
        log_result("Williams %R", f"{col} range [-100,0]", in_range)
    
    # CCI
    col = "cci_20"
    exists = test_column_exists(df, col)
    log_result("CCI", f"{col} existe", exists)
    
    # MFI
    col = "mfi_14"
    exists = test_column_exists(df, col)
    log_result("MFI", f"{col} existe", exists)
    if exists:
        in_range = test_range(df, col, 0, 100)
        log_result("MFI", f"{col} range [0-100]", in_range)
    
    # ROC
    col = "roc_12"
    exists = test_column_exists(df, col)
    log_result("ROC", f"{col} existe", exists)
    
    # Momentum
    col = "mom_10"
    exists = test_column_exists(df, col)
    log_result("Momentum", f"{col} existe", exists)
    
    # TSI
    for col in ["tsi_13_25_13", "tsis_13_25_13"]:
        exists = test_column_exists(df, col)
        log_result("TSI", f"{col} existe", exists)
    
    # Ultimate Oscillator
    col = "uo"
    exists = test_column_exists(df, col)
    log_result("Ultimate Osc", f"{col} existe", exists)
    if exists:
        in_range = test_range(df, col, 0, 100)
        log_result("Ultimate Osc", f"{col} range [0-100]", in_range)
    
    # Awesome Oscillator
    col = "ao"
    exists = test_column_exists(df, col)
    log_result("Awesome Osc", f"{col} existe", exists)
    
    # PPO
    for col in ["ppo_12_26_9", "ppoh_12_26_9", "ppos_12_26_9"]:
        exists = test_column_exists(df, col)
        log_result("PPO", f"{col} existe", exists)
    
    # CMO
    col = "cmo_14"
    exists = test_column_exists(df, col)
    log_result("CMO", f"{col} existe", exists)
    if exists:
        in_range = test_range(df, col, -100, 100)
        log_result("CMO", f"{col} range [-100,100]", in_range)
    
    # Fisher Transform
    for col in ["fishert_9_1", "fisherts_9_1"]:
        exists = test_column_exists(df, col)
        log_result("Fisher", f"{col} existe", exists)
    
    # 2.1.2 TREND (12)
    print("\n" + "=" * 70)
    print("2.1.2 TREND")
    print("=" * 70)
    
    # SMA (10, 20, 50, 100, 200)
    for period in [10, 20, 50, 100, 200]:
        col = f"sma_{period}"
        exists = test_column_exists(df, col)
        log_result("SMA", f"sma_{period} existe", exists)
        if exists:
            # Verificar formula: SMA deve ser media dos ultimos N closes
            expected = df['close'].rolling(period).mean()
            formula_ok = test_formula(df, col, expected)
            log_result("SMA", f"sma_{period} formula correta", formula_ok)
    
    # EMA (9, 12, 21, 50, 200)
    for period in [9, 12, 21, 50, 200]:
        col = f"ema_{period}"
        exists = test_column_exists(df, col)
        log_result("EMA", f"ema_{period} existe", exists)
    
    # WMA
    col = "wma_20"
    exists = test_column_exists(df, col)
    log_result("WMA", f"{col} existe", exists)
    
    # HMA
    col = "hma_9"
    exists = test_column_exists(df, col)
    log_result("HMA", f"{col} existe", exists)
    
    # TEMA
    col = "tema_9"
    exists = test_column_exists(df, col)
    log_result("TEMA", f"{col} existe", exists)
    
    # ADX (+DI, -DI)
    for col in ["adx_14", "dmp_14", "dmn_14"]:
        exists = test_column_exists(df, col)
        log_result("ADX", f"{col} existe", exists)
    if test_column_exists(df, "adx_14"):
        in_range = test_range(df, "adx_14", 0, 100)
        log_result("ADX", "adx_14 range [0-100]", in_range)
    
    # Ichimoku (5 linhas)
    for col in ["isa_9", "isb_26", "its_9", "iks_26", "ics_26"]:
        exists = test_column_exists(df, col)
        log_result("Ichimoku", f"{col} existe", exists)
    
    # Parabolic SAR
    for col in ["psarl_0.02_0.2", "psars_0.02_0.2"]:
        exists = test_column_exists(df, col)
        log_result("PSAR", f"{col} existe", exists)
    
    # Supertrend
    for col in ["supert_10_3.0", "supertd_10_3.0"]:
        exists = test_column_exists(df, col)
        log_result("Supertrend", f"{col} existe", exists)
    
    # Aroon
    for col in ["aroond_25", "aroonu_25", "aroonosc_25"]:
        exists = test_column_exists(df, col)
        log_result("Aroon", f"{col} existe", exists)
    
    # STC
    col = "stc_10_12_26_0.5"
    exists = test_column_exists(df, col)
    log_result("STC", f"{col} existe", exists)
    
    # KAMA
    col = "kama_10"
    exists = test_column_exists(df, col)
    log_result("KAMA", f"{col} existe", exists)
    
    # 2.1.3 VOLATILIDADE (7)
    print("\n" + "=" * 70)
    print("2.1.3 VOLATILIDADE")
    print("=" * 70)
    
    # ATR
    col = "atr_14"
    exists = test_column_exists(df, col)
    log_result("ATR", f"{col} existe", exists)
    if exists:
        positive = (df[col].dropna() >= 0).all()
        log_result("ATR", f"{col} valores >= 0", positive)
    
    # Bollinger Bands (upper, mid, lower, %B, bandwidth)
    for col in ["bbl_20_2.0", "bbm_20_2.0", "bbu_20_2.0", "bbb_20_2.0", "bbp_20_2.0"]:
        exists = test_column_exists(df, col)
        log_result("Bollinger", f"{col} existe", exists)
    
    # Keltner Channels
    for col in ["kcle_20_2", "kcbe_20_2", "kcue_20_2"]:
        exists = test_column_exists(df, col)
        log_result("Keltner", f"{col} existe", exists)
    
    # Donchian Channels
    for col in ["dcl_20_20", "dcm_20_20", "dcu_20_20"]:
        exists = test_column_exists(df, col)
        log_result("Donchian", f"{col} existe", exists)
    
    # NATR
    col = "natr_14"
    exists = test_column_exists(df, col)
    log_result("NATR", f"{col} existe", exists)
    
    # True Range
    col = "true_range"
    exists = test_column_exists(df, col)
    log_result("True Range", f"{col} existe", exists)
    
    # Standard Deviation
    col = "stdev_20"
    exists = test_column_exists(df, col)
    log_result("StdDev", f"{col} existe", exists)
    
    # 2.1.4 VOLUME (9)
    print("\n" + "=" * 70)
    print("2.1.4 VOLUME")
    print("=" * 70)
    
    # OBV
    col = "obv"
    exists = test_column_exists(df, col)
    log_result("OBV", f"{col} existe", exists)
    
    # VWAP
    col = "vwap"
    exists = test_column_exists(df, col)
    log_result("VWAP", f"{col} existe", exists)
    if exists:
        no_nan = test_no_all_nan(df, col)
        log_result("VWAP", f"{col} tem valores", no_nan)
    
    # CMF
    col = "cmf_20"
    exists = test_column_exists(df, col)
    log_result("CMF", f"{col} existe", exists)
    if exists:
        in_range = test_range(df, col, -1, 1)
        log_result("CMF", f"{col} range [-1,1]", in_range)
    
    # ADL
    col = "adl"
    exists = test_column_exists(df, col)
    log_result("ADL", f"{col} existe", exists)
    
    # Chaikin Oscillator
    col = "adosc"
    exists = test_column_exists(df, col)
    log_result("Chaikin Osc", f"{col} existe", exists)
    
    # Force Index
    col = "efi_13"
    exists = test_column_exists(df, col)
    log_result("Force Index", f"{col} existe", exists)
    
    # NVI/PVI
    for col in ["nvi", "pvi"]:
        exists = test_column_exists(df, col)
        log_result("NVI/PVI", f"{col} existe", exists)
    
    # PVT
    col = "pvt"
    exists = test_column_exists(df, col)
    log_result("PVT", f"{col} existe", exists)
    
    # Klinger
    col = "kvo_34_55_13"
    exists = test_column_exists(df, col)
    log_result("Klinger", f"{col} existe", exists)
    
    # 2.1.5 SUPORTE/RESISTENCIA (4)
    print("\n" + "=" * 70)
    print("2.1.5 SUPORTE/RESISTENCIA")
    print("=" * 70)
    
    # Elder Ray
    for col in ["bullp_13", "bearp_13"]:
        exists = test_column_exists(df, col)
        log_result("Elder Ray", f"{col} existe", exists)
    
    # VWMA
    col = "vwma_20"
    exists = test_column_exists(df, col)
    log_result("VWMA", f"{col} existe", exists)
    
    # DPO
    col = "dpo_20"
    exists = test_column_exists(df, col)
    log_result("DPO", f"{col} existe", exists)
    
    # Vortex
    for col in ["vtxp_14", "vtxm_14"]:
        exists = test_column_exists(df, col)
        log_result("Vortex", f"{col} existe", exists)
    
    # 2.2 CUSTOM (5)
    print("\n" + "=" * 70)
    print("2.2 CUSTOM INDICATORS")
    print("=" * 70)
    
    # WaveTrend
    for col in ["wt1", "wt2", "wt_cross"]:
        exists = test_column_exists(df, col)
        log_result("WaveTrend", f"{col} existe", exists)
    
    # Fibonacci Retracement (niveis: 23.6%, 38.2%, 50%, 61.8%, 78.6%)
    for level in ["236", "382", "500", "618", "786"]:
        col = f"fib_{level}"
        exists = test_column_exists(df, col)
        log_result("Fib Retrace", f"{col} existe", exists)
    
    # Fibonacci Extension (niveis: 127.2%, 161.8%, 200%, 261.8%)
    for level in ["1272", "1618", "2000", "2618"]:
        col = f"fib_ext_{level}"
        exists = test_column_exists(df, col)
        log_result("Fib Extension", f"{col} existe", exists)
    
    # ZigZag
    for col in ["zigzag_pivot", "zigzag_value"]:
        exists = test_column_exists(df, col)
        log_result("ZigZag", f"{col} existe", exists)
    if test_column_exists(df, "zigzag_pivot"):
        valid_vals = df["zigzag_pivot"].dropna().unique()
        valid = set(valid_vals).issubset({-1, 0, 1})
        log_result("ZigZag", "zigzag_pivot valores {-1,0,1}", valid)
    
    # Pivot Points (PP, R1, R2, R3, S1, S2, S3)
    for col in ["pivot_pp", "pivot_r1", "pivot_r2", "pivot_r3", "pivot_s1", "pivot_s2", "pivot_s3"]:
        exists = test_column_exists(df, col)
        log_result("Pivot Points", f"{col} existe", exists)
    
    # Verificar formula do Pivot Point: PP = (H + L + C) / 3
    if all(c in df.columns for c in ["pivot_pp", "high", "low", "close"]):
        expected_pp = (df['high'] + df['low'] + df['close']) / 3
        formula_ok = test_formula(df, "pivot_pp", expected_pp)
        log_result("Pivot Points", "PP formula (H+L+C)/3", formula_ok)
    
    # 2.3 DERIVADOS (3)
    print("\n" + "=" * 70)
    print("2.3 INDICADORES DERIVADOS")
    print("=" * 70)
    
    # RSI Divergence Detector
    for col in ["rsi_bull_div", "rsi_bear_div"]:
        exists = test_column_exists(df, col)
        log_result("RSI Divergence", f"{col} existe", exists)
    
    # Monday Range (monday_high, monday_low, sweep_direction)
    for col in ["monday_high", "monday_low", "monday_sweep"]:
        exists = test_column_exists(df, col)
        log_result("Monday Range", f"{col} existe", exists)
    
    # OBOS Multi-Timeframe Scanner
    for col in ["is_oversold_14", "is_overbought_14"]:
        exists = test_column_exists(df, col)
        log_result("OBOS Scanner", f"{col} existe", exists)
    
    # Verificar logica OBOS: oversold = RSI < 30
    if all(c in df.columns for c in ["is_oversold_14", "rsi_14"]):
        expected = (df['rsi_14'] < 30).astype(int)
        formula_ok = (df['is_oversold_14'] == expected).all()
        log_result("OBOS Scanner", "is_oversold_14 = RSI<30", formula_ok)
    
    # RESUMO FINAL
    print("\n" + "=" * 70)
    print("RESUMO FINAL")
    print("=" * 70)
    print(f"  PASSED:   {results['PASSED']}")
    print(f"  FAILED:   {results['FAILED']}")
    print(f"  WARNINGS: {results['WARNINGS']}")
    print("=" * 70)
    
    if results['FAILED'] == 0:
        print("\n[SUCCESS] TODOS OS TESTES PASSARAM!")
    else:
        print(f"\n[WARNING] {results['FAILED']} testes falharam!")
    
    return results

if __name__ == "__main__":
    run_tests()
