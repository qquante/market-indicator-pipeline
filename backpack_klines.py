"""
Backpack Exchange Klines Downloader v2
- Baixa apenas M1 e agrega localmente
- Retry com exponential backoff
- Checkpoint para retomar
- Deteccao e preenchimento de gaps
- Prioriza simbolos in_progress
"""

import requests
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import time
from typing import Optional, List, Dict, Tuple

BASE_URL = "https://api.backpack.exchange/api/v1"
DATA_DIR = Path("data/perps")
CHECKPOINT_FILE = Path("data/checkpoint.json")

TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"]
MINUTES_PER_TF = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440}


def get_perp_symbols() -> List[str]:
    """Pega todos os simbolos PERP"""
    response = requests.get(f"{BASE_URL}/markets", timeout=30)
    markets = response.json()
    return [m['symbol'] for m in markets if m['marketType'] == 'PERP']


def get_klines_with_retry(symbol: str, interval: str, start_time: int, end_time: int, 
                          max_retries: int = 10) -> Optional[List[Dict]]:
    """Pega klines com retry e exponential backoff"""
    params = {"symbol": symbol, "interval": interval, "startTime": start_time, "endTime": end_time}
    
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{BASE_URL}/klines", params=params, timeout=60)
            data = response.json()
            
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'message' in data:
                print(f"    [API ERROR] {data['message']}")
                return None
            return data
                
        except requests.exceptions.RequestException as e:
            wait_time = min((2 ** attempt) + 1, 60)  # max 60s
            print(f"    [RETRY {attempt+1}/{max_retries}] Aguardando {wait_time}s...")
            time.sleep(wait_time)
    
    print(f"    [FALHA TOTAL] Nao foi possivel conectar apos {max_retries} tentativas")
    return None


def load_checkpoint() -> Dict:
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, 'r') as f:
            return json.load(f)
    return {"last_update": None, "symbols": {}}


def save_checkpoint(checkpoint: Dict):
    checkpoint["last_update"] = datetime.now().isoformat()
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=2)


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


def detect_gaps(df: pd.DataFrame) -> List[Tuple[str, str]]:
    """
    Detecta gaps nos dados de 1m.
    Retorna lista de (gap_start, gap_end) para preencher.
    """
    if len(df) < 2:
        return []
    
    gaps = []
    df = df.sort_values('start').reset_index(drop=True)
    
    for i in range(len(df) - 1):
        current_end = datetime.strptime(df.loc[i, 'end'], "%Y-%m-%d %H:%M:%S")
        next_start = datetime.strptime(df.loc[i+1, 'start'], "%Y-%m-%d %H:%M:%S")
        
        # Se diferenca > 1 minuto, temos gap
        diff_minutes = (next_start - current_end).total_seconds() / 60
        if diff_minutes > 1:
            gaps.append((df.loc[i, 'end'], df.loc[i+1, 'start']))
    
    return gaps


def fill_gaps(symbol: str, gaps: List[Tuple[str, str]], existing_df: pd.DataFrame) -> pd.DataFrame:
    """Preenche gaps baixando os dados faltantes"""
    if not gaps:
        return existing_df
    
    print(f"  Preenchendo {len(gaps)} gaps...")
    all_klines = existing_df.to_dict('records')
    
    for gap_start, gap_end in gaps:
        start_ts = int(datetime.strptime(gap_start, "%Y-%m-%d %H:%M:%S").timestamp())
        end_ts = int(datetime.strptime(gap_end, "%Y-%m-%d %H:%M:%S").timestamp())
        
        time.sleep(0.3)
        result = get_klines_with_retry(symbol, "1m", start_ts, end_ts)
        
        if result and len(result) > 0:
            all_klines.extend(result)
            print(f"    Gap {gap_start} -> {gap_end}: +{len(result)} klines")
    
    # Remover duplicatas e ordenar
    df = pd.DataFrame(all_klines)
    df = df.drop_duplicates(subset=['start'], keep='last')
    df = df.sort_values('start').reset_index(drop=True)
    
    for col in ['open', 'high', 'low', 'close', 'volume', 'quoteVolume', 'trades']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df


