"""
Verificador de Indicadores - Confere 1 por 1 se todos foram calculados
"""
import pandas as pd
from pathlib import Path

# Lista de indicadores que DEVEMOS ter (todos em lowercase)
EXPECTED_INDICATORS = {
    # OHLCV Base
    "OHLCV": ["start", "end", "open", "high", "low", "close", "volume"],
    
    # Momentum
    "RSI": ["rsi_9", "rsi_14", "rsi_21"],
    "MACD": ["macd_12_26_9", "macdh_12_26_9", "macds_12_26_9"],
    "Stochastic": ["stochk_14_3_3", "stochd_14_3_3"],
    "StochRSI": ["stochrsik_14_14_3_3", "stochrsid_14_14_3_3"],
    "Williams %R": ["willr"],
    "CCI": ["cci"],
    "MFI": ["mfi"],
    "ROC": ["roc"],
    "Momentum": ["mom"],
    "TSI": ["tsi_13_25_13", "tsis_13_25_13"],
    "Ultimate Oscillator": ["uo"],
    "Awesome Oscillator": ["ao"],
    "PPO": ["ppo_12_26_9", "ppoh_12_26_9", "ppos_12_26_9"],
    "CMO": ["cmo"],
    "Fisher Transform": ["fishert_9_1", "fisherts_9_1"],
    
    # Trend - Moving Averages
    "SMA": ["sma_10", "sma_20", "sma_50", "sma_100", "sma_200"],
    "EMA": ["ema_9", "ema_12", "ema_21", "ema_50", "ema_200"],
    "WMA": ["wma_20"],
    "HMA": ["hma_9"],
    "TEMA": ["tema_9"],
    "KAMA": ["kama_10"],
    
    # Trend - Other
    "ADX": ["adx_14", "dmp_14", "dmn_14"],
    "Ichimoku": ["isa_9", "isb_26", "its_9", "iks_26", "ics_26"],
    "Parabolic SAR": ["psarl_0.02_0.2", "psars_0.02_0.2"],
    "Supertrend": ["supert_10_3.0", "supertd_10_3.0", "supertl_10_3.0", "superts_10_3.0"],
    "Aroon": ["aroond_25", "aroonu_25", "aroonosc_25"],
    "STC": ["stc_10_12_26_0.5"],
    "Vortex": ["vtxp_14", "vtxm_14"],
    
    # Volatility
    "ATR": ["atr_14", "natr", "true_range"],
    "Bollinger Bands": ["bbl_20_2.0", "bbm_20_2.0", "bbu_20_2.0", "bbb_20_2.0", "bbp_20_2.0"],
    "Keltner Channels": ["kcle_20_2", "kcbe_20_2", "kcue_20_2"],
    "Donchian Channels": ["dcl_20_20", "dcm_20_20", "dcu_20_20"],
    "Std Deviation": ["stdev"],
    
    # Volume
    "OBV": ["obv"],
    "CMF": ["cmf"],
    "ADL": ["adl"],
    "Chaikin Oscillator": ["adosc"],
    "Force Index": ["efi"],
    "NVI": ["nvi"],
    "PVI": ["pvi"],
    "PVT": ["pvt"],
    
    # Custom Indicators
    "WaveTrend": ["wt1", "wt2", "wt_cross"],
    "Pivot Points": ["pivot_pp", "pivot_r1", "pivot_r2", "pivot_r3", "pivot_s1", "pivot_s2", "pivot_s3"],
    "RSI Divergence": ["rsi_bull_div", "rsi_bear_div"],
    "Monday Range": ["monday_high", "monday_low"],
    
    # Derived Signals
    "OBOS Flags": ["is_oversold", "is_overbought"],
    "EMA Cross": ["ema_cross_9_21"],
}


def verify_indicators(parquet_path: str):
    """Verifica se todos indicadores esperados estao presentes"""
    
    print(f"\n{'='*70}")
    print(f"VERIFICANDO: {parquet_path}")
    print(f"{'='*70}\n")
    
    df = pd.read_parquet(parquet_path)
    columns = set(df.columns)
    
    total_expected = 0
    total_found = 0
    total_missing = 0
    missing_list = []
    
    for category, indicators in EXPECTED_INDICATORS.items():
        found = []
        missing = []
        
        for ind in indicators:
            total_expected += 1
            if ind in columns:
                found.append(ind)
                total_found += 1
            else:
                missing.append(ind)
                total_missing += 1
                missing_list.append((category, ind))
        
        # Status
        if len(missing) == 0:
            status = "[OK]"
        else:
            status = "[MISSING]"
        
        print(f"{status:10} {category:25} {len(found)}/{len(indicators)}")
        
        if missing:
            for m in missing:
                print(f"           -> FALTA: {m}")
    
    print(f"\n{'='*70}")
    print(f"RESUMO:")
    print(f"  Total esperado:   {total_expected}")
    print(f"  Total encontrado: {total_found}")
    print(f"  Total faltando:   {total_missing}")
    print(f"  Colunas no DF:    {len(df.columns)}")
    print(f"{'='*70}")
    
    if total_missing == 0:
        print("\n[SUCCESS] TODOS OS INDICADORES FORAM CALCULADOS CORRETAMENTE!")
    else:
        print(f"\n[WARNING] Faltam {total_missing} indicadores!")
        print("\nLista de faltantes:")
        for cat, ind in missing_list:
            print(f"  - {cat}: {ind}")
    
    # Verificar valores NaN
    print("\n" + "="*70)
    print("VERIFICACAO DE VALORES NaN (ultimas 100 rows):")
    print("="*70)
    
    sample = df.tail(100)
    nan_counts = sample.isna().sum()
    nan_cols = nan_counts[nan_counts > 0]
    
    if len(nan_cols) > 0:
        print(f"\nColunas com NaN nos ultimos 100 candles:")
        for col, count in nan_cols.items():
            print(f"  {col}: {count} NaN")
    else:
        print("\n[OK] Nenhum NaN nos ultimos 100 candles!")
    
    # Verificar ranges de valores (sanity check)
    print("\n" + "="*70)
    print("VERIFICACAO DE RANGES (sanity check):")
    print("="*70)
    
    checks = [
        ("rsi_14", 0, 100, "RSI deve estar entre 0-100"),
        ("ADX_14", 0, 100, "ADX deve estar entre 0-100"),
        ("mfi", 0, 100, "MFI deve estar entre 0-100"),
        ("willr", -100, 0, "Williams %R deve estar entre -100 e 0"),
    ]
    
    for col, min_val, max_val, desc in checks:
        if col in df.columns:
            actual_min = df[col].min()
            actual_max = df[col].max()
            if actual_min >= min_val and actual_max <= max_val:
                print(f"  [OK] {col}: min={actual_min:.2f}, max={actual_max:.2f}")
            else:
                print(f"  [WARN] {col}: min={actual_min:.2f}, max={actual_max:.2f} - {desc}")
    
    return total_missing == 0


if __name__ == "__main__":
    # Verificar BTC 1h como exemplo
    result = verify_indicators("data/perps/BTC_USDC_PERP/1h.parquet")
    
    print("\n\n")
    
    # Verificar 1d tambem (menos candles, mais chance de NaN)
    result2 = verify_indicators("data/perps/BTC_USDC_PERP/1d.parquet")
