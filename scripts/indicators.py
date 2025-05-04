import pandas as pd
from dotenv import load_dotenv
import numpy as np
import talib
from config import *
import time
import requests

def calcular_rsi_talib(closes, window=14):
    rsi = talib.RSI(np.array(closes), timeperiod=window)
    return rsi[-1]

def calcular_bandas_bollinger(data, ventana=14, desviacion=2):
    data['MA'] = data[4].rolling(window=ventana).mean()
    data['UpperBand'] = data['MA'] + (data[4].rolling(window=ventana).std() * desviacion)
    data['LowerBand'] = data['MA'] - (data[4].rolling(window=ventana).std() * desviacion)
    data['BB_Width_%'] = ((data['UpperBand'] - data['LowerBand']) / data['MA']) * 100
    return data.iloc[-1]

def calcular_ema(data, ventana=20):
    try:
        ema = data['close'].ewm(span=ventana, adjust=False).mean()
        return ema.iloc[-1]
    except Exception as e:
        print(f"Error al calcular la EMA: {e}")
        return None

def calcular_atr(highs, lows, closes, timeperiod=14):
    atr = talib.ATR(np.array(highs), np.array(lows), np.array(closes), timeperiod=timeperiod)
    return atr[-1]

def calcular_adx(highs, lows, closes, timeperiod=14):
    adx = talib.ADX(np.array(highs), np.array(lows), np.array(closes), timeperiod=timeperiod)
    return adx[-1]

def calcular_sma(closes, timeperiod=30):
    sma = talib.SMA(np.array(closes), timeperiod=timeperiod)
    return sma[-1]

def detectar_tendencia_bb_cci(high_prices, low_prices, close_prices):
    """
    Detecta señales de cambio de tendencia usando Bollinger Bands y CCI.

    Parámetros:
        high_prices  -> Lista o array de precios máximos
        low_prices   -> Lista o array de precios mínimos
        close_prices -> Lista o array de precios de cierre

    Retorna:
        "Alcista"  -> Si hay una señal de reversión alcista
        "Bajista"  -> Si hay una señal de reversión bajista
        None       -> Si no se detecta una señal clara
    """
    
    # Calcular Bollinger Bands
    upper, middle, lower = talib.BBANDS(close_prices, timeperiod=20)

    # Calcular CCI
    cci = talib.CCI(high_prices, low_prices, close_prices, timeperiod=14)

    # Último valor de los indicadores
    close = close_prices[-1]
    lower_band = lower[-1]
    upper_band = upper[-1]
    cci_value = cci[-1]

    # Señal de compra (alcista)
    if close < lower_band and cci_value < -100:
        return "A"

    # Señal de venta (bajista)
    if close > upper_band and cci_value > 100:
        return "B"

    # No hay señal clara
    return ""

def calcular_cci(high_prices, low_prices, close_prices):

    # Calcular CCI
    cci = talib.CCI(high_prices, low_prices, close_prices, timeperiod=14)

    cci_value = cci[-1]

    return cci_value

def detectar_cambio_tendencia(open_prices, high_prices, low_prices, close_prices):

    """
    Detecta posibles cambios de tendencia usando patrones de velas + RSI o MACD.
    
    Parámetros:
        open_prices  -> Lista o array de precios de apertura
        high_prices  -> Lista o array de precios máximos
        low_prices   -> Lista o array de precios mínimos
        close_prices -> Lista o array de precios de cierre
        
    Retorna:
        "Alcista"  -> Si hay una señal de reversión alcista
        "Bajista"  -> Si hay una señal de reversión bajista
        None       -> Si no se detecta una señal clara
    """
    
    # Detectar patrones de velas
    patron_alcista = talib.CDLENGULFING(open_prices, high_prices, low_prices, close_prices) \
                     + talib.CDLHAMMER(open_prices, high_prices, low_prices, close_prices) \
                     + talib.CDLPIERCING(open_prices, high_prices, low_prices, close_prices) \
                     + talib.CDLMORNINGSTAR(open_prices, high_prices, low_prices, close_prices) \
                     + talib.CDL3WHITESOLDIERS(open_prices, high_prices, low_prices, close_prices)

    patron_bajista = talib.CDLENGULFING(open_prices, high_prices, low_prices, close_prices) \
                     + talib.CDLSHOOTINGSTAR(open_prices, high_prices, low_prices, close_prices) \
                     + talib.CDLDARKCLOUDCOVER(open_prices, high_prices, low_prices, close_prices) \
                     + talib.CDLEVENINGSTAR(open_prices, high_prices, low_prices, close_prices) \
                     + talib.CDL3BLACKCROWS(open_prices, high_prices, low_prices, close_prices)


    # Calcular RSI
    rsi = talib.RSI(close_prices, timeperiod=14)

    # Calcular MACD
    macd, macd_signal, _ = talib.MACD(close_prices, fastperiod=12, slowperiod=26, signalperiod=9)

    # Última vela (índice -1)
    if patron_alcista[-1] > 0:  # Si hay patrón alcista
        if rsi[-1] < 30 or (macd[-1] > macd_signal[-1] and macd[-2] < macd_signal[-2]):
            return "A"

    if patron_bajista[-1] < 0:  # Si hay patrón bajista
        if rsi[-1] > 70 or (macd[-1] < macd_signal[-1] and macd[-2] > macd_signal[-2]):
            return "B"

    return ""  # No hay señal clara

def detectar_soportes_resistencias(high_prices, low_prices, period=50):
    """
    Detecta niveles de soporte y resistencia usando máximos y mínimos locales.

    Parámetros:
        high_prices -> Lista o array de precios máximos
        low_prices  -> Lista o array de precios mínimos
        period      -> Número de velas para analizar

    Retorna:
        soporte, resistencia -> Últimos valores detectados
    """
    
    # Detectar resistencia (máximos en el período)
    resistencia = talib.MAX(high_prices, timeperiod=period)
    
    # Detectar soporte (mínimos en el período)
    soporte = talib.MIN(low_prices, timeperiod=period)
    
    return soporte[-1], resistencia[-1]
 
def soporte_resistencias(precios, bins=20):
    """
    Encuentra los niveles de soporte y resistencia basándose en la frecuencia de precios cercanos.
    """
    hist, bin_edges = np.histogram(precios, bins=bins)
    niveles = (bin_edges[:-1] + bin_edges[1:]) / 2  # Centros de los bins
    niveles_importantes = niveles[hist > np.percentile(hist, 75)]  # Filtra los más significativos
    return niveles_importantes

def calcular_macd(closes, fastperiod=12, slowperiod=26, signalperiod=9):
    macd, macdsignal, macdhist = talib.MACD(np.array(closes), fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=signalperiod)
    return macd[-1], macdsignal[-1], macdhist[-1], macd[-2], macdsignal[-2], macdhist[-2]


def vela_martillo_alcista(open_prices, high_prices, low_prices, close_prices):
    patron = talib.CDLHAMMER(open_prices, high_prices, low_prices, close_prices)
    return patron[-1] > 0, close_prices[-1], close_prices[-2], close_prices[-3]

def vela_martillo_bajista(open_prices, high_prices, low_prices, close_prices):
    patron = talib.CDLINVERTEDHAMMER(open_prices, high_prices, low_prices, close_prices)
    return patron[-1] > 0, close_prices[-1], close_prices[-2], close_prices[-3]


