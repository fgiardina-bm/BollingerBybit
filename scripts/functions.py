import os
from pybit.unified_trading import HTTP
import pandas as pd
from dotenv import load_dotenv
import time
import math
import random
from decimal import Decimal, ROUND_DOWN, ROUND_FLOOR
from concurrent.futures import ThreadPoolExecutor
from config import *
from indicators import *
from oscillator import *
import threading
import numpy as np
import matplotlib
# Configuración para entorno headless (sin interfaz gráfica) como Docker
matplotlib.use('Agg')  # Debe ejecutarse antes de importar pyplot
import matplotlib.pyplot as plt
from datetime import datetime
import argparse
import logging
from typing import Tuple, List, Optional, Dict, Any
import os
import ccxt

client = HTTP(api_key=api_key, api_secret=api_secret, testnet=False)

def obtener_orderbook(symbol):
    response = client.get_orderbook(category="linear", symbol=symbol)
    if response["retCode"] == 0:
        orderbook = response["result"]
        return orderbook
    else:
        logger("Error en la API:" + response["retMsg"])
        return None

def obtener_datos_historicos(symbol, interval, limite=200):
    response = client.get_kline(category="linear",symbol=symbol, interval=interval, limite=limite)
    if "result" in response:
        data = pd.DataFrame(response['result']['list']).astype(float)
        data[0] = pd.to_datetime(data[0], unit='ms')
        data.set_index(0, inplace=True)
        data = data[::-1].reset_index(drop=True)
        return data
    else:
        raise Exception("Error al obtener datos historicos: " + str(response))


def obtener_datos_historicos_binance(symbol, timeframe, limite=200):
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

        # Obtener datos OHLCV
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limite)

        # Convertir a DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')  # Convertir timestamp a datetime
        df.set_index('timestamp', inplace=True)  # Establecer timestamp como índice

        return df

    except Exception as e:
        print(f"Error al obtener datos históricos de Binance: {e}")
        return None

def buscar_precios_otros_simbolos(simbolos):
    while True:
        for s in simbolos:
            try:
                precio = client.get_tickers(category='linear', symbol=s)
                precio = float(precio['result']['list'][0]['lastPrice'])
                logger(f"Precio actual de {s}: {precio:.4f}")
            except Exception as e:
                logger(f"Error al obtener precio de {s}: {e}")

        time.sleep(10)  # Esperar 60 segundos antes de la próxima búsqueda

def obtener_simbolos_mayor_volumen(cnt=10):
    global black_list_symbols
    try:
        tickers = client.get_tickers(category='linear')
        if tickers["retCode"] == 0:
            # Filtrar solo los símbolos que terminan en "USDT"
            usdt_tickers = [ticker for ticker in tickers['result']['list'] if ticker['symbol'].endswith('USDT')]
            # Ordenar por volumen en las últimas 24 horas y obtener los 10 primeros
            usdt_tickers.sort(key=lambda x: float(x['turnover24h']), reverse=True)
            top_10_simbolos = [ticker['symbol'] for ticker in usdt_tickers[:cnt]]
            
            # Mostrar el volumen de cada símbolo
            for ticker in usdt_tickers[:cnt]:
                logger(f"Símbolo: {ticker['symbol']} Volumen: {float(ticker['turnover24h']) / 1000000:.2f} M")
            
            # Remover los símbolos que están en la lista negra
            top_10_simbolos = [symbol for symbol in top_10_simbolos if symbol not in black_list_symbols]
            return top_10_simbolos
        else:
            logger("Error en la API:" + tickers["retMsg"])
            return []
    except Exception as e:
        logger(f"Error al obtener los símbolos con mayor volumen: {e}")
        return []

def obtener_simbolos_mayor_volumen_binance(cnt=10):
    """
    Obtiene los símbolos con mayor volumen en Binance.
    
    Args:
        cnt (int): Número de símbolos a obtener (default: 10)
        
    Returns:
        list: Lista de símbolos con mayor volumen
    """
    global black_list_symbols
    
    try:
        # Inicializar el cliente de Binance (asumiendo que ya está importado)
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}  # Para usar el mercado de futuros
        })
        
        # Obtener todos los tickers
        tickers = exchange.fetch_tickers()

        usdt_tickers = []
        for i, (symbol, data) in enumerate(list(tickers.items())):
            if symbol.endswith('USDT'):
                item = {
                    "symbol":data['info']['symbol'],
                    "quoteVolume": data['info']['quoteVolume'],
                    "priceChangePercent": data['info']['priceChangePercent']
                }
                usdt_tickers.append(item)


        # Ordenar la lista por quoteVolume de mayor a menor
        sorted_data = sorted(usdt_tickers, key=lambda x: float(x['quoteVolume']), reverse=True)

        # Obtener los top símbolos
        top_simbolos = []
        # Extract symbols from the top entries based on volume
        for item in sorted_data[:cnt]:
            top_simbolos.append(item['symbol'])
            
            # Log the symbols with their volume for reference
            logger(f"Símbolo: {item['symbol']} Volumen: {float(item['quoteVolume']) / 1000000:.2f} M")
        
        get_btc_price_change_ticker()

        # Remover los símbolos que están en la lista negra
        top_simbolos = [symbol for symbol in top_simbolos if symbol not in black_list_symbols]
        return top_simbolos
    
    except Exception as e:
        logger(f"Error al obtener los símbolos con mayor volumen en Binance: {e}")
        return []

def obtener_simbolos_mayor_open_interest(cnt=10):
    try:
        tickers = client.get_tickers(category='linear')
        if tickers["retCode"] == 0:
            # Filtrar solo los símbolos que terminan en "USDT"
            usdt_tickers = [ticker for ticker in tickers['result']['list'] if ticker['symbol'].endswith('USDT')]
            # Ordenar por open interest y obtener los 10 primeros
            usdt_tickers.sort(key=lambda x: float(x['openInterest']), reverse=True)
            top_10_simbolos = [ticker['symbol'] for ticker in usdt_tickers[:cnt]]
            
            # Mostrar el open interest de cada símbolo
            for ticker in usdt_tickers[:cnt]:
                logger(f"Símbolo: {ticker['symbol']} Open Interest: {ticker['openInterest']}")
            
            return top_10_simbolos
        else:
            logger("Error en la API:"+ tickers["retMsg"])
            return []
    except Exception as e:
        logger(f"Error al obtener los símbolos con mayor open interest: {e}")
        return []

def obtener_saldo_usdt():
    try:
        balance = client.get_wallet_balance(accountType="UNIFIED", coin="USDT")
        if balance["retCode"] == 0:
            saldo_usdt = float(balance['result']['list'][0]['totalAvailableBalance'])
            return saldo_usdt
        else:
            logger("Error en la API:"+ balance["retMsg"])
            return 0.0
    except Exception as e:
        logger(f"Error al obtener el saldo en USDT: {e}")
        return 0.0

def verificar_posicion_abierta(symbol):
    retries = 3
    while retries > 0:
        try:
            posiciones = client.get_positions(category="linear", symbol=symbol)
            if posiciones["retCode"] == 0:
                for posicion in posiciones['result']['list']:
                    if float(posicion['size']) > 0:
                        stop_loss = posicion.get('stopLoss')
                        take_profit = posicion.get('takeProfit')
                        if stop_loss and take_profit:
                            return True
                        else:
                            return False

                return False
            else:
                logger("Error en la API:"+ posiciones["retMsg"])
                return False
        except Exception as e:
            logger(f"Error al verificar la posición abierta en {symbol}: {e}")
            retries -= 1
            if retries == 0:
                return False
            time.sleep(1)


