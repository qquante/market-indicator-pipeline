"""
Preenche gaps nos dados de klines
- Detecta gaps em cada símbolo
- Baixa apenas os períodos faltantes
- Mescla com dados existentes
- Regenera todos os timeframes
"""

import requests
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import time
from typing import List, Tuple, Dict, Optional

BASE_URL = "https://api.backpack.exchange/api/v1"
DATA_DIR = Path("data/perps")
TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"]
MINUTES_PER_TF = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440}


def get_klines_with_retry(symbol: str, start_time: int, end_time: int, max_retries: int = 5) -> Optional[List[Dict]]:
    """Pega klines com retry"""
    params = {"symbol": symbol, "interval": "1m", "startTime": start_time, "endTime": end_time}
    
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{BASE_URL}/klines", params=params, timeout=60)
            data = response.json()
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'message' in data:
                return None
            return data
        except:
            wait_time = min((2 ** attempt) + 1, 30)
            print(f"      [RETRY {attempt+1}/{max_retries}] Aguardando {wait_time}s...")
            time.sleep(wait_time)
    return None


def detect_gaps(df: pd.DataFrame) -> List[Tuple[str, str]]:
    """Detecta gaps nos dados de 1m"""
    if len(df) < 2:
        return []
    
    gaps = []
    df = df.sort_values('start').reset_index(drop=True)
    
    for i in range(len(df) - 1):
        current_end = datetime.strptime(df.loc[i, 'end'], "%Y-%m-%d %H:%M:%S")
        next_start = datetime.strptime(df.loc[i+1, 'start'], "%Y-%m-%d %H:%M:%S")
        
        diff_minutes = (next_start - current_end).total_seconds() / 60
        if diff_minutes > 1:
            gaps.append((df.loc[i, 'end'], df.loc[i+1, 'start']))
    
    return gaps


def aggregate_klines(df_1m: pd.DataFrame, target_tf: str) -> pd.DataFrame:
    """Agrega klines de 1m para timeframe maior"""
    if target_tf == "1m":
        return df_1m.copy()
    
    minutes = MINUTES_PER_TF[target_tf]
    df = df_1m.copy()
    df['start_dt'] = pd.to_datetime(df['start'])
    df['group'] = (df['start_dt'].astype('int64') // 10**9 // 60 // minutes).astype(int)
    
    agg_df = df.groupby('group').agg({
        'start': 'first', 'end': 'last', 'open': 'first', 'high': 'max',
        'low': 'min', 'close': 'last', 'volume': 'sum', 'quoteVolume': 'sum', 'trades': 'sum'
    }).reset_index(drop=True)
    
    return agg_df


def fill_gaps_for_symbol(symbol: str) -> int:
    """Preenche gaps de um símbolo. Retorna quantidade de klines adicionadas."""
    symbol_dir = DATA_DIR / symbol
    parquet_1m = symbol_dir / "1m.parquet"
    
    if not parquet_1m.exists():
        print(f"  [SKIP] 1m.parquet nao existe")
        return 0
    
    # Carregar dados
    df = pd.read_parquet(parquet_1m)
    original_count = len(df)
    
    # Detectar gaps
    gaps = detect_gaps(df)
    if not gaps:
        print(f"  [OK] Sem gaps")
        return 0
    
    print(f"  Encontrados {len(gaps)} gaps")
    
    # Baixar dados faltantes
    all_klines = df.to_dict('records')
    added = 0
    
    for gap_start, gap_end in gaps:
        start_ts = int(datetime.strptime(gap_start, "%Y-%m-%d %H:%M:%S").timestamp())
        end_ts = int(datetime.strptime(gap_end, "%Y-%m-%d %H:%M:%S").timestamp())
        
        time.sleep(0.2)  # Rate limiting
        
        result = get_klines_with_retry(symbol, start_ts, end_ts)
        
        if result and len(result) > 0:
            all_klines.extend(result)
            added += len(result)
            print(f"    Gap {gap_start[:10]} -> {gap_end[:10]}: +{len(result)}")
    
    if added == 0:
        print(f"  [AVISO] Nenhum dado novo obtido")
        return 0
    
    # Reconstruir DataFrame
    df_new = pd.DataFrame(all_klines)
    df_new = df_new.drop_duplicates(subset=['start'], keep='last')
    df_new = df_new.sort_values('start').reset_index(drop=True)
    
    # Converter colunas numericas
    for col in ['open', 'high', 'low', 'close', 'volume', 'quoteVolume', 'trades']:
        if col in df_new.columns:
            df_new[col] = pd.to_numeric(df_new[col], errors='coerce')
    
    # Salvar 1m
    df_new.to_parquet(parquet_1m, index=False)
    
    # Regenerar outros timeframes
    print(f"  Regenerando timeframes...")
    for tf in TIMEFRAMES:
        if tf == "1m":
            continue
        df_tf = aggregate_klines(df_new, tf)
        df_tf.to_parquet(symbol_dir / f"{tf}.parquet", index=False)
    
    print(f"  [OK] +{added} klines | Total: {len(df_new)}")
    return added


def main():
    print("=" * 70)
    print("PREENCHIMENTO DE GAPS")
    print("=" * 70)
    
    # Encontrar todos os simbolos
    symbol_dirs = [d for d in DATA_DIR.iterdir() if d.is_dir()]
    print(f"\nProcessando {len(symbol_dirs)} simbolos...\n")
    
    total_added = 0
    symbols_fixed = 0
    
    for i, symbol_dir in enumerate(sorted(symbol_dirs)):
        symbol = symbol_dir.name
        print(f"[{i+1}/{len(symbol_dirs)}] {symbol}")
        
        added = fill_gaps_for_symbol(symbol)
        total_added += added
        if added > 0:
            symbols_fixed += 1
    
    # Resumo
    print("\n" + "=" * 70)
    print("RESUMO")
    print("=" * 70)
    print(f"Simbolos processados: {len(symbol_dirs)}")
    print(f"Simbolos com gaps preenchidos: {symbols_fixed}")
    print(f"Total de klines adicionadas: {total_added:,}")


if __name__ == "__main__":
    main()
