from pybit.unified_trading import HTTP
import pandas as pd
import numpy as np
import talib
import ccxt

# Configurar la API de Bybit
session = HTTP()

def obtener_datos_historicos_binance(symbol="BTCUSDT", timeframe="1h", limite=200):
    """
    Obtiene datos históricos de futuros de Binance y los convierte en un DataFrame.

    Args:
        symbol (str): Símbolo del par de trading (ej. "BTC/USDT").
        timeframe (str): Intervalo de tiempo (ej. "1m", "5m", "1h", "1d").
        limite (int): Número máximo de velas a obtener (default: 200).

    Returns:
        pd.DataFrame: DataFrame con columnas ['open', 'high', 'low', 'close', 'volume'].
    """
    try:
        # Inicializar cliente de Binance para futuros
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}  # Especificar mercado de futuros
        })


        # Configurar para mostrar todas las columnas
        pd.set_option('display.max_columns', None)
        # Obtener datos OHLCV
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limite)
        print(ohlcv)
        # Convertir a DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')  # Convertir timestamp a datetime
        df.set_index('timestamp', inplace=True)  # Establecer timestamp como índice

        return df

    except Exception as e:
        print(f"Error al obtener datos históricos de Binance: {e}")
        return None


def obtener_datos_bybit(simbolo="BTCUSDT", intervalo="60", limite=50):
    """Obtiene datos de velas de Bybit y adapta la estructura de las columnas."""
    datos = session.get_kline(category="linear", symbol=simbolo, interval=intervalo, limit=limite)
    print(datos)
    if "result" not in datos or "list" not in datos["result"]:
        raise ValueError("La respuesta de la API no contiene datos de velas válidos.")
    
    columnas = ["timestamp", "open", "high", "low", "close", "volume", "turnover"]
    df = pd.DataFrame(datos["result"]["list"], columns=columnas)
    
    # Verificar las columnas reales que devuelve la API
    print("Columnas recibidas:", df.columns)
    
    # Asegurar que las columnas necesarias existen antes de convertir a float
    required_columns = ["open", "close", "high", "low", "volume"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise KeyError(f"Faltan las siguientes columnas en el DataFrame: {missing_columns}")
    
    df[required_columns] = df[required_columns].astype(float)
    return df

def calcular_indicadores(df):
    """Calcula RSI y ADX usando TA-Lib."""
    df["RSI"] = talib.RSI(df["close"], timeperiod=14)
    df["ADX"] = talib.ADX(df["high"], df["low"], df["close"], timeperiod=14)
    return df

def calcular_probabilidad_entrada(df):
    """Calcula la probabilidad de entrar en largo o corto basado en Open Interest, volumen, RSI y ADX."""
    precio_actual = df["close"].iloc[-1]
    precio_anterior = df["close"].iloc[-2]
    volumen_actual = df["volume"].iloc[-1]
    volumen_anterior = df["volume"].iloc[-2]
    oi_actual = df["open_interest"].iloc[-1] if "open_interest" in df.columns else None
    oi_anterior = df["open_interest"].iloc[-2] if "open_interest" in df.columns else None
    rsi_actual = df["RSI"].iloc[-1]
    adx_actual = df["ADX"].iloc[-1]
    
    prob_long = 0
    prob_short = 0
    
    # Evaluar tendencia del precio
    precio_sube = precio_actual > precio_anterior
    precio_baja = precio_actual < precio_anterior
    
    # Evaluar tendencia del volumen
    volumen_sube = volumen_actual > volumen_anterior
    
    # Evaluar tendencia del Open Interest (si está disponible)
    if oi_actual is not None and oi_anterior is not None:
        oi_sube = oi_actual > oi_anterior
        oi_baja = oi_actual < oi_anterior
    else:
        oi_sube = oi_baja = False
    
    # Condiciones para entrar en largo
    if precio_sube and volumen_sube and oi_sube and rsi_actual > 50 and adx_actual > 20:
        prob_long = 85  # Alta probabilidad de continuación alcista
    elif precio_sube and oi_baja:
        prob_long = 40  # Posible trampa alcista, entrada con precaución
    
    # Condiciones para entrar en corto
    if precio_baja and volumen_sube and oi_sube and rsi_actual < 50 and adx_actual > 20:
        prob_short = 85  # Alta probabilidad de continuación bajista
    elif precio_baja and oi_baja:
        prob_short = 40  # Posible trampa bajista, entrada con precaución
    
    # Ajustar si OI y precio están en zona de manipulación
    if oi_sube and not (precio_sube or precio_baja):
        prob_long = 20  # Squeeze posible, baja confianza
        prob_short = 20  # Squeeze posible, baja confianza
    
    return {"prob_long": prob_long, "prob_short": prob_short}

# Ejemplo de uso
df = obtener_datos_bybit()
# df = obtener_datos_historicos_binance()
df = calcular_indicadores(df)
resultado = calcular_probabilidad_entrada(df)
print(resultado)