def verificar_posicion_abierta_solo_stop_loss(symbol):
    retries = 3
    while retries > 0:
        try:
            posiciones = client.get_positions(category="linear", symbol=symbol)
            if posiciones["retCode"] == 0:
                for posicion in posiciones['result']['list']:
                    if float(posicion['size']) > 0:
                        stop_loss = posicion.get('stopLoss')
                        # take_profit = posicion.get('takeProfit')
                        if stop_loss:
                            return True
                        else:
                            return False

                return False
            else:
                logger("Error en la API:"+ posiciones["retMsg"])
                return False
        except Exception as e:
            logger(f"Error al verificar la posición abierta en {symbol}: {e}")
            retries -= 1
            if retries == 0:
                return False
            time.sleep(1)


def verificar_posicion_abierta_details(symbol):
    try:
        posiciones = client.get_positions(category="linear", symbol=symbol)
        return posiciones
    except Exception as e:
        logger(f"Error al verificar la posición abierta en {symbol}: {e}")

def get_bybit_kline(symbol, interval=timeframe, limit=100):
    response = client.get_kline(
        category="linear",
        symbol=symbol,
        interval=interval,
        limit=limit
    )
    
    if response["retCode"] == 0:
        kline = response["result"]["list"]
        closes = [float(candle[4]) for candle in kline]
        return pd.Series(closes[::-1])
    else:
        logger("Error en la API:"+ response["retMsg"])
        return None

def qty_precision(qty, precision):
    logger(f"analizar_posible_orden qty_precision: {qty} - {precision}")
    qty = math.floor(qty / precision) * precision
    logger(f"analizar_posible_orden qty_precision2: {qty} - {precision}")
    return float(f"{qty:.4f}")

def qty_step(price, symbol):
    step = client.get_instruments_info(category="linear", symbol=symbol)
    ticksize = float(step['result']['list'][0]['priceFilter']['tickSize'])
    scala_precio = int(step['result']['list'][0]["priceScale"])

    precision = Decimal(f"{10 ** scala_precio}")
    tickdec = Decimal(f"{ticksize}")
    precio_final = (Decimal(f"{price}") * precision) / precision
    precide = precio_final.quantize(Decimal(f"{1 / precision}"), rounding=ROUND_FLOOR)
    operaciondec = (precide / tickdec).quantize(Decimal('1'), rounding=ROUND_FLOOR) * tickdec
    result = float(operaciondec)

    return result

def crear_orden(symbol, side, order_type, qty):
    global test_mode
    try:
        if test_mode == 0:
            response = client.place_order(
                category="linear",
                symbol=symbol,
                side=side,
                orderType=order_type,
                qty=qty,
                timeInForce="GoodTillCancel"
            )
            logger(f"{test_mode} Orden creada con exito: {str(response)}")
        else:
            logger(f"Test mode activado. No se creará la orden en symbol: {symbol}, side: {side}, order_type: {order_type}, qty: {qty}")

            # time.sleep(1)
            # establecer_st_tp(symbol)

    except Exception as e:
        logger(f"{test_mode} Error al crear la orden: {e}")

def crear_orden_con_stoploss_takeprofit(symbol, side, order_type, qty, sl, tp):
    """
    Crear una orden con stop-loss y take-profit configurados directamente.
    
    Args:
        symbol (str): Símbolo del par de trading
        side (str): 'Buy' o 'Sell'
        order_type (str): Tipo de orden ('Market', 'Limit', etc.)
        qty (float): Cantidad a operar
        sl (float): Precio del stop-loss
        tp (float): Precio del take-profit
    
    Returns:
        dict/None: Respuesta de la API o None si está en modo de prueba
    """
    global test_mode
    try:
        sl_price = qty_step(sl, symbol)
        tp_price = qty_step(tp, symbol)
        
        if test_mode == 0:
            response = client.place_order(
                category="linear",
                symbol=symbol,
                side=side,
                orderType=order_type,
                qty=qty,
                timeInForce="GoodTillCancel",
                stopLoss=sl_price,
                takeProfit=tp_price
            )
            logger(f"{test_mode} Orden creada con SL/TP con éxito: {str(response)}")
            return response
        else:
            logger(f"Test mode activado. No se creará la orden con SL/TP en symbol: {symbol}, side: {side}, qty: {qty}, SL: {sl_price}, TP: {tp_price}")
            return None

    except Exception as e:
        logger(f"{test_mode} Error al crear la orden con SL/TP: {e}")
        return None

def establecer_st_tp(symbol):
    global test_mode

    limit = 10
    while True:
        limit -= 1
        try:
            posiciones = client.get_positions(category="linear", symbol=symbol)
            if float(posiciones['result']['list'][0]['size']) != 0:
                if not verificar_posicion_abierta(symbol):
                    precio_de_entrada = float(posiciones['result']['list'][0]['avgPrice'])
                    if posiciones['result']['list'][0]['side']  == 'Buy':
                        stop_loss_price = precio_de_entrada * (1 - sl_porcent / 100)
                        take_profit_price = precio_de_entrada * (1 + tp_porcent / 100)
                        result_sl = establecer_stop_loss(symbol, stop_loss_price)
                        result_tp = establecer_take_profit(symbol,take_profit_price, "Sell")
                        if result_sl and result_tp:
                            logger(f"{symbol} Stop loss y take profit activados")
                        
                    else:
                        stop_loss_price = precio_de_entrada * (1 + sl_porcent / 100)
                        take_profit_price = precio_de_entrada * (1 - tp_porcent / 100)
                        result_sl = establecer_stop_loss(symbol, stop_loss_price)
                        result_tp = establecer_take_profit(symbol, take_profit_price, "Buy")
                        if result_sl and result_tp:
                            logger(f"{symbol} {limit} Stop loss y take profit activados")

                    break
        except Exception as e:
            logger(f"{test_mode} {symbol} {limit} Error al establecer stop loss y take profit: {e}")                   

        if limit == 0:
            break

def establecer_stop_loss(symbol, sl):
    global test_mode
    try:
        sl = qty_step(sl,symbol)

        if test_mode == 1:
            logger(f"Test mode activado. No se establecerá el stop loss en {symbol} en {sl}")
            return None

        order = client.set_trading_stop(
            category="linear",
            symbol=symbol,
            stopLoss=sl,
            slTriggerB="LastPrice",
            positionIdx=0
        )
  
        logger(f"{symbol} Stop loss establecido en {sl}")
        return order
    except Exception as e:
        logger(f"{test_mode} {symbol} Error al establecer el stop loss: {e}")
        return None

def establecer_take_profit(symbol, tp, side):
    global test_mode
    
    datam = obtener_datos_historicos(symbol, timeframe)
    ema_20 = calcular_ema(datam[4], ventana=20)

    price_tp = qty_step(tp,symbol)
    price = qty_step(ema_20,symbol)

    if side == "Buy":
        if price < price_tp:
            price = price_tp
    else:
        if price > price_tp:
            price = price_tp

    try:
        if test_mode == 1:
            logger(f"Test mode activado. No se establecerá el take profit en {symbol} en {price}")
            return None

        # Establecer el take profit en la posición
        order = client.set_trading_stop(
            category="linear",
            symbol=symbol,
            takeProfit=price,
            tpTriggerBy="LastPrice",
            positionIdx=0
        )

        logger(f"{symbol} Take profit establecido a {price}")
        return order
    except Exception as e:
        logger(f"{test_mode} {symbol} Error al establecer el take profit: {e}")
        return None



def establecer_stop_loss2(symbol, sl):
    global test_mode
    try:
        sl = qty_step(sl,symbol)

        if test_mode == 1:
            logger(f"Test mode activado. No se establecerá el stop loss en {symbol} en {sl}")
            return None

        order = client.set_trading_stop(
            category="linear",
            symbol=symbol,
            stopLoss=sl,
            slTriggerB="LastPrice",
            positionIdx=0
        )
  
        logger(f"{symbol} Stop loss establecido en {sl}")
        return order
    except Exception as e:
        logger(f"{test_mode} {symbol} Error al establecer el stop loss: {e}")
        return None