def download_1m_klines(symbol: str, checkpoint: Dict, force_continue: bool = True) -> Optional[pd.DataFrame]:
    """Baixa todas as klines de 1m de um simbolo"""
    symbol_dir = DATA_DIR / symbol
    symbol_dir.mkdir(parents=True, exist_ok=True)
    parquet_file = symbol_dir / "1m.parquet"
    
    # Inicializar checkpoint
    if symbol not in checkpoint["symbols"]:
        checkpoint["symbols"][symbol] = {"last_timestamp": None, "total_rows": 0, "status": "pending"}
    
    sym_ckpt = checkpoint["symbols"][symbol]
    
    now = datetime.now()
    end_ts = int(now.timestamp())
    
    # Determinar inicio
    if sym_ckpt.get("last_timestamp"):
        start_dt = datetime.strptime(sym_ckpt["last_timestamp"], "%Y-%m-%d %H:%M:%S")
        start_ts = int(start_dt.timestamp())
        print(f"  Continuando de {sym_ckpt['last_timestamp']}")
    else:
        start_dt = datetime(2025, 1, 1)
        start_ts = int(start_dt.timestamp())
        print(f"  Iniciando do zero (2025-01-01)")
    
    # Carregar dados existentes
    all_klines = []
    if parquet_file.exists():
        existing_df = pd.read_parquet(parquet_file)
        all_klines = existing_df.to_dict('records')
        print(f"  Carregados {len(all_klines)} klines existentes")
    
    # Baixar em chunks de 24h
    chunk_seconds = 24 * 3600
    current_start = start_ts
    consecutive_failures = 0
    max_consecutive_failures = 3
    
    while current_start < end_ts:
        current_end = min(current_start + chunk_seconds, end_ts)
        
        time.sleep(0.25)  # Rate limiting
        
        result = get_klines_with_retry(symbol, "1m", current_start, current_end)
        
        if result is None:
            consecutive_failures += 1
            if consecutive_failures >= max_consecutive_failures:
                print(f"  [PAUSA] {max_consecutive_failures} falhas consecutivas. Salvando e pausando...")
                break
            # Tentar novamente o mesmo chunk
            time.sleep(5)
            continue
        
        consecutive_failures = 0  # Reset
        
        if len(result) > 0:
            all_klines.extend(result)
            last_kline = result[-1]
            
            last_end_dt = datetime.strptime(last_kline['end'], "%Y-%m-%d %H:%M:%S")
            current_start = int(last_end_dt.timestamp())
            
            # Salvar a cada chunk
            df = pd.DataFrame(all_klines)
            df = df.drop_duplicates(subset=['start'], keep='last')
            df = df.sort_values('start').reset_index(drop=True)
            
            for col in ['open', 'high', 'low', 'close', 'volume', 'quoteVolume', 'trades']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df.to_parquet(parquet_file, index=False)
            
            sym_ckpt["last_timestamp"] = last_kline['end']
            sym_ckpt["total_rows"] = len(df)
            sym_ckpt["status"] = "in_progress"
            save_checkpoint(checkpoint)
            
            print(f"    + {len(result)} | Total: {len(df)} | Ate: {last_kline['end']} [SALVO]")
        else:
            current_start = current_end
    
    # Verificar se chegou ao fim
    if all_klines:
        last_ts = datetime.strptime(sym_ckpt["last_timestamp"], "%Y-%m-%d %H:%M:%S")
        if (now - last_ts).total_seconds() < 3600:  # Menos de 1h atras = completo
            sym_ckpt["status"] = "complete"
        save_checkpoint(checkpoint)
        return pd.read_parquet(parquet_file)
    
    return None


def generate_all_timeframes(symbol: str):
    """Gera todos os timeframes a partir do 1m"""
    symbol_dir = DATA_DIR / symbol
    parquet_1m = symbol_dir / "1m.parquet"
    
    if not parquet_1m.exists():
        print(f"  [ERRO] 1m.parquet nao encontrado")
        return
    
    df_1m = pd.read_parquet(parquet_1m)
    print(f"  Gerando timeframes ({len(df_1m)} klines 1m)...")
    
    for tf in TIMEFRAMES:
        if tf == "1m":
            continue
        df_tf = aggregate_klines(df_1m, tf)
        df_tf.to_parquet(symbol_dir / f"{tf}.parquet", index=False)
        print(f"    {tf}: {len(df_tf)} klines")


def verify_and_fill_gaps(symbol: str, checkpoint: Dict):
    """Verifica e preenche gaps em um simbolo"""
    symbol_dir = DATA_DIR / symbol
    parquet_1m = symbol_dir / "1m.parquet"
    
    if not parquet_1m.exists():
        return
    
    df = pd.read_parquet(parquet_1m)
    gaps = detect_gaps(df)
    
    if gaps:
        print(f"  Encontrados {len(gaps)} gaps!")
        df = fill_gaps(symbol, gaps, df)
        df.to_parquet(parquet_1m, index=False)
        
        # Atualizar checkpoint
        checkpoint["symbols"][symbol]["total_rows"] = len(df)
        save_checkpoint(checkpoint)
        print(f"  Gaps preenchidos. Total: {len(df)} klines")
    else:
        print(f"  Sem gaps!")


def main():
    print("=" * 60)
    print("BACKPACK KLINES DOWNLOADER v2")
    print("=" * 60)
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    checkpoint = load_checkpoint()
    
    # Pegar todos os simbolos PERP
    print("\nBuscando simbolos PERP...")
    all_symbols = get_perp_symbols()
    print(f"Total: {len(all_symbols)} simbolos")
    
    # Separar por status
    in_progress = []
    pending = []
    complete = []
    
    for symbol in all_symbols:
        status = checkpoint.get("symbols", {}).get(symbol, {}).get("status", "pending")
        if status == "in_progress":
            in_progress.append(symbol)
        elif status == "complete":
            complete.append(symbol)
        else:
            pending.append(symbol)
    
    print(f"\nStatus:")
    print(f"  Completos: {len(complete)}")
    print(f"  Em progresso: {len(in_progress)}")
    print(f"  Pendentes: {len(pending)}")
    
    # Processar: primeiro in_progress, depois pending
    to_process = in_progress + pending
    
    for i, symbol in enumerate(to_process):
        print(f"\n[{i+1}/{len(to_process)}] {symbol}")
        
        # Baixar/continuar 1m
        df = download_1m_klines(symbol, checkpoint)
        
        if df is not None:
            # Gerar outros timeframes
            generate_all_timeframes(symbol)
            print(f"  [OK] Completo!")
    
    # Resumo
    print("\n" + "=" * 60)
    print("RESUMO FINAL")
    print("=" * 60)
    
    complete_count = sum(1 for s in checkpoint["symbols"].values() if s.get("status") == "complete")
    in_progress_count = sum(1 for s in checkpoint["symbols"].values() if s.get("status") == "in_progress")
    
    print(f"Completos: {complete_count}")
    print(f"Em progresso: {in_progress_count}")
    print(f"Total klines: {sum(s.get('total_rows', 0) for s in checkpoint['symbols'].values()):,}")


if __name__ == "__main__":
    main()
