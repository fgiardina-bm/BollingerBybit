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
    try:
        response = client.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            orderType=order_type,
            qty=qty,
            timeInForce="GoodTillCancel"
        )
        logger("Orden creada con exito:" + str(response))

        time.sleep(1)
        establecer_st_tp(symbol)

    except Exception as e:
        logger(f"Error al crear la orden: {e}")

def establecer_st_tp(symbol):
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
                        logger(f"{symbol} Stop loss y take profit activados")
    except Exception as e:
        logger(f"{symbol} Error al establecer stop loss y take profit: {e}")                   

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
  
        logger(f"{symbol} Stop loss establecido en {sl}")
        return order
    except Exception as e:
        logger(f"{symbol} Error al establecer el stop loss: {e}")
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

        logger(f"{symbol} Take profit establecido a {price}")
        return order
    except Exception as e:
        logger(f"{symbol} Error al establecer el take profit: {e}")
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
    max_min_rsi = rsi_init_data

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
                    
                if side == "Sell": # bollineger y RSI altos
                    if rsi > max_min_rsi:
                        max_min_rsi = rsi

                    rsi_limit = float(rsi) + float(verify_rsi)
                    if (bollinger['UpperBand'] < bollinger_init_data['UpperBand']) or (rsi_limit < max_min_rsi):
                        actual_bb = bollinger['LowerBand']
                        inicial_bb = bollinger_init_data['LowerBand']
                        logger(f"analizar_posible_orden en {symbol} - Creando orden en {symbol} - {side} - {order_type} - {qty} - rsi {rsi} - rsi_limit {rsi_limit} - rsi_init_data {rsi_init_data} - actual_bb {actual_bb} - inicial_bb {inicial_bb}")
                        crear_orden(symbol, side, order_type, qty)

                        if monitoring == 1:
                            # Iniciar el monitoreo de la operación
                            precio_entrada = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                            hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_entrada, side, qty))
                            hilo_monitoreo.start()

                        break
                    else:
                        logger(f"analizar_posible_orden en {symbol} - SELL RSI en {symbol} rsi_limit: {rsi_limit} es mayor a max_min_rsi: {max_min_rsi} - rsi_init_data: {rsi_init_data} - Actual UB: {bollinger['UpperBand']} - Inicial UB: {bollinger_init_data['UpperBand']}")

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
                logger(f"analizar_posible_orden en {symbol} - Ya hay una posición abierta en {symbol}")
                break
        except Exception as e:
            logger(f"analizar_posible_orden en {symbol} - Error al analizar posible orden en {symbol}: {e}")
            break

        time.sleep(20)

def analizar_posible_orden_patron_velas(symbol, side, order_type, qty, bollinger_init_data, rsi_init_data):
    rsi = rsi_init_data

    while True:
        try:
            if len(opened_positions) >= max_ops:
                logger(f"analizar_posible_orden - Se alcanzó el límite de posiciones abiertas | {max_ops}.")
                break
            
            logger(f"analizar_posible_orden en {symbol} - {side} - {order_type} - {qty} - {bollinger_init_data['UpperBand']} -  {bollinger_init_data['LowerBand']} -  {bollinger_init_data['MA']} -  {bollinger_init_data['BB_Width_%']} - RSI INICIAL: {rsi_init_data} - RSI ACTUAL{(rsi)}")
            if not verificar_posicion_abierta(symbol):
                logger(f"analizar_posible_orden en {symbol} - No hay posiciones abiertas en {symbol}")
                datam = obtener_datos_historicos(symbol, timeframe)
                open_prices = np.array(datam[1])
                high_prices = np.array(datam[2])
                low_prices = np.array(datam[3])
                close_prices = np.array(datam[4])

                rsi = calcular_rsi_talib(datam[4])
                momento_alcista = patron_velas_alcistas(open_prices, high_prices, low_prices, close_prices)
                momento_bajista = patron_velas_bajistas(open_prices, high_prices, low_prices, close_prices)

                if rsi > 40 and rsi < 60:
                    logger(f"analizar_posible_orden en {symbol} - RSI en instancias medias {rsi} salgo del analisis.")
                    break
                    
                if side == "Sell":

                    if momento_bajista:
                        logger(f"analizar_posible_orden en {symbol} - Creando orden en {symbol} - {side} - {order_type} - {qty} - rsi {rsi}")
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
                        logger(f"analizar_posible_orden en {symbol} - Creando orden en {symbol} - {side} - {order_type} - {qty}  - rsi {rsi}")
                        crear_orden(symbol, side, order_type, qty)
                        if monitoring == 1:
                            # Iniciar el monitoreo de la operación
                            precio_entrada = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                            hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_entrada, side, qty))
                            hilo_monitoreo.start()
                    else:
                        logger(f"analizar_posible_orden en {symbol} - No se detecta un patrón alcista en {symbol}") 

            else:
                logger(f"analizar_posible_orden en {symbol} - Ya hay una posición abierta en {symbol}")
                break
        except Exception as e:
            logger(f"analizar_posible_orden en {symbol} - Error al analizar posible orden en {symbol}: {e}")
            break

        time.sleep(random.randint(int(sleep_rand_from/4), int(sleep_rand_to/4)))


def monitorear_operaciones_abiertas(symbol, precio_entrada, side, qty):
    pe = precio_entrada
    while True:
        try:
            posiciones = client.get_positions(category="linear", symbol=symbol)
            if float(posiciones['result']['list'][0]['size']) != 0:
                precio_actual = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                logger(f"monitorear_operaciones_abiertas {symbol} - Precio actual de {symbol}: {precio_actual} - Precio de entrada: {precio_entrada}")
                if side == 'Buy':
                    # if precio_actual > pe and (precio_actual - precio_entrada) / precio_entrada >= (sl_callback_percentage / 100):
                    # if (precio_actual * 1.02) > pe:
                    if precio_actual > pe:
                        nuevo_stop_loss = precio_actual * (1 - sl_callback_percentage / 100)
                        establecer_stop_loss(symbol, nuevo_stop_loss)
                        pe = precio_actual
                        logger(f"monitorear_operaciones_abiertas {symbol} Stop loss ajustado a {nuevo_stop_loss} para {symbol} en posición Buy")
                else:
                    # if precio_actual < pe and (precio_entrada - precio_actual) / precio_entrada >= (sl_callback_percentage / 100):
                    # if (precio_actual * 0.98) < pe:
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
        log_file.write(str(timeframe) + '|' + time.strftime('%Y-%m-%d %H:%M:%S') + " " + log_message + " " + aditional_text + "\n")


def t_logger(log_message,aditional_text=""):
    log_path = f"logs/t_log-{timeframe}-{time.strftime('%Y%m%d')}.csv"
    with open(log_path, "a") as log_file:
        log_file.write(str(timeframe) + ";" + time.strftime('%Y-%m-%d %H:%M:%S') + ";" + log_message.replace('.', ',') + aditional_text + "\n")