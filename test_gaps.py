"""
Verificador de Gaps nos dados de klines
Analisa todos os símbolos baixados e lista gaps encontrados
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("data/perps")

def detect_gaps(df: pd.DataFrame, symbol: str):
    """Detecta gaps nos dados de 1m"""
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
            gap_hours = diff_minutes / 60
            gaps.append({
                'symbol': symbol,
                'gap_start': df.loc[i, 'end'],
                'gap_end': df.loc[i+1, 'start'],
                'missing_minutes': int(diff_minutes),
                'missing_hours': round(gap_hours, 1)
            })
    
    return gaps


def main():
    print("=" * 80)
    print("VERIFICADOR DE GAPS")
    print("=" * 80)
    
    # Encontrar todos os simbolos
    symbol_dirs = [d for d in DATA_DIR.iterdir() if d.is_dir()]
    print(f"\nEncontrados {len(symbol_dirs)} simbolos\n")
    
    all_gaps = []
    symbols_with_gaps = 0
    symbols_ok = 0
    
    for symbol_dir in sorted(symbol_dirs):
        symbol = symbol_dir.name
        parquet_1m = symbol_dir / "1m.parquet"
        
        if not parquet_1m.exists():
            print(f"[SKIP] {symbol}: 1m.parquet nao encontrado")
            continue
        
        df = pd.read_parquet(parquet_1m)
        gaps = detect_gaps(df, symbol)
        
        if gaps:
            symbols_with_gaps += 1
            all_gaps.extend(gaps)
            
            # Calcular total de minutos faltando
            total_missing = sum(g['missing_minutes'] for g in gaps)
            total_hours = total_missing / 60
            
            print(f"[GAP] {symbol}: {len(gaps)} gaps | Total: {total_hours:.1f}h ({total_missing} min) faltando")
            
            # Mostrar maiores gaps
            big_gaps = [g for g in gaps if g['missing_hours'] >= 1]
            if big_gaps:
                for g in sorted(big_gaps, key=lambda x: -x['missing_minutes'])[:3]:
                    print(f"       {g['gap_start']} -> {g['gap_end']} ({g['missing_hours']}h)")
        else:
            symbols_ok += 1
            print(f"[OK] {symbol}: {len(df)} klines, sem gaps")
    
    # Resumo
    print("\n" + "=" * 80)
    print("RESUMO")
    print("=" * 80)
    print(f"Simbolos OK (sem gaps): {symbols_ok}")
    print(f"Simbolos com gaps: {symbols_with_gaps}")
    print(f"Total de gaps: {len(all_gaps)}")
    
    if all_gaps:
        total_missing = sum(g['missing_minutes'] for g in all_gaps)
        print(f"Total de minutos faltando: {total_missing:,} ({total_missing/60:.1f}h)")
        
        # Top 10 maiores gaps
        print("\nTop 10 maiores gaps:")
        for g in sorted(all_gaps, key=lambda x: -x['missing_minutes'])[:10]:
            print(f"  {g['symbol']}: {g['gap_start']} -> {g['gap_end']} ({g['missing_hours']}h)")


if __name__ == "__main__":
    main()