def patron_velas_alcistas(open_prices, high_prices, low_prices, close_prices):
    
    patron_alcista = talib.CDLENGULFING(open_prices, high_prices, low_prices, close_prices) \
                     + talib.CDLHAMMER(open_prices, high_prices, low_prices, close_prices) \
                     + talib.CDLPIERCING(open_prices, high_prices, low_prices, close_prices) \
                     + talib.CDLMORNINGSTAR(open_prices, high_prices, low_prices, close_prices) \
                     + talib.CDL3WHITESOLDIERS(open_prices, high_prices, low_prices, close_prices)

    return patron_alcista[-1] > 0


def patron_velas_bajistas(open_prices, high_prices, low_prices, close_prices):

    patron_bajista = talib.CDLENGULFING(open_prices, high_prices, low_prices, close_prices) \
                     + talib.CDLSHOOTINGSTAR(open_prices, high_prices, low_prices, close_prices) \
                     + talib.CDLDARKCLOUDCOVER(open_prices, high_prices, low_prices, close_prices) \
                     + talib.CDLEVENINGSTAR(open_prices, high_prices, low_prices, close_prices) \
                     + talib.CDL3BLACKCROWS(open_prices, high_prices, low_prices, close_prices)

    return patron_bajista[-1] < 0



def patron_velas_martillo_alcista(open_prices, high_prices, low_prices, close_prices):
    
    patron_martillo_alcista = talib.CDLENGULFING(open_prices, high_prices, low_prices, close_prices) \
                     + talib.CDLHAMMER(open_prices, high_prices, low_prices, close_prices) \
                     + talib.CDLPIERCING(open_prices, high_prices, low_prices, close_prices) \
                     + talib.CDLMORNINGSTAR(open_prices, high_prices, low_prices, close_prices) \
                     + talib.CDL3WHITESOLDIERS(open_prices, high_prices, low_prices, close_prices)

    rsi = talib.RSI(close_prices, timeperiod=14)

    return patron_martillo_alcista[-1] > 0 and (rsi[-1] < 25)

def patron_velas_martillo_bajista(open_prices, high_prices, low_prices, close_prices):

    patron_martillo_bajista = talib.CDLENGULFING(open_prices, high_prices, low_prices, close_prices) \
                     + talib.CDLSHOOTINGSTAR(open_prices, high_prices, low_prices, close_prices) \
                     + talib.CDLDARKCLOUDCOVER(open_prices, high_prices, low_prices, close_prices) \
                     + talib.CDLEVENINGSTAR(open_prices, high_prices, low_prices, close_prices) \
                     + talib.CDL3BLACKCROWS(open_prices, high_prices, low_prices, close_prices)

    rsi = talib.RSI(close_prices, timeperiod=14)

    return patron_martillo_bajista[-1] < 0 and (rsi[-1] > 75)








def macd_alcista(close_prices):
    macd, macd_signal, _ = talib.MACD(close_prices, fastperiod=12, slowperiod=26, signalperiod=9)

    return (macd[-1] > macd_signal[-1] and macd[-2] < macd_signal[-2])

def macd_bajista(close_prices):
    macd, macd_signal, _ = talib.MACD(close_prices, fastperiod=12, slowperiod=26, signalperiod=9)

    return (macd[-1] < macd_signal[-1] and macd[-2] > macd_signal[-2])

def is_strong_bullish_signal(open_prices, high_prices, low_prices, close_prices):
    """
    Devuelve True si hay una fuerte señal alcista (dos o más patrones alcistas detectados en la última vela).
    """
    bullish_patterns = [
        talib.CDLENGULFING(open_prices, high_prices, low_prices, close_prices),
        talib.CDLHAMMER(open_prices, high_prices, low_prices, close_prices),
        talib.CDLPIERCING(open_prices, high_prices, low_prices, close_prices),
        talib.CDLMORNINGSTAR(open_prices, high_prices, low_prices, close_prices),
        talib.CDL3WHITESOLDIERS(open_prices, high_prices, low_prices, close_prices)
    ]

    signals = sum(pattern[-1] == 100 for pattern in bullish_patterns)  # Verifica la última vela
    return signals >= 2  # Si hay 2 o más patrones alcistas en la última vela, retorna True

def is_strong_bearish_signal(open_prices, high_prices, low_prices, close_prices):
    """
    Devuelve True si hay una fuerte señal bajista (dos o más patrones bajistas detectados en la última vela).
    """
    bearish_patterns = [
        talib.CDLENGULFING(open_prices, high_prices, low_prices, close_prices),
        talib.CDLSHOOTINGSTAR(open_prices, high_prices, low_prices, close_prices),
        talib.CDLDARKCLOUDCOVER(open_prices, high_prices, low_prices, close_prices),
        talib.CDLEVENINGSTAR(open_prices, high_prices, low_prices, close_prices),
        talib.CDL3BLACKCROWS(open_prices, high_prices, low_prices, close_prices)
    ]

    signals = sum(pattern[-1] == -100 for pattern in bearish_patterns)  # Verifica la última vela
    return signals >= 2  # Si hay 2 o más patrones bajistas en la última vela, retorna True


# Función para detectar soportes y resistencias
def detectar_soportes_resistencias6(symbol, df, window=50):
    """
    Detecta soportes y resistencias utilizando los máximos y mínimos de un periodo de tiempo.
    :param df: DataFrame con columnas ['high', 'low']
    :param window: tamaño de ventana para detectar los pivotes
    :return: niveles de soporte y resistencia
    """
    soportes = []
    resistencias = []

    for i in range(window, len(df) - window):
        # Pivote alcista (mínimo local)
        if df['low'][i] == min(df['low'][i - window:i + window]):
            soportes.append(df['low'][i])
        
        # Pivote bajista (máximo local)
        if df['high'][i] == max(df['high'][i - window:i + window]):
            resistencias.append(df['high'][i])

    return soportes, resistencias


def detectar_soportes_resistencias_opt1(symbol, df, window=50):
    """
    Detecta soportes y resistencias utilizando los máximos y mínimos de un periodo de tiempo.
    :param df: DataFrame con columnas ['high', 'low']
    :param window: tamaño de ventana para detectar los pivotes
    :return: niveles de soporte y resistencia
    """
    soportes = []
    resistencias = []

    for i in range(window, len(df)):
        # Soporte: Mínimo en las últimas 'window' velas
        if df['low'][i] == min(df['low'][i - window:i + 1]):
            soportes.append(df['low'][i])

        # Resistencia: Máximo en las últimas 'window' velas
        if df['high'][i] == max(df['high'][i - window:i + 1]):
            resistencias.append(df['high'][i])

    return soportes, resistencias



def detectar_soportes_resistencias_opt2(symbol, df, window=50, delta=0.0001):
    """
    Similar a la versión anterior, pero permite una tolerancia 'delta' para detectar
    soportes y resistencias y evitar falsos negativos por pequeñas diferencias.
    :param df: DataFrame con columnas ['high', 'low']
    :param window: número de observaciones a considerar a cada lado del punto actual.
    :param delta: tolerancia para la comparación
    :return: Tupla con listas: (soportes, resistencias)
    """
    df['rolling_min'] = df['low'].rolling(window=2*window+1, center=True).min()
    df['rolling_max'] = df['high'].rolling(window=2*window+1, center=True).max()

    # Se consideran soportes/resistencias si el valor actual está dentro del rango definido por delta
    df['soporte'] = abs(df['low'] - df['rolling_min']) < delta
    df['resistencia'] = abs(df['high'] - df['rolling_max']) < delta

    soportes = df.loc[df['soporte'], 'low'].tolist()
    resistencias = df.loc[df['resistencia'], 'high'].tolist()

    return soportes, resistencias


