import os
from pybit.unified_trading import HTTP
import pandas as pd
from dotenv import load_dotenv
import time
import math
from decimal import Decimal, ROUND_DOWN, ROUND_FLOOR
from concurrent.futures import ThreadPoolExecutor
from config import *
from indicators import *
import threading

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
            
            return top_10_simbolos
        else:
            logger("Error en la API:" + tickers["retMsg"])
            return []
    except Exception as e:
        logger(f"Error al obtener los símbolos con mayor volumen: {e}")
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
    try:
        posiciones = client.get_positions(category="linear", symbol=symbol)
        if posiciones["retCode"] == 0:
            for posicion in posiciones['result']['list']:
                if float(posicion['size']) > 0:
                    stop_loss = posicion.get('stopLoss')
                    take_profit = posicion.get('takeProfit')
                    if stop_loss:
                        # print(f"Posición abierta en {symbol} con Stop Loss: {stop_loss} y Take Profit: {take_profit}")
                        return True
                    else:
                        # print(f"Posición abierta en {symbol} sin Stop Loss o Take Profit configurados")
                        return False
            # print(f"No hay posiciones abiertas en {symbol}")
            return False
        else:
            logger("Error en la API:"+ posiciones["retMsg"])
            return False
    except Exception as e:
        logger(f"Error al verificar la posición abierta en {symbol}: {e}")
        return False

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
    qty = math.floor(qty / precision) * precision
    return qty

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

    # # Establecer el modo de margen y el apalancamiento antes de crear la orden
    # if not establecer_modo_margen_y_apalancamiento(symbol, leverage=10):
    #     print(f"No se pudo establecer el modo de margen y apalancamiento para {symbol}. Orden no creada.")
    #     return

    response = client.place_order(
        category="linear",
        symbol=symbol,
        side=side,
        orderType=order_type,
        qty=qty,
        timeInForce="GoodTillCancel"
    )
    logger("Orden creada con exito:" + str(response))

def establecer_stop_loss(symbol, sl):

    try:
        sl = qty_step(sl,symbol)

        order = client.set_trading_stop(
            category="linear",
            symbol=symbol,
            stopLoss=sl,
            slTriggerB="LastPrice",
            positionIdx=0
        )
  
        return order
    except Exception as e:
        logger(f"Error al establecer el stop loss para {symbol}: {e}")
        return None

def establecer_take_profit(symbol, tp, side):
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
        # Establecer el take profit en la posición
        order = client.set_trading_stop(
            category="linear",
            symbol=symbol,
            takeProfit=price,
            tpTriggerBy="LastPrice",
            positionIdx=0
        )

        logger(f"Take profit establecido para {symbol} a {price}")
        return order
    except Exception as e:
        logger(f"Error al establecer el take profit para {symbol}: {e}")
        return None

def establecer_trailing_stop(symbol, tp, side, qty, callback_ratio=1):

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


        logger(f"Trailing stop establecido para {symbol} a {trigger_price}")
        return order
    except Exception as e:
        logger(f"Error al establecer el trailing stop para {symbol}: {e}")
        return None


def check_opened_positions(opened_positions):
    while True:
        print()
        print(f" ----------------------------- Posiciones abiertas: {opened_positions} ----------------------------- ")
        print()
        time.sleep(60)