def establecer_take_profit2(symbol, tp, side):
    global test_mode
    price_tp = qty_step(tp,symbol)

    try:
        if test_mode == 1:
            logger(f"Test mode activado. No se establecerá el take profit2 en {symbol} en {price_tp}")
            return None

        # Establecer el take profit en la posición
        order = client.set_trading_stop(
            category="linear",
            symbol=symbol,
            takeProfit=price_tp,
            tpTriggerBy="LastPrice",
            positionIdx=0
        )

        logger(f"{symbol} Take profit establecido a {price_tp}")
        return order
    except Exception as e:
        logger(f"{test_mode} {symbol} Error al establecer el take profit: {e}")
        return None


def establecer_trailing_stop(symbol, tp, side, qty, callback_ratio=1):
    global test_mode

    datam = obtener_datos_historicos(symbol, timeframe)
    ema_20 = calcular_ema(datam[4], ventana=20)

    price_tp = qty_step(tp,symbol)
    trigger_price = qty_step(ema_20,symbol)

    if side == "Buy":
        if trigger_price < price_tp:
            trigger_price = price_tp
    else:
        if trigger_price > price_tp:
            trigger_price = price_tp

    try:
        if test_mode == 1:
            logger(f"Test mode activado. No se establecerá el trailing stop en {symbol} en {trigger_price}")
            return None

        # Establecer el take profit en la posición
        order = client.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            orderType="TrailingStopMarket",
            qty=qty,
            triggerPrice=trigger_price,  # 🔥 Se activa cuando el precio llega aquí
            triggerBy="LastPrice",  # Puedes cambiarlo a "MarkPrice" o "IndexPrice"
            callbackRatio=callback_ratio,  # 🔥 Ratio de trailing stop (1% en este caso)
            reduceOnly=True
        )


        logger(f"{test_mode} Trailing stop establecido para {symbol} a {trigger_price}")
        return order
    except Exception as e:
        logger(f"{test_mode} Error al establecer el trailing stop para {symbol}: {e}")
        return None


def check_opened_positions(opened_positions):
    while True:
        print()
        print(f" ----------------------------- Posiciones abiertas: {opened_positions} ----------------------------- ")
        print()
        time.sleep(60)

def analizar_posible_orden(symbol, side, order_type, qty, bollinger_init_data, rsi_init_data):
    global test_mode

    rsi = rsi_init_data
    max_min_rsi = rsi_init_data

    while True:
        try:
            logger(f"{test_mode} analizar_posible_orden en {symbol} - {side} - {order_type} - {qty} - {bollinger_init_data['UpperBand']} -  {bollinger_init_data['LowerBand']} -  {bollinger_init_data['MA']} -  {bollinger_init_data['BB_Width_%']} - RSI INICIAL: {rsi_init_data} - RSI ACTUAL{(rsi)}")
            if not verificar_posicion_abierta(symbol):
                logger(f"{test_mode} analizar_posible_orden en {symbol} - No hay posiciones abiertas en {symbol}")
                datam = obtener_datos_historicos(symbol, timeframe)
                bollinger = calcular_bandas_bollinger(datam)
                rsi = calcular_rsi_talib(datam[4])

                bb_width = bollinger['BB_Width_%']
                if bb_width < Bollinger_bands_width:
                    logger(f"{test_mode} analizar_posible_orden en {symbol} - bb_width {bb_width} - Bollinger_bands_width {Bollinger_bands_width}")
                    time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                    continue;
                    
                if rsi > 45 and rsi < 55:
                    logger(f"{test_mode} analizar_posible_orden en {symbol} - RSI en instancias medias {rsi} salgo del analisis.")
                    break

                if side == "Sell": # bollineger y RSI altos
                    if rsi > max_min_rsi:
                        max_min_rsi = rsi

                    rsi_limit = float(rsi) + float(verify_rsi)
                    if (bollinger['UpperBand'] < bollinger_init_data['UpperBand']) or (rsi_limit < max_min_rsi):
                        actual_bb = bollinger['LowerBand']
                        inicial_bb = bollinger_init_data['LowerBand']
                        logger(f"{test_mode} analizar_posible_orden en {symbol} - Creando orden en {symbol} - {side} - {order_type} - {qty} - rsi {rsi} - rsi_limit {rsi_limit} - rsi_init_data {rsi_init_data} - actual_bb {actual_bb} - inicial_bb {inicial_bb}")
                        crear_orden(symbol, side, order_type, qty)

                        if monitoring == 1:
                            # Iniciar el monitoreo de la operación
                            precio_entrada = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                            hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_entrada, side, qty))
                            hilo_monitoreo.start()

                        break
                    else:
                        logger(f"{test_mode} analizar_posible_orden en {symbol} - SELL RSI en {symbol} rsi_limit: {rsi_limit} es mayor a max_min_rsi: {max_min_rsi} - rsi_init_data: {rsi_init_data} - Actual UB: {bollinger['UpperBand']} - Inicial UB: {bollinger_init_data['UpperBand']}")

                else:

                    if rsi < max_min_rsi:
                        max_min_rsi = rsi

                    rsi_limit = float(rsi) - float(verify_rsi)
                    if (bollinger['LowerBand'] > bollinger_init_data['LowerBand']) or (rsi_limit > max_min_rsi):
                        actual_bb = bollinger['LowerBand']
                        inicial_bb = bollinger_init_data['LowerBand']
                        logger(f"analizar_posible_orden en {symbol} - Creando orden en {symbol} - {side} - {order_type} - {qty}  - rsi {rsi} - verify_rsi {verify_rsi} - rsi_init_data {rsi_init_data} - actual_bb {actual_bb} - inicial_bb {inicial_bb}")
                        crear_orden(symbol, side, order_type, qty)
                        if monitoring == 1:
                            # Iniciar el monitoreo de la operación
                            precio_entrada = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                            hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_entrada, side, qty))
                            hilo_monitoreo.start()
                            
                        break
                    else:
                       logger(f"analizar_posible_orden en {symbol} - BUY RSI en {symbol} rsi_limit: {rsi_limit} es menor a max_min_rsi: {max_min_rsi} - rsi_init_data: {rsi_init_data} - Actual LB: {bollinger['LowerBand']} - Inicial LB: {bollinger_init_data['LowerBand']}")

            else:
                logger(f"{test_mode} analizar_posible_orden en {symbol} - Ya hay una posición abierta en {symbol}")
                break
        except Exception as e:
            logger(f"{test_mode} analizar_posible_orden en {symbol} - Error al analizar posible orden en {symbol}: {e}")
            break

        time.sleep(20)