# Función para analizar el volumen
def confirmar_volumen6(symbol, df, window=20):
    """
    Compara el volumen de la vela actual con el promedio de los últimos 'window' períodos.
    :param df: DataFrame con columna 'volume'
    :param window: tamaño de la ventana para el promedio
    :return: Booleano indicando si el volumen está aumentando
    """
    df['avg_volume'] = df['volume'].rolling(window).mean()
    df['volumen_en_aumento'] = df['volume'] > df['avg_volume']
    # Ver si el volumen actual es mayor al promedio
    return df['volumen_en_aumento'].iloc[-1]

# Función para calcular los niveles de Fibonacci
def fibonacci_retracement6(symbol, df):
    """
    Calcula los niveles de Fibonacci de un movimiento entre el máximo y el mínimo reciente.
    :param df: DataFrame con las columnas 'high' y 'low'
    :return: diccionario con los niveles de Fibonacci
    """
    max_price = df['high'].max()
    min_price = df['low'].min()

    # Niveles de Fibonacci
    fib_levels = {
        '0.236': min_price + 0.236 * (max_price - min_price),
        '0.382': min_price + 0.382 * (max_price - min_price),
        '0.5': min_price + 0.5 * (max_price - min_price),
        '0.618': min_price + 0.618 * (max_price - min_price),
        '0.786': min_price + 0.786 * (max_price - min_price),
    }

    return fib_levels

# Función para verificar si un precio está cerca de una lista de niveles en un % de tolerancia
def esta_cerca(precio, niveles, tolerancia=0.01):  # 1% de tolerancia
    return any(abs(precio - nivel) <= nivel * tolerancia for nivel in niveles)

def filtrar_niveles(niveles, tolerancia):
    """
    Filtra una lista de niveles eliminando aquellos que están muy próximos.
    :param niveles: lista de precios (soportes o resistencias)
    :param tolerancia: diferencia mínima entre niveles para considerarlos distintos
    :return: lista filtrada de niveles
    """
    if not niveles:
        return []
    
    niveles.sort()
    niveles_filtrados = [niveles[0]]
    
    for nivel in niveles[1:]:
        if abs(nivel - niveles_filtrados[-1]) >= tolerancia:
            niveles_filtrados.append(nivel)
    
    return niveles_filtrados


def confirmar_patron_con_soporte_resistencia(symbol, df, patron_ultimo, window=50, tolerancia=0.01):
    global test_mode
    # Detectamos soportes y resistencias

    soportes, resistencias = detectar_soportes_resistencias_opt1(symbol, df, window)

    soportes = filtrar_niveles(soportes, tolerancia=0.01)
    resistencias = filtrar_niveles(resistencias, tolerancia=0.01)

    volumen_aumento = confirmar_volumen6(symbol,df)
    niveles_fib = fibonacci_retracement6(symbol, df)

    if test_mode == 1:
        print(f"1 {symbol} {resistencias} | {df['close'].iloc[-1]} | {soportes}")
    
    # Último precio de cierre
    ultimo_precio = df['close'].iloc[-1]
    
    # Verificamos si está cerca de un nivel Fibonacci
    cerca_fib = esta_cerca(ultimo_precio, niveles_fib.values(), tolerancia)

    # Verificamos si está cerca de un soporte o resistencia
    cerca_soporte = esta_cerca(ultimo_precio, soportes, tolerancia)
    cerca_resistencia = esta_cerca(ultimo_precio, resistencias, tolerancia)

    # Condición: patrón alcista cerca de soporte o patrón bajista cerca de resistencia
    if patron_ultimo == 'alcista':
        if cerca_soporte and volumen_aumento and cerca_fib:
            return True,cerca_soporte,cerca_resistencia,volumen_aumento,cerca_fib # Confirmación de patrón alcista
    elif patron_ultimo == 'bajista':
        if cerca_resistencia and volumen_aumento and cerca_fib:
            return True,cerca_soporte,cerca_resistencia,volumen_aumento,cerca_fib # Confirmación de patrón bajista

    return False,cerca_soporte,cerca_resistencia,volumen_aumento,cerca_fib



def confirmar_patron_con_soporte_resistencia_3niveles(symbol, df, patron_ultimo, item, bb, window=50, tolerancia=0.01):
    global test_mode
    # Detectamos soportes y resistencias

    niveles = item['niveles']
   
    volumen_aumento = confirmar_volumen6(symbol,df)
    niveles_fib = fibonacci_retracement6(symbol, df)
    UpperBandDiff = abs(bb['UpperBand'] - df['close'].iloc[-1])
    LowerBandDiff = abs(bb['LowerBand'] - df['close'].iloc[-1])
    UpperTolerance = bb['UpperBand'] * tolerancia
    LowerTolerance = bb['LowerBand'] * tolerancia
    # price_in_bollinger_upper = abs(bb['UpperBand'] - df['close'].iloc[-1]) <= bb['UpperBand'] * tolerancia or df['close'].iloc[-1] > bb['UpperBand']
    # price_in_bollinger_lower = abs(bb['LowerBand'] - df['close'].iloc[-1]) <= bb['LowerBand'] * tolerancia or df['close'].iloc[-1] < bb['LowerBand']
    price_in_bollinger_upper = df['close'].iloc[-1] > bb['UpperBand']
    price_in_bollinger_lower = df['close'].iloc[-1] < bb['LowerBand']



    if test_mode == 1:
        print(f"{test_mode} {symbol} {niveles} | {df['close'].iloc[-1]}")
    
    # Último precio de cierre
    ultimo_precio = df['close'].iloc[-1]
    
    # Verificamos si está cerca de un nivel Fibonacci
    cerca_fib = esta_cerca(ultimo_precio, niveles_fib.values(), tolerancia)

    # Verificamos si está cerca de un soporte o resistencia
    cerca_soporte_resistencia = esta_cerca(ultimo_precio, niveles, tolerancia)

    # Condición: patrón alcista cerca de soporte o patrón bajista cerca de resistencia
    if patron_ultimo == 'alcista':
        if cerca_soporte_resistencia and volumen_aumento and price_in_bollinger_lower:
            return True,cerca_soporte_resistencia,volumen_aumento,price_in_bollinger_lower,UpperBandDiff,LowerBandDiff,UpperTolerance,LowerTolerance # Confirmación de patrón alcista
    elif patron_ultimo == 'bajista':
        if  cerca_soporte_resistencia and volumen_aumento and price_in_bollinger_upper:
            return True,cerca_soporte_resistencia,volumen_aumento,price_in_bollinger_upper,UpperBandDiff,LowerBandDiff,UpperTolerance,LowerTolerance  # Confirmación de patrón bajista

    return False,cerca_soporte_resistencia,volumen_aumento,price_in_bollinger_upper,UpperBandDiff,LowerBandDiff,UpperTolerance,LowerTolerance

def calcular_atr(df, periodo=14):
    """
    Calcula el ATR (Average True Range) para la volatilidad.
    
    Parámetros:
    - df: DataFrame con columnas ['open', 'high', 'low', 'close']
    - periodo: El período para el cálculo del ATR
    
    Retorna:
    - ATR: El valor del ATR para cada vela
    """
    atr = talib.ATR(df['high'], df['low'], df['close'], timeperiod=periodo)
    return atr

