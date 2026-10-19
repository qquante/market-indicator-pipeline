import requests
import json
import os
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import time

BASE_URL = "https://api.backpack.exchange/api/v1"

# Configuração
SYMBOL = "BTC_USDC_PERP"
INTERVALS = ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"]
DATA_DIR = Path("data/perps")
CHECKPOINT_FILE = Path("data/checkpoint.json")

# Limites de tempo por intervalo (em horas) - descoberto nos testes
TIME_LIMITS = {
    "1m": 24,       # 24 horas max
    "3m": 72,       # 3 dias
    "5m": 120,      # 5 dias
    "15m": 168,     # 7 dias
    "30m": 336,     # 14 dias
    "1h": 720,      # 30 dias
    "4h": 2160,     # 90 dias
    "1d": 8760,     # 365 dias
}

def get_klines(symbol: str, interval: str, start_time: int, end_time: int):
    """Pega klines de um símbolo"""
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": start_time,
        "endTime": end_time
    }
    response = requests.get(f"{BASE_URL}/klines", params=params)
    return response.json()

def load_checkpoint():
    """Carrega checkpoint existente ou cria novo"""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, 'r') as f:
            return json.load(f)
    return {"last_update": None, "symbols": {}}

def save_checkpoint(checkpoint):
    """Salva checkpoint"""
    checkpoint["last_update"] = datetime.now().isoformat()
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=2)

def download_klines_for_interval(symbol: str, interval: str, checkpoint: dict):
    """Baixa todas as klines de um intervalo específico"""
    
    symbol_dir = DATA_DIR / symbol
    symbol_dir.mkdir(parents=True, exist_ok=True)
    parquet_file = symbol_dir / f"{interval}.parquet"
    
    # Inicializar checkpoint do símbolo se não existir
    if symbol not in checkpoint["symbols"]:
        checkpoint["symbols"][symbol] = {}
    if interval not in checkpoint["symbols"][symbol]:
        checkpoint["symbols"][symbol][interval] = {
            "last_timestamp": None,
            "total_rows": 0,
            "status": "pending"
        }
    
    symbol_checkpoint = checkpoint["symbols"][symbol][interval]
    
    # Determinar ponto de início
    now = datetime.now()
    end_ts = int(now.timestamp())
    
    if symbol_checkpoint["last_timestamp"]:
        # Continuar de onde parou
        start_dt = datetime.strptime(symbol_checkpoint["last_timestamp"], "%Y-%m-%d %H:%M:%S")
        start_ts = int(start_dt.timestamp())
        print(f"  Continuando de {symbol_checkpoint['last_timestamp']}")
    else:
        # Começar do início (janeiro 2025 para perps)
        start_dt = datetime(2025, 1, 1)
        start_ts = int(start_dt.timestamp())
        print(f"  Começando do início (2025-01-01)")
    
    # Carregar dados existentes se houver
    all_klines = []
    if parquet_file.exists():
        existing_df = pd.read_parquet(parquet_file)
        all_klines = existing_df.to_dict('records')
        print(f"  Carregados {len(all_klines)} klines existentes")
    
    # Baixar em chunks
    chunk_hours = TIME_LIMITS[interval]
    chunk_seconds = chunk_hours * 3600
    
    current_start = start_ts
    new_klines = 0
    
    while current_start < end_ts:
        current_end = min(current_start + chunk_seconds, end_ts)
        
        # Rate limiting
        time.sleep(0.1)
        
        result = get_klines(symbol, interval, current_start, current_end)
        
        if isinstance(result, list) and len(result) > 0:
            all_klines.extend(result)
            new_klines += len(result)
            last_kline = result[-1]
            
            # Atualizar para proximo chunk
            last_end_dt = datetime.strptime(last_kline['end'], "%Y-%m-%d %H:%M:%S")
            current_start = int(last_end_dt.timestamp())
            
            # === SALVAR A CADA CHUNK ===
            df = pd.DataFrame(all_klines)
            df = df.drop_duplicates(subset=['start'], keep='last')
            df = df.sort_values('start').reset_index(drop=True)
            
            # Converter colunas numericas
            numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'quoteVolume', 'trades']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Salvar parquet
            df.to_parquet(parquet_file, index=False)
            
            # Atualizar checkpoint
            symbol_checkpoint["last_timestamp"] = last_kline['end']
            symbol_checkpoint["total_rows"] = len(df)
            symbol_checkpoint["status"] = "in_progress"
            save_checkpoint(checkpoint)
            
            print(f"    + {len(result)} klines | Total: {len(df)} | Ate: {last_kline['end']} [SALVO]")
            
        elif isinstance(result, dict) and 'message' in result:
            print(f"    [ERRO] {result['message']}")
            break
        else:
            # Sem mais dados, avancar para proximo chunk
            current_start = current_end
    
    # Marcar como completo
    if all_klines:
        symbol_checkpoint["status"] = "complete"
        save_checkpoint(checkpoint)
        print(f"  [OK] Completo: {symbol_checkpoint['total_rows']} klines")
        return pd.read_parquet(parquet_file)
    else:
        symbol_checkpoint["status"] = "empty"
        save_checkpoint(checkpoint)
        print(f"  [AVISO] Sem dados")
        return None

def main():
    print("=" * 60)
    print(f"TESTE: Baixando klines de {SYMBOL}")
    print("=" * 60)
    
    # Criar diretório
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Carregar checkpoint
    checkpoint = load_checkpoint()
    
    # Baixar cada intervalo
    for interval in INTERVALS:
        print(f"\n[INTERVAL] {interval}:")
        download_klines_for_interval(SYMBOL, interval, checkpoint)
        save_checkpoint(checkpoint)
    
    # Resumo final
    print("\n" + "=" * 60)
    print("RESUMO FINAL")
    print("=" * 60)
    
    if SYMBOL in checkpoint["symbols"]:
        for interval, data in checkpoint["symbols"][SYMBOL].items():
            print(f"  {interval}: {data['total_rows']} klines | Status: {data['status']}")
    
    print(f"\n[OK] Checkpoint salvo em: {CHECKPOINT_FILE}")
    print(f"[DIR] Dados salvos em: {DATA_DIR / SYMBOL}")

if __name__ == "__main__":
    main()