def analizar_posible_orden_macd_syr(symbol, side, order_type, qty, bollinger_init_data, rsi_init_data):
    global test_mode

    rsi = rsi_init_data
    max_min_rsi = rsi_init_data

    soportes, resistencias, valor_actual = get_soportes_resistencia(symbol)

    for soporte in soportes:
        porcentaje = ((valor_actual - soporte) / soporte) * 100
        logger(f"{symbol} {valor_actual:.5f} | Soporte {soporte} | Porcentaje {porcentaje:.2f}%")

    for resistencia in resistencias:
        porcentaje = ((resistencia - valor_actual) / valor_actual) * 100
        logger(f"{symbol} {valor_actual:.5f} | Resistencia {resistencia} | Porcentaje {porcentaje:.2f}%")


    while True:
        try:
            logger(f"analizar_posible_orden en {symbol} - {side} - {order_type} - {qty} - {bollinger_init_data['UpperBand']} -  {bollinger_init_data['LowerBand']} -  {bollinger_init_data['MA']} -  {bollinger_init_data['BB_Width_%']} - RSI INICIAL: {rsi_init_data} - RSI ACTUAL{(rsi)}")
            if not verificar_posicion_abierta(symbol):
                logger(f"analizar_posible_orden en {symbol} - No hay posiciones abiertas en {symbol}")
                datam = obtener_datos_historicos(symbol, timeframe)
                bollinger = calcular_bandas_bollinger(datam)
                rsi = calcular_rsi_talib(datam[4])

                bb_width = bollinger['BB_Width_%']
                if bb_width < Bollinger_bands_width:
                    logger(f"analizar_posible_orden en {symbol} - bb_width {bb_width} - Bollinger_bands_width {Bollinger_bands_width}")
                    time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                    continue;
                    
                if rsi > 45 and rsi < 55:
                    logger(f"analizar_posible_orden en {symbol} - RSI en instancias medias {rsi} salgo del analisis.")
                    break

                if side == "Sell": # bollineger y RSI altos
                    if rsi > max_min_rsi:
                        max_min_rsi = rsi

                    rsi_limit = float(rsi) + float(verify_rsi)

                    # si macd da senal bajista entrol
                    if macd_bajista(np.array(datam[4])):
                        logger(f"{test_mode} analizar_posible_orden en {symbol} - Creando orden en {symbol} - {side} - {order_type} - {qty}")
                        crear_orden(symbol, side, order_type, qty)

                        if monitoring == 1:
                            # Iniciar el monitoreo de la operación
                            precio_entrada = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                            hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_entrada, side, qty))
                            hilo_monitoreo.start()

                        break
                    else:
                        logger(f"{test_mode} analizar_posible_orden en {symbol} - SELL RSI en {symbol} rsi_limit: {rsi_limit} es mayor a max_min_rsi: {max_min_rsi} - rsi_init_data: {rsi_init_data} - Actual UB: {bollinger['UpperBand']} - Inicial UB: {bollinger_init_data['UpperBand']}")

                else:

                    if rsi < max_min_rsi:
                        max_min_rsi = rsi

                    rsi_limit = float(rsi) - float(verify_rsi)
                    if macd_alcista(np.array(datam[4])):
                        logger(f"analizar_posible_orden en {symbol} - Creando orden en {symbol} - {side} - {order_type} - {qty}")
                        crear_orden(symbol, side, order_type, qty)
                        if monitoring == 1:
                            # Iniciar el monitoreo de la operación
                            precio_entrada = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                            hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abierta_macd_syr, args=(symbol, precio_entrada, side, qty))
                            hilo_monitoreo.start()
                            
                        break
                    else:
                       logger(f"analizar_posible_orden en {symbol} - BUY RSI en {symbol} rsi_limit: {rsi_limit} es menor a max_min_rsi: {max_min_rsi} - rsi_init_data: {rsi_init_data} - Actual LB: {bollinger['LowerBand']} - Inicial LB: {bollinger_init_data['LowerBand']}")

            else:
                logger(f"analizar_posible_orden en {symbol} - Ya hay una posición abierta en {symbol}")
                break
        except Exception as e:
            logger(f"analizar_posible_orden en {symbol} - Error al analizar posible orden en {symbol}: {e}")
            break

        time.sleep(20)


def analizar_posible_orden_patron_velas(symbol, side, order_type, qty, bollinger_init_data, rsi_init_data):
    global opened_positions, monitoring, test_mode

    rsi = rsi_init_data

    while True:
        try:
            if len(opened_positions) >= max_ops:
                logger(f"{test_mode} analizar_posible_orden - Se alcanzó el límite de posiciones abiertas | {max_ops}.")
                break
            
            logger(f"analizar_posible_orden en {symbol} - {side} - {order_type} - {qty} - {bollinger_init_data['UpperBand']} -  {bollinger_init_data['LowerBand']} -  {bollinger_init_data['MA']} -  {bollinger_init_data['BB_Width_%']} - RSI INICIAL: {rsi_init_data} - RSI ACTUAL{(rsi)}")
            if not verificar_posicion_abierta(symbol):
                logger(f"{test_mode} analizar_posible_orden en {symbol} - No hay posiciones abiertas en {symbol}")
                datam = obtener_datos_historicos(symbol, timeframe)
                open_prices = np.array(datam[1])
                high_prices = np.array(datam[2])
                low_prices = np.array(datam[3])
                close_prices = np.array(datam[4])

                rsi = calcular_rsi_talib(datam[4])
                momento_alcista = patron_velas_alcistas(open_prices, high_prices, low_prices, close_prices)
                momento_bajista = patron_velas_bajistas(open_prices, high_prices, low_prices, close_prices)

                if rsi > 45 and rsi < 55:
                    logger(f"{test_mode} analizar_posible_orden en {symbol} - RSI en instancias medias {rsi} salgo del analisis.")
                    break
                    
                if side == "Sell":

                    if momento_bajista:
                        logger(f"{test_mode} analizar_posible_orden en {symbol} - Creando orden en {symbol} - {side} - {order_type} - {qty} - rsi {rsi}")
                        crear_orden(symbol, side, order_type, qty)

                        if monitoring == 1:
                            # Iniciar el monitoreo de la operación
                            precio_entrada = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                            hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_entrada, side, qty))
                            hilo_monitoreo.start()
                    else:
                        logger(f"analizar_posible_orden en {symbol} - No se detecta un patrón bajista en {symbol}")

                else:

                    if momento_alcista:
                        logger(f"{test_mode} analizar_posible_orden en {symbol} - Creando orden en {symbol} - {side} - {order_type} - {qty}  - rsi {rsi}")
                        crear_orden(symbol, side, order_type, qty)
                        if monitoring == 1:
                            # Iniciar el monitoreo de la operación
                            precio_entrada = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                            hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_entrada, side, qty))
                            hilo_monitoreo.start()
                    else:
                        logger(f"{test_mode} analizar_posible_orden en {symbol} - No se detecta un patrón alcista en {symbol}") 

            else:
                logger(f"{test_mode} analizar_posible_orden en {symbol} - Ya hay una posición abierta en {symbol}")
                break
        except Exception as e:
            logger(f"{test_mode} analizar_posible_orden en {symbol} - Error al analizar posible orden en {symbol}: {e}")
            break

        time.sleep(random.randint(int(sleep_rand_from/4), int(sleep_rand_to/4)))


def analizar_posible_orden_ema(symbol, side, order_type, qty, stop_loss_param, take_profit_param):
    global test_mode

    
    while True:
        try:
            if not verificar_posicion_abierta(symbol):
                logger(f"analizar_posible_orden en {symbol} - No hay posiciones abiertas en {symbol}")
 
                datam = obtener_datos_historicos(symbol, timeframe)
                
                open_prices = np.array(datam[1])
                high_prices = np.array(datam[2])
                low_prices = np.array(datam[3])
                close_prices = np.array(datam[4])
                volumes = np.array(datam[5])

                df = pd.DataFrame({
                    'open': open_prices,
                    'high': high_prices,
                    'low': low_prices,
                    'close': close_prices,
                    'volume': volumes
                })

                ema20 = talib.EMA(close_prices, timeperiod=20)[-1]
                # Obtener el precio actual del último cierre
                precio_actual = close_prices[-1]
                logger(f"Analizando {symbol} - Precio actual: {precio_actual} - EMA20: {ema20}")

                # También podríamos obtener un precio en tiempo real directamente de la API
                try:
                    precio_tiempo_real = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                    logger(f"Precio en tiempo real de {symbol}: {precio_tiempo_real}")
                except Exception as e:
                    logger(f"Error al obtener precio en tiempo real: {e}")
                    precio_tiempo_real = precio_actual

                rsi = calcular_rsi_talib(df['close'])


                if side == "Sell": # Precio por debajo de la ema de 20
                    if precio_tiempo_real < ema20 and rsi < 70:
                        crear_orden_con_stoploss_takeprofit(symbol, "Sell", order_type, qty,stop_loss_param,take_profit_param)
                        break
                   
                else:
                    if precio_tiempo_real > ema20 and rsi > 30:
                        crear_orden_con_stoploss_takeprofit(symbol, "Buy", order_type, qty,stop_loss_param,take_profit_param)
                        break
            else:
                logger(f"analizar_posible_orden en {symbol} - Ya hay una posición abierta en {symbol}")
                break
        except Exception as e:
            logger(f"analizar_posible_orden en {symbol} - Error al analizar posible orden en {symbol}: {e}")
            break

        time.sleep(random.randint(int(sleep_rand_from/4), int(sleep_rand_to/4)))