def obtener_multiplicador_atr(timeframe):
    """
    Ajusta el multiplicador del ATR basado en el timeframe.
    
    Parámetros:
    - timeframe: El timeframe de la operación (por ejemplo, '5m', '15m', '1h', '4h')
    
    Retorna:
    - multiplicador_atr: El multiplicador ajustado para el ATR basado en el timeframe
    """
    if timeframe == '5' or timeframe == '15':
        return 2.5  # Múltiplo más grande para timeframes más cortos
    elif timeframe == '60':
        return 1.5  # Múltiplo medio para timeframes más largos
    elif timeframe == '240':
        return 1.2  # Múltiplo más pequeño para timeframes largos
    else:
        return 1.5  # Valor predeterminado para otros timeframes

def establecer_stop_loss_dinamico(df, slm, tipo_trade, timeframe, multiplicador_atr=None):
    """
    Establece un stop loss dinámico basado en el ATR y el timeframe.
    
    Parámetros:
    - df: DataFrame con columnas ['open', 'high', 'low', 'close']
    - tipo_trade: 'long' o 'short', dependiendo de la operación
    - timeframe: Timeframe de la operación (e.g. '5m', '1h', '4h')
    - multiplicador_atr: Factor para ajustar el tamaño del stop loss en función de la volatilidad
    
    Retorna:
    - stop_loss: El precio del stop loss dinámico ajustado
    """
    if multiplicador_atr is None:
        multiplicador_atr = obtener_multiplicador_atr(timeframe)
    
    # Calcular el ATR
    atr = calcular_atr(df)
    
    # Usar el ATR más reciente para ajustar el stop loss
    atr_actual = atr.iloc[-1]
    
    if tipo_trade == 'long':
        # Colocar el stop loss debajo del mínimo de la vela, ajustado por el ATR
        stop_loss = df['close'].iloc[-1] - ((atr_actual * multiplicador_atr) * slm)
    elif tipo_trade == 'short':
        # Colocar el stop loss encima del máximo de la vela, ajustado por el ATR
        stop_loss = df['close'].iloc[-1] + ((atr_actual * multiplicador_atr) * slm)
    
    return stop_loss,atr_actual,multiplicador_atr,df['close'].iloc[-1]

def establecer_take_profit_dinamico(df, tpm, tipo_trade, timeframe, multiplicador_atr=None):
    """
    Establece un take profit dinámico basado en el ATR y el timeframe.
    
    Parámetros:
    - df: DataFrame con columnas ['open', 'high', 'low', 'close']
    - tipo_trade: 'long' o 'short', dependiendo de la operación
    - timeframe: Timeframe de la operación (e.g. '5m', '1h', '4h')
    - multiplicador_atr: Factor para ajustar el tamaño del take profit en función de la volatilidad
    
    Retorna:
    - take_profit: El precio del take profit dinámico ajustado
    """
    if multiplicador_atr is None:
        multiplicador_atr = obtener_multiplicador_atr(timeframe)
    
    # Calcular el ATR
    atr = calcular_atr(df)
    
    # Usar el ATR más reciente para ajustar el take profit
    atr_actual = atr.iloc[-1]
    
    if tipo_trade == 'long':
        # Colocar el take profit por encima del precio de cierre, ajustado por el ATR
        take_profit = df['close'].iloc[-1] + ((atr_actual * multiplicador_atr) * tpm)
    elif tipo_trade == 'short':
        # Colocar el take profit por debajo del precio de cierre, ajustado por el ATR
        take_profit = df['close'].iloc[-1] - ((atr_actual * multiplicador_atr) * tpm)
    
    return take_profit,atr_actual,multiplicador_atr,df['close'].iloc[-1]



def detectar_reversion_alcista(df, soportes, top_rsi, bottom_rsi):
    """
    Detecta señales de reversión alcista en velas de 5 minutos usando TA-Lib,
    confirmando con ADX y soportes.

    Parámetros:
    - df: DataFrame con columnas ['open', 'high', 'low', 'close', 'volume']
    - soportes: Lista de precios que se consideran soportes clave.

    Retorna:
    - Un array con señales: 1 (reversión alcista detectada) o 0 (sin señal)
    """

    global sr_fib_tolerancia, detectar_incluir_bbands, detectar_incluir_rsi, detectar_incluir_sr, detectar_incluir_patron_velas, detectar_incluir_volume, detectar_incluir_emas, detectar_incluir_adx

    # Detectar patrones de reversión alcista
    hammer = talib.CDLHAMMER(df['open'], df['high'], df['low'], df['close'])
    inverted_hammer = talib.CDLINVERTEDHAMMER(df['open'], df['high'], df['low'], df['close'])
    engulfing = talib.CDLENGULFING(df['open'], df['high'], df['low'], df['close'])
    piercing = talib.CDLPIERCING(df['open'], df['high'], df['low'], df['close'])

    # Calcular RSI
    rsi = talib.RSI(df['close'], timeperiod=14)
    # calcular bandas de bollinger
    upper_band, middle_band, lower_band = talib.BBANDS(df['close'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)




    # Calcular medias móviles
    sma_50 = talib.SMA(df['close'], timeperiod=50)
    sma_200 = talib.SMA(df['close'], timeperiod=200)

    # Confirmar volumen alto
    avg_volume = df['volume'].rolling(window=5).mean()
    volumen_alto = df['volume'] > avg_volume

    # Calcular ADX para confirmar fuerza de tendencia
    adx = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14)
    tendencia_fuerte = adx > 25  # Solo operar si hay tendencia fuerte

    # Confirmar si el precio está cerca de un soporte
    precio_actual = df['close'].iloc[-1]
    cerca_de_soporte = any(abs(precio_actual - s) / s < sr_fib_tolerancia for s in soportes)  # Margen del 1% o 2%

    # Condición para una fuerte reversión alcista
    # Create conditions based on global flags
    conditions = []
    
    if detectar_incluir_bbands == 1:
        conditions.append(pd.Series(precio_actual < lower_band, index=df.index))
    
    if detectar_incluir_patron_velas == 1:
        conditions.append((hammer == 100) | (inverted_hammer == 100) | (engulfing == 100) | (piercing == 100))
    
    if detectar_incluir_rsi == 1:
        conditions.append(rsi < bottom_rsi)
    
    if detectar_incluir_volume == 1:
        conditions.append(volumen_alto)
    
    if detectar_incluir_emas == 1:
        conditions.append(sma_50 < sma_200)
    
    if detectar_incluir_sr == 1:
        conditions.append(pd.Series(cerca_de_soporte, index=df.index))
    
    if detectar_incluir_adx == 1:
        conditions.append(tendencia_fuerte)
    
    # If no conditions are active, return array of zeros
    if not conditions:
        return pd.Series(0, index=df.index)
    
    # Combine all active conditions with logical AND
    reversion_alcista = pd.concat(conditions, axis=1).all(axis=1).astype(int)

    return reversion_alcista


