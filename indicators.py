import pandas as pd
from dotenv import load_dotenv
import numpy as np
import talib

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
        ema = data.ewm(span=ventana, adjust=False).mean()
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