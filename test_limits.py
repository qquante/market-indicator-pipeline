import requests
import json
from datetime import datetime, timedelta

BASE_URL = "https://api.backpack.exchange/api/v1"

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
    now = datetime.now()
    end_ts = int(now.timestamp())
    
    # Teste 1: Quanto tempo máximo podemos pedir por request?
    print("=" * 60)
    print("TESTE 1: Descobrir janela máxima de tempo")
    print("=" * 60)
    
    # Testar com 1d - vamos tentar diferentes ranges
    test_ranges_days = [30, 60, 90, 180, 365, 730, 1000]
    
    for days in test_ranges_days:
        start_ts = int((now - timedelta(days=days)).timestamp())
        result = get_klines("BTC_USDC", "1d", start_ts, end_ts)
        
        if isinstance(result, list):
            print(f"  {days} dias: OK - {len(result)} klines")
        else:
            print(f"  {days} dias: ERRO - {result.get('message', result)}")
    
    # Teste 2: Limite de klines por request para 1m
    print("\n" + "=" * 60)
    print("TESTE 2: Descobrir limite de klines (1m)")
    print("=" * 60)
    
    # 1 dia = 1440 minutos = 1440 klines potenciais
    # Vamos testar diferentes ranges
    test_ranges_hours = [1, 6, 12, 24, 48, 72, 168]  # até 1 semana
    
    for hours in test_ranges_hours:
        start_ts = int((now - timedelta(hours=hours)).timestamp())
        result = get_klines("BTC_USDC", "1m", start_ts, end_ts)
        
        if isinstance(result, list):
            expected = hours * 60
            print(f"  {hours}h ({expected} esperados): {len(result)} klines")
        else:
            print(f"  {hours}h: ERRO - {result.get('message', result)}")
    
    # Teste 3: Descobrir a data mais antiga disponível
    print("\n" + "=" * 60)
    print("TESTE 3: Data mais antiga disponível")
    print("=" * 60)
    
    # Testar com chunks de 365 dias para trás
    symbols_to_test = ["BTC_USDC", "SOL_USDC", "ETH_USDC", "SOL_USDC_PERP", "BTC_USDC_PERP"]
    
    for symbol in symbols_to_test:
        # Começar de hoje e ir para trás
        current_end = end_ts
        earliest_date = None
        
        for i in range(10):  # Máximo 10 anos para trás
            current_start = int((datetime.fromtimestamp(current_end) - timedelta(days=365)).timestamp())
            result = get_klines(symbol, "1d", current_start, current_end)
            
            if isinstance(result, list) and len(result) > 0:
                earliest_date = result[0]['start']
                current_end = int(datetime.strptime(result[0]['start'], "%Y-%m-%d %H:%M:%S").timestamp())
            else:
                break
        
        print(f"  {symbol}: {earliest_date}")
    
    # Teste 4: Verificar resposta do 1m com range grande
    print("\n" + "=" * 60)
    print("TESTE 4: Limite exato para 1m")
    print("=" * 60)
    
    # O limite parece ser por klines, não por tempo
    # Vamos testar incrementando
    test_minutes = [100, 500, 1000, 1500, 2000]
    
    for minutes in test_minutes:
        start_ts = int((now - timedelta(minutes=minutes)).timestamp())
        result = get_klines("BTC_USDC", "1m", start_ts, end_ts)
        
        if isinstance(result, list):
            print(f"  {minutes} min pedidos: {len(result)} klines retornados")
        else:
            print(f"  {minutes} min: ERRO - {result.get('message', result)}")