def detectar_reversion_bajista(df, resistencias, top_rsi, bottom_rsi):
    """
    Detecta señales de reversión bajista en velas de 5 minutos usando TA-Lib,
    confirmando con ADX y resistencias.

    Parámetros:
    - df: DataFrame con columnas ['open', 'high', 'low', 'close', 'volume']
    - resistencias: Lista de precios que se consideran resistencias clave.

    Retorna:
    - Un array con señales: 1 (reversión bajista detectada) o 0 (sin señal)
    """

    global sr_fib_tolerancia, detectar_incluir_bbands, detectar_incluir_rsi, detectar_incluir_sr, detectar_incluir_patron_velas, detectar_incluir_volume, detectar_incluir_emas, detectar_incluir_adx

    # Detectar patrones de reversión bajista
    shooting_star = talib.CDLSHOOTINGSTAR(df['open'], df['high'], df['low'], df['close'])
    hanging_man = talib.CDLHANGINGMAN(df['open'], df['high'], df['low'], df['close'])
    engulfing = talib.CDLENGULFING(df['open'], df['high'], df['low'], df['close'])
    dark_cloud = talib.CDLDARKCLOUDCOVER(df['open'], df['high'], df['low'], df['close'])

    # Calcular RSI
    rsi = talib.RSI(df['close'], timeperiod=14)
    # calcular bandas de bollinger
    upper_band, middle_band, lower_band = talib.BBANDS(df['close'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)

    # Calcular medias móviles
    sma_50 = talib.SMA(df['close'], timeperiod=50)
    sma_200 = talib.SMA(df['close'], timeperiod=200)

    # Confirmar volumen alto
    avg_volume = df['volume'].rolling(window=5).mean()
    volumen_alto = df['volume'] > avg_volume

    # Calcular ADX para confirmar fuerza de tendencia
    adx = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14)
    tendencia_fuerte = adx > 25  # Solo operar si hay tendencia fuerte

    # Confirmar si el precio está cerca de una resistencia
    precio_actual = df['close'].iloc[-1]
    cerca_de_resistencia = any(abs(precio_actual - r) / r < sr_fib_tolerancia for r in resistencias)  # Margen del 1% o 2%

    # Condición para una fuerte reversión bajista
    # Create conditions based on global flags
    conditions = []
    
    if detectar_incluir_bbands == 1:
        conditions.append(pd.Series(precio_actual > upper_band, index=df.index))
    
    if detectar_incluir_patron_velas == 1:
        conditions.append((shooting_star == 100) | (hanging_man == 100) | (engulfing == -100) | (dark_cloud == -100))
    
    if detectar_incluir_rsi == 1:
        conditions.append(rsi > top_rsi)
    
    if detectar_incluir_volume == 1:
        conditions.append(volumen_alto)
    
    if detectar_incluir_emas == 1:
        conditions.append(sma_50 > sma_200)
    
    if detectar_incluir_sr == 1:
        conditions.append(pd.Series(cerca_de_resistencia, index=df.index))
    
    if detectar_incluir_adx == 1:
        conditions.append(tendencia_fuerte)
    
    # If no conditions are active, return array of zeros
    if not conditions:
        return pd.Series(0, index=df.index)
    
    # Combine all active conditions with logical AND
    reversion_bajista = pd.concat(conditions, axis=1).all(axis=1).astype(int)

    return reversion_bajista


