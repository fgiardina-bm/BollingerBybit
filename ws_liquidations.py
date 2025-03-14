import asyncio
import json
import websockets
import requests

# Función para obtener dinámicamente los pares de trading con USDT en Futuros
def get_all_usdt_pairs():
    url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Verifica que la solicitud fue exitosa
        data = response.json()
        symbols = [
            symbol["symbol"].lower()
            for symbol in data.get("symbols", [])
            if symbol["symbol"].endswith("USDT") and symbol["status"] == "TRADING"
        ]
        return symbols
    except requests.RequestException as e:
        print(f"⚠️ Error al obtener los pares de Binance: {e}")
        return []

async def binance_kline_ws():
    symbols = get_all_usdt_pairs()  # ❌ No usar await, ya que es una función normal
    if not symbols:
        print("🚨 No se encontraron pares para suscribirse")
        return
    
    # Formatear correctamente los streams con kline de 1 minuto
    stream_names = [f"{symbol}@kline_1m" for symbol in symbols]
    url = f"wss://fstream.binance.com/stream?streams={'/'.join(stream_names)}"
    
    while True:
        try:
            async with websockets.connect(url) as websocket:
                print(f"📡 Conectado a {url}")
                while True:
                    try:
                        response = await websocket.recv()
                        data = json.loads(response)
                        
                        # Verificar que los datos tengan la estructura esperada
                        if "data" in data and "k" in data["data"]:
                            kline = data["data"]["k"]
                            symbol = data["data"]["s"]
                            close_time = kline["T"]
                            open_price = float(kline["o"])
                            close_price = float(kline["c"])
                            high_price = float(kline["h"])
                            low_price = float(kline["l"])
                            volume = float(kline["v"])

                            print(f"📊 {symbol} | Open: {open_price} | Close: {close_price} | High: {high_price} | Low: {low_price} | Volume: {volume}")
                    
                    except json.JSONDecodeError:
                        print("⚠️ Error al decodificar JSON")
                    except websockets.exceptions.ConnectionClosed:
                        print("⚠️ WebSocket desconectado, intentando reconectar...")
                        break  # Salimos del bucle interno para reconectar
        
        except Exception as e:
            print(f"🚨 Error en WebSocket: {e}")
            await asyncio.sleep(5)  # Esperar antes de reconectar

async def main():
    while True:
        try:
            await binance_kline_ws()
        except Exception as e:
            print(f"⚠️ Error en WebSocket, reconectando... {e}")
            await asyncio.sleep(5)  # Esperar y reconectar

asyncio.run(main())
