import pandas as pd
import numpy as np
import requests
from scipy.signal import argrelextrema


def obtener_datos_futuros_bybit(symbol="BTCUSDT", interval="60", limit=200):
    """Obtiene datos históricos de Bybit para un par dado."""
    url = f"https://api.bybit.com/v2/public/kline/list?symbol={symbol}&interval={interval}&limit={limit}"
    response = requests.get(url)
    data = response.json()["result"]
    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["open_time"], unit="s")
    df = df[["timestamp", "open", "high", "low", "close", "volume", "turnover"]]
    df[["open", "high", "low", "close", "volume", "turnover"]] = df[["open", "high", "low", "close", "volume", "turnover"]].astype(float)
    return df


def obtener_datos_futuros_binance(symbol, intervalo):
    """Obtiene datos históricos de futuros de Binance."""
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={intervalo}&limit=1000"
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
        'quote_asset_volume', 'trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
    return df

def obtener_extremos(df, ventana):
    """Obtiene los niveles máximos y mínimos de los precios."""
    maximos = df.iloc[argrelextrema(df['high'].values, np.greater, order=ventana)[0]]
    minimos = df.iloc[argrelextrema(df['low'].values, np.less, order=ventana)[0]]
    return maximos, minimos

def filtrar_niveles(niveles, tolerancia):
    """Filtra los niveles de soporte y resistencia más importantes."""
    niveles_clave = []
    for nivel in sorted(niveles, reverse=True):
        if not any(abs(nivel - x) < tolerancia * nivel for x in niveles_clave):
            niveles_clave.append(nivel)
    return niveles_clave


def calcular_soportes_resistencias(df, ventana, tolerancia):
    """Calcula niveles de soporte y resistencia basados en los máximos y mínimos de precios."""
    maximos = df.iloc[argrelextrema(df['high'].values, np.greater, order=ventana)[0]]
    minimos = df.iloc[argrelextrema(df['low'].values, np.less, order=ventana)[0]]

    niveles = {
        "resistencias": sorted(filtrar_niveles(maximos['high'], tolerancia), reverse=True),
        "soportes": sorted(filtrar_niveles(minimos['low'], tolerancia))
    }
    return niveles

def contar_toques(df, niveles, tolerancia, min_toques=4):
    """Filtra niveles según la cantidad de veces que han sido tocados."""
    conteo = {}
    for nivel in niveles:
        toques = ((df['low'] <= nivel * (1 + tolerancia)) & (df['high'] >= nivel * (1 - tolerancia))).sum()
        if toques >= min_toques:
            conteo[nivel] = toques
    return sorted(conteo, key=conteo.get, reverse=True)[:3]  # Top 3 niveles con más toques

def calcular_soportes_resistencias_fuertes(df, ventana=10, tolerancia=0.005, min_toques=4):
    """Calcula los 3 soportes y resistencias más fuertes según la cantidad de veces que han sido tocados."""
    niveles = calcular_soportes_resistencias(df, ventana, tolerancia)
    soportes_fuertes = contar_toques(df, niveles["soportes"], tolerancia, min_toques)
    resistencias_fuertes = contar_toques(df, niveles['resistencias'], tolerancia, min_toques=min_toques)
    return {
        "soportes": sorted(soportes_fuertes),
        "resistencias": sorted(resistencias_fuertes, reverse=True)
    }

df_btc = obtener_datos_futuros_binance("BTCUSDT", intervalo="4h")
niveles_fuertes = calcular_soportes_resistencias_fuertes(df_btc, ventana=10, tolerancia=0.005, min_toques=1)

print("📉 **Soportes Fuertes**:", niveles_fuertes['soportes'])
print("📈 **Resistencias Fuertes**: ", niveles_fuertes['resistencias'])