def calcular_probabilidad_reversion(df, timeframe="240", ventana_analisis=20):
    """
    Calcula la probabilidad de reversión de tendencia basada en múltiples indicadores técnicos.
    
    Args:
        df (pd.DataFrame): DataFrame con datos OHLCV (open, high, low, close, volume)
        timeframe (str): Periodo de tiempo para ajustar la sensibilidad de ciertos indicadores
        ventana_analisis (int): Número de velas para el análisis de patrones históricos
        
    Returns:
        tuple: (
            probabilidad_reversion (float): Probabilidad de reversión (0-100%),
            direccion_probable (str): Dirección probable de la reversión ('alcista' o 'bajista'),
            factores_contribuyentes (dict): Factores que contribuyen a la señal
        )
    """

    # Extraer datos
    open_prices = df['open'].values
    high_prices = df['high'].values
    low_prices = df['low'].values
    close_prices = df['close'].values
    volumes = df['volume'].values
    
    # 1. Calcular indicadores técnicos
    # RSI (sobrecompra/sobreventa)
    rsi = talib.RSI(close_prices, timeperiod=14)
    rsi_actual = rsi[-1]
    
    # Bandas de Bollinger
    upper, middle, lower = talib.BBANDS(close_prices, timeperiod=20, nbdevup=2, nbdevdn=2)
    bb_width = (upper[-1] - lower[-1]) / middle[-1] * 100
    precio_vs_bb_upper = (close_prices[-1] - upper[-1]) / upper[-1] * 100
    precio_vs_bb_lower = (close_prices[-1] - lower[-1]) / lower[-1] * 100
    
    # Estocástico
    slowk, slowd = talib.STOCH(high_prices, low_prices, close_prices, 
                               fastk_period=14, slowk_period=3, slowk_matype=0, 
                               slowd_period=3, slowd_matype=0)
    stoch_k = slowk[-1]
    stoch_d = slowd[-1]
    
    # MACD
    macd_line, signal_line, macd_hist = talib.MACD(close_prices, fastperiod=12, slowperiod=26, signalperiod=9)
    macd_actual = macd_line[-1]
    signal_actual = signal_line[-1]
    hist_actual = macd_hist[-1]
    
    # ADX (fuerza de la tendencia)
    adx = talib.ADX(high_prices, low_prices, close_prices, timeperiod=14)
    adx_actual = adx[-1]
    
    # ATR (volatilidad)
    atr = talib.ATR(high_prices, low_prices, close_prices, timeperiod=14)
    atr_actual = atr[-1]
    atr_percent = atr_actual / close_prices[-1] * 100
    
    # 2. Detectar patrones de velas (señales de reversión)
    # Patrones alcistas
    hammer = talib.CDLHAMMER(open_prices, high_prices, low_prices, close_prices)[-1]
    piercing = talib.CDLPIERCING(open_prices, high_prices, low_prices, close_prices)[-1]
    morning_star = talib.CDLMORNINGSTAR(open_prices, high_prices, low_prices, close_prices)[-1]
    engulfing_alcista = talib.CDLENGULFING(open_prices, high_prices, low_prices, close_prices)[-1] > 0
    
    # Patrones bajistas
    hanging_man = talib.CDLHANGINGMAN(open_prices, high_prices, low_prices, close_prices)[-1]
    shooting_star = talib.CDLSHOOTINGSTAR(open_prices, high_prices, low_prices, close_prices)[-1]
    evening_star = talib.CDLEVENINGSTAR(open_prices, high_prices, low_prices, close_prices)[-1]
    engulfing_bajista = talib.CDLENGULFING(open_prices, high_prices, low_prices, close_prices)[-1] < 0
    
    # 3. Detectar divergencias
    # Crear serie de tendencia de precio
    ventana = min(ventana_analisis, len(close_prices) - 1)
    precio_tendencia = np.polyfit(np.arange(ventana), close_prices[-ventana:], 1)[0]
    rsi_tendencia = np.polyfit(np.arange(ventana), rsi[-ventana:], 1)[0]
    
    # Detección de divergencias
    divergencia_bajista = precio_tendencia > 0 and rsi_tendencia < 0
    divergencia_alcista = precio_tendencia < 0 and rsi_tendencia > 0
    
    # 4. Volumen inusual
    volumen_promedio = np.mean(volumes[-20:])
    volumen_actual = volumes[-1]
    volumen_inusual = volumen_actual > volumen_promedio * 1.5
    
    # 5. Detectar soportes y resistencias
    # Simplificado: usaremos máximos y mínimos recientes como proxy
    max_reciente = np.max(high_prices[-ventana_analisis:])
    min_reciente = np.min(low_prices[-ventana_analisis:])
    
    # Distancia a soportes y resistencias
    distancia_a_max = (max_reciente - close_prices[-1]) / close_prices[-1] * 100
    distancia_a_min = (close_prices[-1] - min_reciente) / close_prices[-1] * 100
    
    # 6. Análisis de tendencia
    ema20 = talib.EMA(close_prices, timeperiod=20)
    ema50 = talib.EMA(close_prices, timeperiod=50)
    ema200 = talib.EMA(close_prices, timeperiod=200)
    
    tendencia_corto_alcista = close_prices[-1] > ema20[-1]
    tendencia_medio_alcista = close_prices[-1] > ema50[-1]
    tendencia_largo_alcista = close_prices[-1] > ema200[-1]
    
    cruce_emas = (ema20[-2] < ema50[-2] and ema20[-1] > ema50[-1]) or (ema20[-2] > ema50[-2] and ema20[-1] < ema50[-1])

    # 7. Saturación de condiciones para timeframes específicos
    if timeframe in ["60", "240", "D"]:
        # Para timeframes mayores, damos más peso a indicadores de tendencia
        factor_timeframe = 1.2
    else:
        # Para timeframes menores, damos más peso a indicadores de momentum
        factor_timeframe = 0.8
    
    # 8. Calcular probabilidades
    factores_alcistas = 0
    max_factores_alcistas = 0
    factores_bajistas = 0
    max_factores_bajistas = 0
    
    # --- FACTORES ALCISTAS ---
    # RSI en sobreventa
    if rsi_actual < 30:
        factores_alcistas += 20
    elif rsi_actual < 40:
        factores_alcistas += 10
    max_factores_alcistas += 20
    
    # Estocástico en sobreventa
    if stoch_k < 20 and stoch_d < 20:
        factores_alcistas += 15
    max_factores_alcistas += 15
    
    # Precio cerca/debajo de banda inferior de Bollinger
    if precio_vs_bb_lower <= 0:
        factores_alcistas += 15
    elif precio_vs_bb_lower < 2:
        factores_alcistas += 8
    max_factores_alcistas += 15
    
    # Patrones de velas alcistas
    if hammer > 0 or piercing > 0 or morning_star > 0 or engulfing_alcista:
        factores_alcistas += 15
    max_factores_alcistas += 15
    
    # Divergencia alcista
    if divergencia_alcista:
        factores_alcistas += 20
    max_factores_alcistas += 20
    
    # Volumen inusual en mínimos
    if volumen_inusual and close_prices[-1] < ema20[-1]:
        factores_alcistas += 10
    max_factores_alcistas += 10
    
    # Cercanía a soporte
    if distancia_a_min < 3:
        factores_alcistas += 15
    elif distancia_a_min < 7:
        factores_alcistas += 8
    max_factores_alcistas += 15
    
    # MACD por debajo de la línea de señal pero acercándose
    if macd_actual < signal_actual and macd_actual > macd_line[-2]:
        factores_alcistas += 10
    max_factores_alcistas += 10
    
    # --- FACTORES BAJISTAS ---
    # RSI en sobrecompra
    if rsi_actual > 70:
        factores_bajistas += 20
    elif rsi_actual > 60:
        factores_bajistas += 10
    max_factores_bajistas += 20
    
    # Estocástico en sobrecompra
    if stoch_k > 80 and stoch_d > 80:
        factores_bajistas += 15
    max_factores_bajistas += 15
    
    # Precio cerca/arriba de banda superior de Bollinger
    if precio_vs_bb_upper >= 0:
        factores_bajistas += 15
    elif precio_vs_bb_upper > -2:
        factores_bajistas += 8
    max_factores_bajistas += 15
    
    # Patrones de velas bajistas
    if hanging_man < 0 or shooting_star < 0 or evening_star < 0 or engulfing_bajista:
        factores_bajistas += 15
    max_factores_bajistas += 15
    
    # Divergencia bajista
    if divergencia_bajista:
        factores_bajistas += 20
    max_factores_bajistas += 20
    
    # Volumen inusual en máximos
    if volumen_inusual and close_prices[-1] > ema20[-1]:
        factores_bajistas += 10
    max_factores_bajistas += 10
    
    # Cercanía a resistencia
    if distancia_a_max < 3:
        factores_bajistas += 15
    elif distancia_a_max < 7:
        factores_bajistas += 8
    max_factores_bajistas += 15
    
    # MACD por encima de la línea de señal pero alejándose
    if macd_actual > signal_actual and macd_actual < macd_line[-2]:
        factores_bajistas += 10
    max_factores_bajistas += 10

    # Considerar fuerza de tendencia (ADX)
    if adx_actual > 25:
        # Tendencia fuerte actual - más difícil de revertir
        factores_alcistas *= 0.9
        factores_bajistas *= 0.9
    elif adx_actual < 15:
        # Tendencia débil - más fácil de revertir
        factores_alcistas *= 1.1
        factores_bajistas *= 1.1
    
    # Ajustar por timeframe
    factores_alcistas *= factor_timeframe
    factores_bajistas *= factor_timeframe
    
    # 9. Calcular probabilidad final y dirección
    prob_alcista = (factores_alcistas / max_factores_alcistas) * 100
    prob_bajista = (factores_bajistas / max_factores_bajistas) * 100
    
    # Limitar a 100%
    prob_alcista = min(prob_alcista, 100)
    prob_bajista = min(prob_bajista, 100)
    
    # Decidir dirección y probabilidad final
    if prob_alcista > prob_bajista:
        direccion = 'alcista'
        probabilidad = prob_alcista
    else:
        direccion = 'bajista'
        probabilidad = prob_bajista
    
    # Normalizar la probabilidad basada en volatilidad del mercado
    # Alta volatilidad (ATR%) puede hacer reversiones más probables
    if atr_percent > 3:  # Alta volatilidad
        probabilidad *= 1.1
    elif atr_percent < 1:  # Baja volatilidad
        probabilidad *= 0.9
    
    probabilidad = min(probabilidad, 100)
    
    # Devolver factores detallados para análisis
    factores_contribuyentes = {
        'rsi': rsi_actual,
        'estocástico_k': stoch_k,
        'estocástico_d': stoch_d,
        'bb_width': bb_width,
        'bb_posicion': precio_vs_bb_lower if direccion == 'alcista' else precio_vs_bb_upper,
        'patrones_vela': hammer + piercing + morning_star if direccion == 'alcista' else hanging_man + shooting_star + evening_star,
        'divergencia': divergencia_alcista if direccion == 'alcista' else divergencia_bajista,
        'volumen_ratio': volumen_actual / volumen_promedio,
        'distancia_sr': distancia_a_min if direccion == 'alcista' else distancia_a_max,
        'adx': adx_actual,
        'atr_percent': atr_percent,
        'emas': {
            'ema20': tendencia_corto_alcista,
            'ema50': tendencia_medio_alcista,
            'ema200': tendencia_largo_alcista,
            'cruce_emas': cruce_emas
        },
        'macd': {
            'line': macd_actual,
            'signal': signal_actual,
            'hist': hist_actual
        },
        'tendencia_fuerza': adx_actual,
        'timeframe': timeframe
    }
    
    return probabilidad, direccion, factores_contribuyentes