def monitorear_operaciones_abiertas_0(symbol, precio_entrada, side, qty):
    global test_mode

    pe = precio_entrada
    while True:
        try:
            posiciones = client.get_positions(category="linear", symbol=symbol)
            if float(posiciones['result']['list'][0]['size']) != 0:
                precio_actual = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                logger(f"{test_mode} monitorear_operaciones_abiertas {symbol} - Precio actual: {precio_actual} - Precio de entrada: {precio_entrada}")
                if side == 'Buy':
                    if precio_actual > (pe):
                        nuevo_stop_loss = precio_actual * (1 - sl_callback_percentage / 100)
                        establecer_stop_loss(symbol, nuevo_stop_loss)
                        pe = precio_actual
                        logger(f"{test_mode} monitorear_operaciones_abiertas {symbol} Stop loss ajustado a {nuevo_stop_loss} para {symbol} en posición Buy")
                else:
                    if precio_actual < (pe):
                        nuevo_stop_loss = precio_actual * (1 + sl_callback_percentage / 100)
                        establecer_stop_loss(symbol, nuevo_stop_loss)
                        pe = precio_actual
                        logger(f"{test_mode} monitorear_operaciones_abiertas {symbol} Stop loss ajustado a {nuevo_stop_loss} para {symbol} en posición Sell")
            else:
                logger(f"{test_mode} monitorear_operaciones_abiertas {symbol} No hay posiciones abiertas en {symbol}. Saliendo del monitoreo.")
                break

            time.sleep(random.randint(int(sleep_rand_from/4), int(sleep_rand_to/4)))
        except Exception as e:
            logger(f"{test_mode} monitorear_operaciones_abiertas {symbol} Error al monitorear la operación en {symbol}: {e}")
            break




def monitorear_operaciones_abiertas(symbol, precio_entrada, side, sl_callback=1):
    global test_mode,sl_callback_progresive

    pe = precio_entrada
    counter_sl = 1.0
    
    while True:
        try:
            posiciones = client.get_positions(category="linear", symbol=symbol)
            if float(posiciones['result']['list'][0]['size']) != 0:
                precio_actual = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                logger(f"{test_mode} monitorear_operaciones_abiertas {symbol} - Precio actual: {precio_actual} - Precio de entrada: {precio_entrada}")
                if side == 'Buy':
                    if precio_actual > (pe * 1.01):
                        sl_progresive = sl_callback / counter_sl
                        nuevo_stop_loss = precio_actual * (1 - sl_progresive / 100)
                        establecer_stop_loss(symbol, nuevo_stop_loss)
                        pe = precio_actual
                        counter_sl += sl_callback_progresive
                        logger(f"{test_mode} monitorear_operaciones_abiertas {symbol} Stop loss ajustado a {nuevo_stop_loss} para {symbol} en posición Buy")
                else:
                    if precio_actual < (pe * 0.99):
                        sl_progresive = sl_callback / counter_sl
                        nuevo_stop_loss = precio_actual * (1 + sl_progresive / 100)
                        establecer_stop_loss(symbol, nuevo_stop_loss)
                        pe = precio_actual
                        counter_sl += sl_callback_progresive
                        logger(f"{test_mode} monitorear_operaciones_abiertas {symbol} Stop loss ajustado a {nuevo_stop_loss} para {symbol} en posición Sell")
            else:
                logger(f"{test_mode} monitorear_operaciones_abiertas {symbol} No hay posiciones abiertas en {symbol}. Saliendo del monitoreo.")
                break

            time.sleep(random.randint(int(sleep_rand_from/4), int(sleep_rand_to/4)))
        except Exception as e:
            logger(f"{test_mode} monitorear_operaciones_abiertas {symbol} Error al monitorear la operación en {symbol}: {e}")
            break



def monitorear_operaciones_abierta_macd_syr(symbol, precio_entrada, side, qty):
    global test_mode

    pe = precio_entrada
    while True:
        try:
            posiciones = client.get_positions(category="linear", symbol=symbol)
            if float(posiciones['result']['list'][0]['size']) != 0:
                precio_actual = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                logger(f"{test_mode} monitorear_operaciones_abiertas {symbol} - Precio actual: {precio_actual} - Precio de entrada: {precio_entrada}")
                if side == 'Buy':
                    if precio_actual > pe:
                        nuevo_stop_loss = precio_actual * (1 - sl_callback_percentage / 100)
                        establecer_stop_loss(symbol, nuevo_stop_loss)
                        pe = precio_actual
                        logger(f"{test_mode} monitorear_operaciones_abiertas {symbol} Stop loss ajustado a {nuevo_stop_loss} para {symbol} en posición Buy")
                else:
                    if precio_actual < pe:
                        nuevo_stop_loss = precio_actual * (1 + sl_callback_percentage / 100)
                        establecer_stop_loss(symbol, nuevo_stop_loss)
                        pe = precio_actual
                        logger(f"{test_mode} monitorear_operaciones_abiertas {symbol} Stop loss ajustado a {nuevo_stop_loss} para {symbol} en posición Sell")
            else:
                logger(f"{test_mode} monitorear_operaciones_abiertas {symbol} No hay posiciones abiertas en {symbol}. Saliendo del monitoreo.")
                break

            time.sleep(random.randint(int(sleep_rand_from/4), int(sleep_rand_to/4)))
        except Exception as e:
            logger(f"{test_mode} monitorear_operaciones_abiertas {symbol} Error al monitorear la operación en {symbol}: {e}")
            break

def monitorear_operaciones_abiertas_macd(symbol, precio_entrada, side, qty):
    global test_mode

    pe = precio_entrada
    while True:
        try:
            posiciones = client.get_positions(category="linear", symbol=symbol)
            if float(posiciones['result']['list'][0]['size']) != 0:
                precio_actual = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                logger(f"{test_mode} monitorear_operaciones_abiertas {symbol} - Precio actual: {precio_actual} - Precio de entrada: {precio_entrada}")
                if side == 'Buy':
                    if precio_actual > pe:
                        nuevo_stop_loss = precio_actual * (1 - sl_callback_percentage / 100)
                        establecer_stop_loss(symbol, nuevo_stop_loss)
                        pe = precio_actual
                        logger(f"{test_mode} monitorear_operaciones_abiertas {symbol} Stop loss ajustado a {nuevo_stop_loss} para {symbol} en posición Buy")
                else:
                    if precio_actual < pe:
                        nuevo_stop_loss = precio_actual * (1 + sl_callback_percentage / 100)
                        establecer_stop_loss(symbol, nuevo_stop_loss)
                        pe = precio_actual
                        logger(f"{test_mode} monitorear_operaciones_abiertas {symbol} Stop loss ajustado a {nuevo_stop_loss} para {symbol} en posición Sell")
            else:
                logger(f"{test_mode} monitorear_operaciones_abiertas {symbol} No hay posiciones abiertas en {symbol}. Saliendo del monitoreo.")
                break

            time.sleep(random.randint(int(sleep_rand_from/4), int(sleep_rand_to/4)))
        except Exception as e:
            logger(f"{test_mode} monitorear_operaciones_abiertas {symbol} Error al monitorear la operación en {symbol}: {e}")
            break


def get_opened_positions(symbol):
    global test_mode
    global opened_positions_long, opened_positions_short

    try:
        posiciones = client.get_positions(category="linear", symbol=symbol)
        if float(posiciones['result']['list'][0]['size']) == 0:
            if symbol in opened_positions_long:
                opened_positions_long.remove(symbol)
            if symbol in opened_positions_short:
                opened_positions_short.remove(symbol)

        if float(posiciones['result']['list'][0]['size']) != 0:
            for posicion in posiciones['result']['list']:
                if posicion['side'] == 'Buy' and posicion['symbol'] not in opened_positions_long:
                    opened_positions_long.append(posicion['symbol'])
                elif posicion['side'] == 'Sell' and posicion['symbol'] not in opened_positions_short:
                    opened_positions_short.append(posicion['symbol'])

        return posiciones



    except Exception as e:
        logger(f"{test_mode} get_opened_positions Error al obtener las posiciones abiertas: {e}")


