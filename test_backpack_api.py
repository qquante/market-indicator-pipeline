import requests
import json
from datetime import datetime

BASE_URL = "https://api.backpack.exchange/api/v1"

def get_markets():
    """Pega todos os mercados disponíveis"""
    response = requests.get(f"{BASE_URL}/markets")
    return response.json()

def get_klines(symbol: str, interval: str, start_time: int, end_time: int = None):
    """Pega klines de um símbolo"""
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": start_time
    }
    if end_time:
        params["endTime"] = end_time
    
    response = requests.get(f"{BASE_URL}/klines", params=params)
    return response.json()

if __name__ == "__main__":
    # 1. Testar markets
    print("=" * 60)
    print("TESTANDO GET /markets")
    print("=" * 60)
    
    markets = get_markets()
    print(f"\nTotal de mercados: {len(markets)}")
    
    # Mostrar primeiros 5 mercados
    print("\nPrimeiros 5 mercados:")
    for m in markets[:5]:
        print(f"  - {m['symbol']} ({m['marketType']})")
    
    # Separar por tipo
    spot_markets = [m for m in markets if m['marketType'] == 'SPOT']
    perp_markets = [m for m in markets if m['marketType'] == 'PERP']
    
    print(f"\nMercados SPOT: {len(spot_markets)}")
    print(f"Mercados PERP: {len(perp_markets)}")
    
    # Listar todos os símbolos
    print("\nTodos os símbolos SPOT:")
    for m in spot_markets:
        print(f"  - {m['symbol']}")
    
    print("\nTodos os símbolos PERP:")
    for m in perp_markets:
        print(f"  - {m['symbol']}")
    
    # 2. Testar klines
    print("\n" + "=" * 60)
    print("TESTANDO GET /klines")
    print("=" * 60)
    
    # Pegar klines de BTC_USDC do início (timestamp 0) até agora
    test_symbol = "BTC_USDC"
    test_interval = "1d"
    
    # Timestamp de 1 de janeiro de 2023
    start_ts = int(datetime(2023, 1, 1).timestamp())
    end_ts = int(datetime.now().timestamp())
    
    print(f"\nTestando {test_symbol} - {test_interval}")
    print(f"Start: {datetime.fromtimestamp(start_ts)} ({start_ts})")
    print(f"End: {datetime.fromtimestamp(end_ts)} ({end_ts})")
    
    klines = get_klines(test_symbol, test_interval, start_ts, end_ts)
    
    if isinstance(klines, list):
        print(f"\nKlines retornados: {len(klines)}")
        
        if len(klines) > 0:
            print("\nPrimeira kline:")
            print(json.dumps(klines[0], indent=2))
            
            print("\nÚltima kline:")
            print(json.dumps(klines[-1], indent=2))
            
            # Verificar range de datas
            first_start = klines[0].get('start')
            last_end = klines[-1].get('end')
            print(f"\nRange: {first_start} -> {last_end}")
    else:
        print(f"Erro ou resposta inesperada: {klines}")
    
    # 3. Testar com timestamp 0 (desde o início da exchange)
    print("\n" + "=" * 60)
    print("TESTANDO DESDE O INÍCIO (timestamp 0)")
    print("=" * 60)
    
    klines_from_start = get_klines(test_symbol, test_interval, 0, end_ts)
    
    if isinstance(klines_from_start, list):
        print(f"Klines desde o início: {len(klines_from_start)}")
        if len(klines_from_start) > 0:
            print(f"Primeira kline disponível: {klines_from_start[0].get('start')}")
    else:
        print(f"Resposta: {klines_from_start}")
    
    # 4. Testar limite de klines por request
    print("\n" + "=" * 60)
    print("TESTANDO LIMITE POR REQUEST (1m interval)")
    print("=" * 60)
    
    klines_1m = get_klines(test_symbol, "1m", start_ts, end_ts)
    if isinstance(klines_1m, list):
        print(f"Klines 1m retornados: {len(klines_1m)}")
        print("(Se houver limite, precisamos fazer paginação)")