def get_open_interest_binance(symbol="BTCUSDT", interval="5m", limit=6):
        """
        Obtiene el Open Interest de un símbolo en Binance para las últimas N velas en un intervalo específico.
        
        Parámetros:
        - symbol (str): Par de trading, por defecto "BTCUSDT"
        - interval (str): Intervalo de tiempo, por defecto "5m"
        - limit (int): Número de velas a obtener, por defecto 20
        
        Retorna:
        - pandas.DataFrame: DataFrame con el Open Interest y su timestamp
        """
        try:
            
            # Endpoint para obtener el Open Interest de Binance
            url = f"https://fapi.binance.com/fapi/v1/openInterest"
            
            # Obtener Open Interest histórico
            historical_url = f"https://fapi.binance.com/futures/data/openInterestHist"
            params = {
                "symbol": symbol,
                "period": interval,
                "limit": limit
            }
            
            response = requests.get(historical_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Convertir a DataFrame
                df = pd.DataFrame(data)
                
                # Convertir campos a tipos apropiados
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df['sumOpenInterest'] = df['sumOpenInterest'].astype(float)
                df['sumOpenInterestValue'] = df['sumOpenInterestValue'].astype(float)

                # Añadir datos de precio al DataFrame de Open Interest
                if 'timestamp' in df.columns:
                    # Endpoint para obtener datos OHLCV
                    klines_url = f"https://fapi.binance.com/fapi/v1/klines"
                    klines_params = {
                        "symbol": symbol,
                        "interval": interval,
                        "limit": limit
                    }
                    
                    klines_response = requests.get(klines_url, params=klines_params)
                    
                    if klines_response.status_code == 200:
                        klines_data = klines_response.json()
                        
                        # Crear DataFrame con datos OHLCV
                        klines_df = pd.DataFrame(klines_data, columns=[
                            'kline_open_time', 'open', 'high', 'low', 'close', 'volume',
                            'kline_close_time', 'quote_asset_volume', 'number_of_trades',
                            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
                        ])
                        
                        # Convertir a tipos apropiados
                        klines_df['kline_open_time'] = pd.to_datetime(klines_df['kline_open_time'], unit='ms')
                        klines_df['open'] = klines_df['open'].astype(float)
                        klines_df['high'] = klines_df['high'].astype(float)
                        klines_df['low'] = klines_df['low'].astype(float)
                        klines_df['close'] = klines_df['close'].astype(float)
                        klines_df['volume'] = klines_df['volume'].astype(float)
                        
                        # Alinear timestamps entre OI y OHLCV (aproximadamente)
                        df['kline_open_time'] = df['timestamp'].dt.floor('5min')
                        klines_df['timestamp_key'] = klines_df['kline_open_time']
                        
                        # Combinar DataFrames
                        df = pd.merge_asof(
                            df.sort_values('kline_open_time'), 
                            klines_df[['timestamp_key', 'close', 'volume']].sort_values('timestamp_key'),
                            left_on='kline_open_time',
                            right_on='timestamp_key',
                            direction='nearest'
                        )

                tend, porc,oi_value = analizar_tendencia_open_interest(df, periodo=limit)
                vtend, vporc, vol_value = analizar_tendencia_volumen(df, periodo=limit)
                tendencia, fuerza, cambio_porcentual,precio_actual = calcular_tendencia_precio(df, periodo=limit, metodo='ema')

                return df,tend, porc,vtend, vporc, tendencia, fuerza, cambio_porcentual,precio_actual,oi_value,vol_value
            else:
                print(f"Error al obtener datos: {response.status_code}")
                print(response.text)
                return None,None, None,None,None,None,None,None,None,None,None
            
        except Exception as e:
            print(f"Error en la solicitud: {e}")
            return None,None, None,None,None,None,None,None,None,None,None


def analizar_viariacion_open_interest(df_oi, periodo=5):
    """
    Analiza la tendencia del open interest para determinar si es alcista o bajista.
    
    Parámetros:
    - df_oi: DataFrame con los datos de open interest (debe contener la columna 'sumOpenInterest')
    - periodo: Número de periodos para calcular la tendencia (por defecto 5)
    
    Retorna:
    - str: 'alcista', 'bajista' o 'neutral'
    - float: Porcentaje de cambio en el periodo analizado
    """
    if df_oi is None or len(df_oi) < periodo:
        return 0
    
    # Asegurarse que los datos estén ordenados por timestamp (ascendente)
    df_sorted = df_oi.sort_values('timestamp')
    
    # Calcular la media móvil para suavizar la tendencia
    df_sorted['oi_sma'] = df_sorted['sumOpenInterest'].rolling(window=min(3, len(df_sorted))).mean()
    
    # Llenar NaN con el primer valor válido
    df_sorted['oi_sma'] = df_sorted['oi_sma'].fillna(df_sorted['sumOpenInterest'])
    
    # Obtener los valores recientes para comparar
    recent_oi = df_sorted['sumOpenInterest'].iloc[-periodo:].values
    
    # Calcular el porcentaje de cambio
    cambio_porcentual = ((recent_oi[-3] - recent_oi[0]) / recent_oi[0]) * 100
    return cambio_porcentual,recent_oi[-3],recent_oi[0]


def analizar_tendencia_open_interest(df_oi, periodo=5):
    """
    Analiza la tendencia del open interest para determinar si es alcista o bajista.
    
    Parámetros:
    - df_oi: DataFrame con los datos de open interest (debe contener la columna 'sumOpenInterest')
    - periodo: Número de periodos para calcular la tendencia (por defecto 5)
    
    Retorna:
    - str: 'alcista', 'bajista' o 'neutral'
    - float: Porcentaje de cambio en el periodo analizado
    """
    if df_oi is None or len(df_oi) < periodo:
        return "neutral", 0
    
    # Asegurarse que los datos estén ordenados por timestamp (ascendente)
    df_sorted = df_oi.sort_values('timestamp')
    
    # Calcular la media móvil para suavizar la tendencia
    df_sorted['oi_sma'] = df_sorted['sumOpenInterest'].rolling(window=min(3, len(df_sorted))).mean()
    
    # Llenar NaN con el primer valor válido
    df_sorted['oi_sma'] = df_sorted['oi_sma'].fillna(df_sorted['sumOpenInterest'])
    
    # Obtener los valores recientes para comparar
    recent_oi = df_sorted['oi_sma'].iloc[-periodo:].values
    
    # Calcular el porcentaje de cambio
    cambio_porcentual = ((recent_oi[-1] - recent_oi[0]) / recent_oi[0]) * 100
    
    # Calcular pendiente de la tendencia usando regresión lineal
    x = np.arange(len(recent_oi))
    pendiente = np.polyfit(x, recent_oi, 1)[0]
    
    # Determinar la fuerza de la tendencia
    if abs(cambio_porcentual) < 1.0:
        return "neutral", cambio_porcentual, recent_oi[0]
    elif pendiente > 0:
        return "alza", cambio_porcentual, recent_oi[0]
    else:
        return "baja", cambio_porcentual, recent_oi[0]


def analizar_tendencia_volumen(df, periodo=5):
            """
            Analiza la tendencia del volumen para determinar si está en alza o baja.
            
            Parámetros:
            - df: DataFrame con los datos de volumen (debe contener la columna 'volume')
            - periodo: Número de periodos para calcular la tendencia (por defecto 5)
            
            Retorna:
            - str: 'alza', 'baja' o 'neutral'
            - float: Porcentaje de cambio en el periodo analizado
            """
            if df is None or len(df) < periodo:
                return "neutral", 0
            
            # Asegurarse que los datos estén ordenados por timestamp (ascendente)
            if 'timestamp' in df.columns:
                df_sorted = df.sort_values('timestamp')
            else:
                # Si no hay columna timestamp, asumir que los datos ya están ordenados
                df_sorted = df.copy()
            
            # Calcular la media móvil para suavizar la tendencia
            df_sorted['vol_sma'] = df_sorted['volume'].rolling(window=min(3, len(df_sorted))).mean()
            
            # Llenar NaN con el primer valor válido
            df_sorted['vol_sma'] = df_sorted['vol_sma'].fillna(df_sorted['volume'])
            
            # Obtener los valores recientes para comparar
            recent_vol = df_sorted['vol_sma'].iloc[-periodo:].values
            
            # Calcular el porcentaje de cambio
            cambio_porcentual = ((recent_vol[-1] - recent_vol[0]) / recent_vol[0]) * 100
            
            # Calcular pendiente de la tendencia usando regresión lineal
            x = np.arange(len(recent_vol))
            pendiente = np.polyfit(x, recent_vol, 1)[0]
            
            # Determinar la fuerza de la tendencia
            if abs(cambio_porcentual) < 5.0:  # Los volúmenes suelen tener más variabilidad
                return "neutral", cambio_porcentual,recent_vol[0]
            elif pendiente > 0:
                return "alza", cambio_porcentual,recent_vol[0]
            else:
                return "baja", cambio_porcentual,recent_vol[0]


def calcular_tendencia_precio(df, periodo=14, metodo='sma'):
                    """
                    Calcula la tendencia del precio basada en las medias móviles o regresión lineal.
                    
                    Parámetros:
                    - df: DataFrame con la columna 'close'
                    - periodo: Número de periodos para calcular la tendencia
                    - metodo: 'sma' para media móvil simple, 'ema' para media móvil exponencial, 
                              'regresion' para regresión lineal
                    
                    Retorna:
                    - tendencia: 'alcista', 'bajista' o 'neutral'
                    - fuerza: valor numérico indicando la fuerza de la tendencia
                    - porcentaje: cambio porcentual en el periodo analizado
                    """
                    if len(df) < periodo:
                        return "neutral", 0, 0
                    
                    # Obtener los precios de cierre
                    close_prices = df['close'].values
                    
                    if metodo == 'sma':
                        # Calcular la media móvil simple
                        sma = talib.SMA(close_prices, timeperiod=periodo)
                        precio_actual = close_prices[-1]
                        sma_actual = sma[-1]
                        sma_anterior = sma[-2]
                        
                        # Determinar tendencia basada en posición del precio respecto a SMA
                        if precio_actual > sma_actual and sma_actual > sma_anterior:
                            tendencia = "alcista"
                        elif precio_actual < sma_actual and sma_actual < sma_anterior:
                            tendencia = "bajista"
                        else:
                            tendencia = "neutral"
                        
                        # Calcular la fuerza como distancia del precio a la media en porcentaje
                        fuerza = abs((precio_actual - sma_actual) / sma_actual * 100)
                        
                    elif metodo == 'ema':
                        # Calcular la media móvil exponencial
                        ema = talib.EMA(close_prices, timeperiod=periodo)
                        precio_actual = close_prices[-1]
                        ema_actual = ema[-1]
                        ema_anterior = ema[-2]
                        
                        # Determinar tendencia basada en posición del precio respecto a EMA
                        if precio_actual > ema_actual and ema_actual > ema_anterior:
                            tendencia = "alcista"
                        elif precio_actual < ema_actual and ema_actual < ema_anterior:
                            tendencia = "bajista"
                        else:
                            tendencia = "neutral"
                        
                        # Calcular la fuerza como distancia del precio a la media en porcentaje
                        fuerza = abs((precio_actual - ema_actual) / ema_actual * 100)
                        
                    elif metodo == 'regresion':
                        # Calcular regresión lineal para determinar la pendiente
                        x = np.arange(periodo)
                        y = close_prices[-periodo:]
                        pendiente, _, _, _, _ = talib.LINEARREG(close_prices, timeperiod=periodo)
                        
                        # Normalizar la pendiente respecto al precio promedio para hacerla comparable
                        precio_promedio = np.mean(y)
                        pendiente_normalizada = pendiente[-1] / precio_promedio * 100
                        
                        # Determinar tendencia basada en la pendiente
                        if pendiente_normalizada > 0.1:
                            tendencia = "alcista"
                        elif pendiente_normalizada < -0.1:
                            tendencia = "bajista"
                        else:
                            tendencia = "neutral"
                        
                        # La fuerza es el valor absoluto de la pendiente normalizada
                        fuerza = abs(pendiente_normalizada)
                    
                    # Calcular el cambio porcentual en el periodo
                    cambio_porcentual = ((close_prices[-1] - close_prices[-periodo]) / close_prices[-periodo]) * 100
                    
                    return tendencia, fuerza, cambio_porcentual,precio_actual


def get_oi(symbol="BTCUSDT", interval="5m", limit=6):
    """
    Obtiene el Open Interest de un símbolo en Binance para las últimas N velas en un intervalo específico.
    
    Parámetros:
    - symbol (str): Par de trading, por defecto "BTCUSDT"
    - interval (str): Intervalo de tiempo, por defecto "5m"
    - limit (int): Número de velas a obtener, por defecto 20
    
    Retorna:
    - pandas.DataFrame: DataFrame con el Open Interest y su timestamp
    """
    try:
        # Endpoint para obtener el Open Interest de Binance
        url = f"https://fapi.binance.com/futures/data/openInterestHist"
        
        # Obtener Open Interest histórico
        params = {
            "symbol": symbol,
            "period": interval,
            "limit": limit
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            # Convertir a DataFrame
            df = pd.DataFrame(data)
            
            # Convertir campos a tipos apropiados
            df['open_interest'] = df['sumOpenInterestValue'].astype(float)
            
            return df
        else:
            print(f"{symbol} Error al obtener datos: {response.status_code}")
            print(response.text)
            return None
        
    except Exception as e:
        print(f"{symbol} Error en la solicitud: {e}")
        return None

def check_rising_oi(df, symbol, periods=5):
    """
    Verifica si el Open Interest ha subido en los últimos 'periods' registros.
    """
    if df is None or len(df) < periods:
        return False

    df_symbol = df.copy()
    df_symbol["oi_change"] = df_symbol["open_interest"].diff()
    
    # Filtrar últimos 'periods' registros
    last_changes = df_symbol["oi_change"].iloc[-periods:]
    
    # Si todas las diferencias son positivas, enviar alerta
    if all(last_changes > 0):
        print(f"🔔 Alerta: Open Interest de {symbol} ha subido en los últimos {periods} períodos consecutivos.")
        return True
    return False



def get_variacion_open_interest_binance(symbol="BTCUSDT", interval="5m", limit=6):
        """
        Obtiene el Open Interest de un símbolo en Binance para las últimas N velas en un intervalo específico.
        
        Parámetros:
        - symbol (str): Par de trading, por defecto "BTCUSDT"
        - interval (str): Intervalo de tiempo, por defecto "5m"
        - limit (int): Número de velas a obtener, por defecto 20
        
        Retorna:
        - pandas.DataFrame: DataFrame con el Open Interest y su timestamp
        """
        try:
            
            # Endpoint para obtener el Open Interest de Binance
            url = f"https://fapi.binance.com/fapi/v1/openInterest"
            
            # Obtener Open Interest histórico
            historical_url = f"https://fapi.binance.com/futures/data/openInterestHist"
            params = {
                "symbol": symbol,
                "period": interval,
                "limit": limit
            }
            
            response = requests.get(historical_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Convertir a DataFrame
                df = pd.DataFrame(data)
                
                # Convertir campos a tipos apropiados
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df['sumOpenInterest'] = df['sumOpenInterest'].astype(float)
                df['sumOpenInterestValue'] = df['sumOpenInterestValue'].astype(float)


                variacion, h, l= analizar_viariacion_open_interest(df, periodo=limit)

                return variacion,h,l
            else:
                print(f"Error al obtener datos: {response.status_code}")
                print(response.text)
                return None, None, None
            
        except Exception as e:
            return None, None, None