def logger(log_message,aditional_text=""):
    global timeframe, test_mode
    log_path = f"logs/log-{timeframe}-{time.strftime('%Y%m%d')}.txt"
    with open(log_path, "a") as log_file:
        log_file.write(str(timeframe) + '|' + str(test_mode) + '|' + time.strftime('%Y-%m-%d %H:%M:%S') + " " + log_message + " " + aditional_text + "\n")


def t_logger(log_message,aditional_text=""):
    log_path = f"logs/t_log-{timeframe}-{time.strftime('%Y%m%d')}.csv"
    with open(log_path, "a") as log_file:
        log_file.write(str(timeframe) + ";" + time.strftime('%Y-%m-%d %H:%M:%S') + ";" + log_message.replace('.', ',') + aditional_text + "\n")



# Metodos para calculo de soportes y resistencias
def calcular_niveles(precios: np.ndarray, bins: int = 20) -> np.ndarray:
        hist, bin_edges = np.histogram(precios, bins=bins)
        niveles = (bin_edges[:-1] + bin_edges[1:]) / 2  # Centros de los bins
        niveles_importantes = niveles[hist > np.percentile(hist, 75)]  # Filtra los más significativos
        return niveles_importantes

def consolidar_niveles(niveles_tf1: np.ndarray, 
                        niveles_tf2: np.ndarray, 
                        niveles_tf3: np.ndarray, 
                        tolerancia: float = 0.005) -> np.ndarray:

        niveles_totales = np.concatenate([niveles_tf1, niveles_tf2, niveles_tf3])
        niveles_filtrados = []
        
        for nivel in niveles_totales:
            if not any(abs(nivel - n) < tolerancia * nivel for n in niveles_filtrados):
                niveles_filtrados.append(nivel)
                
        return np.array(sorted(niveles_filtrados))
        

def encontrar_niveles_cercanos(niveles: np.ndarray, valor_actual: float) -> Tuple[np.ndarray, np.ndarray]:

        niveles = np.array(niveles)
        soportes = niveles[niveles < valor_actual]
        resistencias = niveles[niveles > valor_actual]

        # Tomar los dos soportes más cercanos (ordenados de mayor a menor)
        soportes_cercanos = np.sort(soportes)[-3:] if len(soportes) >= 3 else soportes
        
        # Tomar las dos resistencias más cercanas (ordenados de menor a mayor)
        resistencias_cercanas = np.sort(resistencias)[:3] if len(resistencias) >= 3 else resistencias

        return soportes_cercanos, resistencias_cercanas

def obtener_precio_actual(symbol: str) -> float:
    try:
        ticker = client.get_tickers(category='linear', symbol=symbol)
        precio = float(ticker['result']['list'][0]['lastPrice'])
        return precio
    except Exception as e:
        logger.error(f"Error al obtener el precio actual de {symbol}: {e}")
        raise


def get_soportes_resistencia(symbol, frame1="240", frame2="D", frame3="W", limit1=200, limit2=100, limit3=50, tolerancia=0.005) -> Tuple[np.ndarray, np.ndarray, float, np.ndarray, np.ndarray]:

    data1 = obtener_datos_historicos(symbol, frame1, limit1)
    if data1 is None or len(data1[4]) == 0:
        raise ValueError(f"No se pudieron obtener datos para {symbol} en timeframe {frame1}")
    i1 = np.array(data1[4])  # Precios de cierre
    
    data2 = obtener_datos_historicos(symbol, frame2, limit2)
    if data2 is None or len(data2[4]) == 0:
        raise ValueError(f"No se pudieron obtener datos para {symbol} en timeframe {frame2}")
    i2 = np.array(data2[4])  # Precios de cierre
    
    data3 = obtener_datos_historicos(symbol, frame3, limit3)
    if data3 is None or len(data3[4]) == 0:
        raise ValueError(f"No se pudieron obtener datos para {symbol} en timeframe {frame3}")
    i3 = np.array(data3[4])  # Precios de cierre
    
    niveles_1 = calcular_niveles(i1)
    niveles_2 = calcular_niveles(i2)
    niveles_3 = calcular_niveles(i3)
    
    niveles_finales = consolidar_niveles(niveles_1, niveles_2, niveles_3, tolerancia)
    valor_actual = obtener_precio_actual(symbol)

    niveles = np.array(niveles_finales)
    soportes_todas = niveles[niveles < valor_actual]
    resistencias_todas = niveles[niveles > valor_actual]

    soportes_cercanos, resistencias_cercanas = encontrar_niveles_cercanos(niveles_finales, valor_actual)

    return soportes_cercanos, resistencias_cercanas, valor_actual, soportes_todas, resistencias_todas,niveles_finales

def get_soportes_resistencia_fuertes(symbol, frame1="240", frame2="D", frame3="W", 
                               limit1=200, limit2=100, limit3=50, 
                               tolerancia=0.005, min_coincidencias=2) -> Tuple[np.ndarray, np.ndarray, float, np.ndarray, np.ndarray]:
    """
    Obtiene soportes y resistencias fuertes que coinciden en múltiples timeframes.
    
    Args:
        symbol: Símbolo a analizar
        frame1, frame2, frame3: Timeframes a considerar
        limit1, limit2, limit3: Número de velas a obtener para cada timeframe
        tolerancia: Tolerancia para considerar que dos niveles son similares
        min_coincidencias: Mínimo número de timeframes donde debe aparecer un nivel (2 o 3)
        
    Returns:
        Soportes cercanos, resistencias cercanas, precio actual, todos los soportes, todas las resistencias
    """
    # Obtener datos para cada timeframe
    data1 = obtener_datos_historicos(symbol, frame1, limit1)
    if data1 is None or len(data1[4]) == 0:
        raise ValueError(f"No se pudieron obtener datos para {symbol} en timeframe {frame1}")
    i1 = np.array(data1[4])  # Precios de cierre
    
    data2 = obtener_datos_historicos(symbol, frame2, limit2)
    if data2 is None or len(data2[4]) == 0:
        raise ValueError(f"No se pudieron obtener datos para {symbol} en timeframe {frame2}")
    i2 = np.array(data2[4])  # Precios de cierre
    
    data3 = obtener_datos_historicos(symbol, frame3, limit3)
    if data3 is None or len(data3[4]) == 0:
        raise ValueError(f"No se pudieron obtener datos para {symbol} en timeframe {frame3}")
    i3 = np.array(data3[4])  # Precios de cierre
    
    # Calcular niveles independientes para cada timeframe
    niveles_1 = calcular_niveles(i1)
    niveles_2 = calcular_niveles(i2)
    niveles_3 = calcular_niveles(i3)
    
    # Crear un diccionario para rastrear las coincidencias
    niveles_coincidentes = {}
    
    # Función para verificar si un nivel coincide con otro dentro de la tolerancia
    def es_coincidente(nivel, lista_niveles, tolerancia_rel):
        for n in lista_niveles:
            if abs(nivel - n) < nivel * tolerancia_rel:
                return True, n
        return False, None
    
    # Verificar coincidencias entre timeframes
    for nivel in niveles_1:
        coincide_tf2, nivel_tf2 = es_coincidente(nivel, niveles_2, tolerancia)
        coincide_tf3, nivel_tf3 = es_coincidente(nivel, niveles_3, tolerancia)
        
        puntuacion = 1  # Siempre cuenta el timeframe actual
        if coincide_tf2: puntuacion += 1
        if coincide_tf3: puntuacion += 1
        
        # Obtener el nivel promedio de las coincidencias
        if puntuacion > 1:
            niveles_coincidentes[nivel] = {
                'puntuacion': puntuacion,
                'valor': nivel  # Usamos el nivel original por simplicidad
            }
    
    # Verificar si hay niveles en TF2 que no coinciden con TF1 pero sí con TF3
    for nivel in niveles_2:
        if not any(abs(nivel - n) < nivel * tolerancia for n in niveles_1):
            coincide_tf3, nivel_tf3 = es_coincidente(nivel, niveles_3, tolerancia)
            
            if coincide_tf3:
                niveles_coincidentes[nivel] = {
                    'puntuacion': 2,  # TF2 + TF3
                    'valor': nivel
                }
    
    # Filtrar solo los niveles que aparecen en al menos min_coincidencias timeframes
    niveles_filtrados = [info['valor'] for nivel, info in niveles_coincidentes.items() 
                        if info['puntuacion'] >= min_coincidencias]
    
    # Si no hay niveles con suficientes coincidencias, relajar el criterio
    if not niveles_filtrados and min_coincidencias > 1:
        logger(f"{symbol:<15}\tNo se encontraron niveles coincidentes en {min_coincidencias} timeframes. Probando con coincidencias = 1")
        # Usar todos los niveles consolidados como respaldo
        niveles_filtrados = consolidar_niveles(niveles_1, niveles_2, niveles_3, tolerancia)
    
    niveles_finales = np.array(sorted(niveles_filtrados))
    valor_actual = obtener_precio_actual(symbol)
    
    # Clasificar los niveles según el precio actual
    soportes_todas = niveles_finales[niveles_finales < valor_actual]
    resistencias_todas = niveles_finales[niveles_finales > valor_actual]
    
    # Obtener los niveles más cercanos
    soportes_cercanos, resistencias_cercanas = encontrar_niveles_cercanos(niveles_finales, valor_actual)
    
    # Registrar información sobre los niveles fuertes
    logger(f"Niveles fuertes para {symbol}: {len(niveles_finales)} encontrados")
    logger(f"Soportes fuertes: {len(soportes_todas)}, Resistencias fuertes: {len(resistencias_todas)}")
    
    return soportes_cercanos, resistencias_cercanas, valor_actual, soportes_todas, resistencias_todas, niveles_finales