def analizar_posible_orden(symbol, side, order_type, qty, bollinger_init_data, rsi_init_data):

    rsi = rsi_init_data
    while True:
        try:
            logger(f"analizar_posible_orden en {symbol} - {side} - {order_type} - {qty} - {bollinger_init_data['UpperBand']} -  {bollinger_init_data['LowerBand']} -  {bollinger_init_data['MA']} -  {bollinger_init_data['BB_Width_%']} - {rsi_init_data} - {(rsi - verify_rsi)} - {(rsi + verify_rsi)}")
            if not verificar_posicion_abierta(symbol):
                logger(f"analizar_posible_orden en {symbol} - No hay posiciones abiertas en {symbol}")
                datam = obtener_datos_historicos(symbol, timeframe)
                bollinger = calcular_bandas_bollinger(datam)
                rsi = calcular_rsi_talib(datam[4])

                if side == "Sell": # bollineger y RSI altos
                    if bollinger['UpperBand'] < bollinger_init_data['UpperBand'] or (rsi - verify_rsi) < rsi_init_data:
                        logger(f"analizar_posible_orden en {symbol} - Creando orden en {symbol} - {side} - {order_type} - {qty}")
                        crear_orden(symbol, side, order_type, qty)
                        # Iniciar el monitoreo de la operación
                        precio_entrada = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                        hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_entrada, side, qty))
                        hilo_monitoreo.start()
                        break
                    else:
                        logger(f"analizar_posible_orden en {symbol} - SELL RSI en {symbol} es mayor a {rsi_init_data} - Actual UB: {bollinger['UpperBand']} - Inicial UB: {bollinger_init_data['UpperBand']}")

                else:
                    if bollinger['LowerBand'] > bollinger_init_data['LowerBand'] or (rsi + verify_rsi) > rsi_init_data:
                        logger(f"analizar_posible_orden en {symbol} - Creando orden en {symbol} - {side} - {order_type} - {qty}")
                        crear_orden(symbol, side, order_type, qty)
                        # Iniciar el monitoreo de la operación
                        precio_entrada = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                        hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_entrada, side, qty))
                        hilo_monitoreo.start()
                        break
                    else:
                       logger(f"analizar_posible_orden en {symbol} - BUY RSI en {symbol} es menor a {rsi_init_data} - Actual LB: {bollinger['LowerBand']} - Inicial LB: {bollinger_init_data['LowerBand']}")

            else:
                logger(f"analizar_posible_orden en {symbol} - Ya hay una posición abierta en {symbol}")
                break
        except Exception as e:
            logger(f"analizar_posible_orden en {symbol} - Error al analizar posible orden en {symbol}: {e}")
            break

        time.sleep(20)

def monitorear_operaciones_abiertas(symbol, precio_entrada, side, qty):
    pe = precio_entrada
    while True:
        try:
            posiciones = client.get_positions(category="linear", symbol=symbol)
            if float(posiciones['result']['list'][0]['size']) != 0:
                precio_actual = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                logger(f"monitorear_operaciones_abiertas {symbol} - Precio actual de {symbol}: {precio_actual} - Precio de entrada: {pe}")
                if side == 'Buy':
                    # if precio_actual > pe and (precio_actual - precio_entrada) / precio_entrada >= (sl_callback_percentage / 100):
                    if precio_actual > pe:
                        nuevo_stop_loss = precio_actual * (1 - sl_callback_percentage / 100)
                        establecer_stop_loss(symbol, nuevo_stop_loss)
                        pe = precio_actual
                        logger(f"monitorear_operaciones_abiertas {symbol} Stop loss ajustado a {nuevo_stop_loss} para {symbol} en posición Buy")
                else:
                    # if precio_actual < pe and (precio_entrada - precio_actual) / precio_entrada >= (sl_callback_percentage / 100):
                    if precio_actual < pe:
                        nuevo_stop_loss = precio_actual * (1 + sl_callback_percentage / 100)
                        establecer_stop_loss(symbol, nuevo_stop_loss)
                        pe = precio_actual
                        logger(f"monitorear_operaciones_abiertas {symbol} Stop loss ajustado a {nuevo_stop_loss} para {symbol} en posición Sell")
            else:
                logger(f"monitorear_operaciones_abiertas {symbol} No hay posiciones abiertas en {symbol}. Saliendo del monitoreo.")
                break

            time.sleep(10)
        except Exception as e:
            logger(f"monitorear_operaciones_abiertas {symbol} Error al monitorear la operación en {symbol}: {e}")
            break


def logger(log_message,aditional_text=""):
    log_path = f"logs/log-{timeframe}-{time.strftime('%Y%m%d')}.txt"
    with open(log_path, "a") as log_file:
        log_file.write(timeframe + '|' + log_message + aditional_text + "\n")