def obtener_orderbook_binance(symbol: str, limite: int = 1000):
    """
    Obtiene el Order Book (libro de órdenes) de Binance para un par de trading.

    Parámetros:
    - symbol (str): Par de trading en formato Binance (ej. "BTC/USDT").
    - limite (int): Número de niveles del Order Book (default: 100, máximo: 5000).

    Retorna:
    - bids: Lista de órdenes de compra [[precio, volumen], ...]
    - asks: Lista de órdenes de venta [[precio, volumen], ...]
    """

    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}  # Esto especifica que quieres usar el mercado de futuros
    })

    try:
        order_book = exchange.fetch_order_book(symbol.replace('USDT', '/USDT'), limit=limite)
        bids = order_book['bids']  # Órdenes de compra [[precio, volumen]]
        asks = order_book['asks']  # Órdenes de venta [[precio, volumen]]

        return bids, asks

    except Exception as e:
        print(f"⚠️ Error al obtener Order Book de binance: {e}")
        return [], []

def hay_acumulacion_compras(symbol: str, soporte: float, bids, asks ,tolerancia: float = 0.01):
    """
    Verifica si hay acumulación de órdenes de compra en el soporte que supera las ventas.
    
    Parámetros:
    - symbol (str): El par de trading (ej. "BTCUSDT").
    - soporte (float): Nivel de soporte a evaluar.
    - tolerancia (float): Margen de precio para considerar órdenes cercanas al soporte (por defecto ±1%).

    Retorna:
    - bool: True si hay más compras que ventas en el soporte, False si no.
    """
    try:

        # Filtrar órdenes de compra cercanas al soporte (dentro de ±tolerancia%)
        bids_cercanos = [bid for bid in bids if soporte * (1 - tolerancia) <= float(bid[0]) <= soporte * (1 + tolerancia)]
        asks_cercanos = [ask for ask in asks if soporte * (1 - tolerancia) <= float(ask[0]) <= soporte * (1 + tolerancia)]

        # Sumar volumen de órdenes de compra y venta en el soporte
        volumen_compras = sum(float(bid[1]) for bid in bids_cercanos)
        volumen_ventas = sum(float(ask[1]) for ask in asks_cercanos)

        print(f"📊 Soporte: {soporte}")
        print(f"💰 Volumen de compras: {volumen_compras}")
        print(f"📉 Volumen de ventas: {volumen_ventas}")

        # Comparar volúmenes
        if volumen_compras > volumen_ventas:
            print("✅ Hay acumulación de compras en el soporte. Posible rebote.")
            return True,volumen_ventas,volumen_compras
        else:
            print("❌ No hay acumulación de compras suficiente en el soporte.")
            return False,volumen_ventas,volumen_compras

    except Exception as e:
        print(f"⚠️ Error al obtener datos: {e}")
        return False,0,0


def hay_acumulacion_ventas(symbol: str, resistencia: float, bids, asks , tolerancia: float = 0.01):
    """
    Verifica si hay acumulación de órdenes de venta en la resistencia que supera las compras.
    
    Parámetros:
    - symbol (str): El par de trading (ej. "BTCUSDT").
    - resistencia (float): Nivel de resistencia a evaluar.
    - tolerancia (float): Margen de precio para considerar órdenes cercanas a la resistencia (por defecto ±1%).

    Retorna:
    - bool: True si hay más ventas que compras en la resistencia, False si no.
    """
    try:

        # Filtrar órdenes de venta cercanas a la resistencia (dentro de ±tolerancia%)
        asks_cercanos = [ask for ask in asks if resistencia * (1 - tolerancia) <= float(ask[0]) <= resistencia * (1 + tolerancia)]
        bids_cercanos = [bid for bid in bids if resistencia * (1 - tolerancia) <= float(bid[0]) <= resistencia * (1 + tolerancia)]

        # Sumar volumen de órdenes de venta y compra en la resistencia
        volumen_ventas = sum(float(ask[1]) for ask in asks_cercanos)
        volumen_compras = sum(float(bid[1]) for bid in bids_cercanos)

        print(f"📊 Resistencia: {resistencia}")
        print(f"📉 Volumen de ventas: {volumen_ventas}")
        print(f"💰 Volumen de compras: {volumen_compras}")

        # Comparar volúmenes
        if volumen_ventas > volumen_compras:
            print("🚨 Hay acumulación de ventas en la resistencia. Posible rechazo. 🚨")
            return True,volumen_ventas,volumen_compras
        else:
            print("✅ No hay acumulación fuerte de ventas en la resistencia.")
            return False,volumen_ventas,volumen_compras

    except Exception as e:
        print(f"⚠️ Error al obtener datos: {e}")
        return False,0,0

def get_open_interest(symbol: str):
    global timeframe
    """
    Obtiene el Open Interest para un símbolo en Bybit y determina su tendencia.
    
    :param symbol: Símbolo de la criptomoneda (ej. "BTCUSDT")
    :param interval: Intervalo de tiempo en minutos para el historial (ej. 5, 15, 30, 60)
    :return: Dirección de la tendencia ("Subiendo", "Bajando" o "Sin cambios")
    """
    try:
        response = client.get_open_interest(
            category="linear",
            symbol=symbol,
            intervalTime="5min"
        )
        
        if "result" not in response:
            return "Error en la respuesta de la API"
        
        data = response["result"]["list"]
        
        if not data:
            return "No hay datos disponibles"
        
        # Convertir datos a DataFrame para análisis
        df = pd.DataFrame(data)
        df["openInterest"] = df["openInterest"].astype(float)

        # Verificar si el Open Interest está subiendo o bajando
        oi_actual = df["openInterest"].iloc[-1]
        oi_anterior = df["openInterest"].iloc[-2]

        if oi_actual > oi_anterior:
            return "Subiendo"
        elif oi_actual < oi_anterior:
            return "Bajando"
        else:
            return "Sin cambios"
       
    
    except Exception as e:
        logger(f"Error: {str(e)}") 
        return None



def analizar_reversion_tendencia(symbol, timeframe="240"):
    """
    Analiza la probabilidad de reversión de tendencia para un símbolo específico.
    
    Args:
        symbol (str): Símbolo a analizar (ej. "BTCUSDT")
        timeframe (str): Timeframe del análisis 
        
    Returns:
        dict: Resultado del análisis de reversión
    """
    try:
        # Obtener datos históricos
        datam = obtener_datos_historicos(symbol, timeframe)
        
        # Convertir a DataFrame de pandas
        df = pd.DataFrame({
            'open': np.array(datam[1]),
            'high': np.array(datam[2]),
            'low': np.array(datam[3]),
            'close': np.array(datam[4]),
            'volume': np.array(datam[5])
        })
        
        # Calcular probabilidad de reversión
        probabilidad, direccion, factores = calcular_probabilidad_reversion(df, timeframe)
        
        # Obtener precio actual
        ticker = client.get_tickers(category='linear', symbol=symbol)
        precio = float(ticker['result']['list'][0]['lastPrice'])
        
        resultado = {
            'symbol': symbol,
            'precio_actual': precio,
            'timeframe': timeframe,
            'probabilidad_reversion': round(probabilidad, 2),
            'direccion_probable': direccion,
            'factores_clave': {
                'rsi': round(factores['rsi'], 2),
                'adx': round(factores['adx'], 2),
                'volatilidad_atr': round(factores['atr_percent'], 2),
                'divergencia': factores['divergencia'],
                'patrones_vela': factores['patrones_vela'] != 0
            }
        }

        # try:
        #     res = trend_reversal_probability(df)
        # except Exception as e:
        #     print(f"Error al calcular la probabilidad de reversión: {e}")
        
        logger(f"{symbol:<15}\t{precio:.5f} \tTF: {timeframe}\tProb. Reversión: {probabilidad:.2f}%\t\tDirección: {direccion}\tRSI: {factores['rsi']:.1f}")

        t_log_message = f"{symbol};{precio:.5f};{timeframe};{probabilidad:.2f};{direccion};{factores['rsi']:.1f};{factores['adx']:.1f};{factores['atr_percent']:.1f};{factores['divergencia']};{factores['patrones_vela']}"
        t_logger(t_log_message)

        return resultado
    
    except Exception as e:
        # logger(f"Error al analizar reversión para {symbol}: {e}")
        return None




def get_oi_klines_binance(symbol="BTCUSDT", interval="5m", limit=6):
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
                df['open_interest'] = df['sumOpenInterest'].astype(float)
                df['open_interest_value'] = df['sumOpenInterestValue'].astype(float)

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
                            klines_df[['timestamp_key', 'open', 'close', 'volume']].sort_values('timestamp_key'),
                            left_on='kline_open_time',
                            right_on='timestamp_key',
                            direction='nearest'
                        )


                return df
            else:
                # print(f"Error al obtener datos: {response.status_code}")
                # print(response.text)
                return None
        except Exception as e:
            # print(f"Error en la solicitud: {e}")
            return None

def detectar_tendencia_fuerte(symbol, df, umbral = 0.01):
    """
    df: DataFrame con las últimas 5 velas. Debe tener columnas: 'precio', 'open_interest', 'volumen'
    Retorna: 'alcista fuerte', 'bajista fuerte' o 'nada'
    """

    if df is None or len(df) == 0:
        return "sin datos"

    if len(df) < 2:
        return "insuficientes datos"

    df = df.copy()

    df[['close', 'open_interest', 'volume']] = df[['close', 'open_interest', 'volume']].astype(float)
    # print(df[['timestamp','close', 'open_interest', 'volume']])
    cambios = df[['close', 'open_interest', 'volume']].pct_change().dropna()

    cambios['suma_close'] = cambios['close'].cumsum()
    cambios['suma_open_interest'] = cambios['open_interest'].cumsum()
    cambios['suma_volume'] = cambios['volume'].cumsum()

    ultimos_cambios = cambios.iloc[-1]

    precio_sube = ultimos_cambios['suma_close'] > umbral
    oi_sube = ultimos_cambios['suma_open_interest'] >umbral
    vol_sube = ultimos_cambios['suma_volume'] > umbral

    precio_baja = ultimos_cambios['suma_close'] < umbral*(-1.0)
    oi_baja = ultimos_cambios['suma_open_interest'] < umbral*(-1.0)
    vol_baja = ultimos_cambios['suma_volume'] < umbral*(-1.0)
    diff_open_close = df['open'].iloc[-1] - df['close'].iloc[-1]

    # print(f"Precio: PS: {precio_sube}, OIS: {oi_sube}, PB: {precio_baja}, OIB: {oi_baja},")
    print(f"{symbol:<15}\tUltimos cambios: {ultimos_cambios['suma_close']:<5.5f}\t{ultimos_cambios['suma_open_interest']:<5.5f}\t\t{diff_open_close:<5.4f}")
    # \t{df['open'].iloc[-1].astype(float) - df['close'].iloc[-1].astype(float)}
    
    if precio_sube and oi_sube and vol_sube and diff_open_close < 0:
        return "alcista"
    elif precio_baja and oi_sube and vol_sube and diff_open_close > 0:
        return "bajista"
    else:
        return "nada"


def get_btc_price_change():
    """
    Obtiene el cambio porcentual del precio de BTC en las últimas 24 horas.
    
    Retorna:
        float: Cambio porcentual del precio de BTC.
    """
    try:
        ticker = client.get_tickers(category='linear', symbol='BTCUSDT')
        precio_actual = float(ticker['result']['list'][0]['lastPrice'])
        precio_24h_ago = float(ticker['result']['list'][0]['prevPrice24h'])
        
        cambio_porcentual = ((precio_actual - precio_24h_ago) / precio_24h_ago) * 100
        return cambio_porcentual
    except Exception as e:
        logger(f"Error al obtener el cambio porcentual del precio de BTC: {e}")
        return None


def get_btc_price_change_ticker():

    try:
        # Simple in-memory cache for 1 hour
        if not hasattr(get_btc_price_change_ticker, "_cache"):
            get_btc_price_change_ticker._cache = {"value": None, "timestamp": 0}
        cache = get_btc_price_change_ticker._cache
        now = time.time()
        if cache["value"] is not None and now - cache["timestamp"] < 60:  # 5 minutes cache
            return float(cache["value"])

        # If not cached or cache expired, fetch and cache
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}  # Para usar el mercado de futuros
        })
        

        # Check if another process is already executing
        if cache.get("executing", False):
            # En vez de retornar 0.0, retorna el último valor cacheado si existe
            if cache["value"] is not None:
                return float(cache["value"])
            return 0.0
        cache["executing"] = True
        try:
            value = 0.0
            tickers = exchange.fetch_tickers()
            ticker = None
            for i, (symbol, data) in enumerate(list(tickers.items())):
                    if symbol.endswith('USDT'):
                        item = {
                            "symbol":data['info']['symbol'],
                            "quoteVolume": data['info']['quoteVolume'],
                            "priceChangePercent": data['info']['priceChangePercent']
                        }
                        if item['symbol'] == 'BTCUSDT':
                            print(f"Encontrado BTCUSDT en tickers: {item}")
                            ticker = item
                            break
                        

            value = float(ticker['priceChangePercent'])
            cache["value"] = value
            cache["timestamp"] = now
            return value
        finally:
            cache["executing"] = False


        
    except Exception as e:
        logger(f"Error al obtener el cambio porcentual del ticker de BTC: {e}")
        return 0.0

    