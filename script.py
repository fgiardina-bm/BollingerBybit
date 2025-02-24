from pybit.unified_trading import HTTP
import pandas as pd
import math
from decimal import Decimal, ROUND_DOWN, ROUND_FLOOR
import time

import os
from dotenv import load_dotenv
import numpy as np
import threading
from concurrent.futures import ThreadPoolExecutor
import queue
import random
import json
from functions import *
from indicators import *
from config import config_lock, reload_config

logger(f"Bot iniciado {timeframe}")

saldo_usdt_inicial = 0
try:
    saldo_usdt_inicial = obtener_saldo_usdt()
    logger("Saldo USDT:"+ str(saldo_usdt_inicial))
except Exception as e:
    logger(str(e))

def operar(simbolos):
    global opened_positions, opened_positions_short, opened_positions_long
    global saldo_usdt_inicial
    global api_key, api_secret, timeframe, tp_porcent, sl_porcent, cnt_symbols
    global account_percentage, top_rsi, bottom_rsi, sleep_rand_from, sleep_rand_to
    global sl_callback_percentage, verify_rsi, Bollinger_bands_width, monitoring, max_ops
    global opened_positions_long, opened_positions_short
    global max_ops_long, max_ops_short

    with config_lock:
        logger(f"Operando con un % de saldo de {account_percentage} primera operacion {saldo_usdt_inicial * (account_percentage / 100)}")

    while True:

         for symbol in simbolos:
            try:
                posiciones = get_opened_positions(symbol=symbol)
                if float(posiciones['result']['list'][0]['size']) != 0:

                    if symbol not in opened_positions:
                        opened_positions.append(symbol)

                    logger("Hay una posicion abierta en " + symbol)
                    if not verificar_posicion_abierta(symbol):
                        logger(f"{symbol}: verifico posicion abierta con detalles: {verificar_posicion_abierta_details(symbol)}")

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
                                
                    else:
                        logger(f"Hay una posicion abierta en {symbol} espero 60 segundos")
                        time.sleep(60)
                else:

                    if symbol in opened_positions:
                        opened_positions.remove(symbol)


                    with config_lock:
                        if len(opened_positions) >= max_ops:
                            logger(f"Se alcanzó el límite de posiciones abiertas | {max_ops}.")
                            time.sleep(60)
                            continue


                    # Obtener datos historicos
                    datam = obtener_datos_historicos(symbol, timeframe)
                    # Calcular bandas de bollinger
                    data = calcular_bandas_bollinger(datam)
                    # Calcular RSI
                    # ema20 = calcular_ema(datam[4], ventana=20)
                    rsi = calcular_rsi_talib(datam[4], window=14)

                    open_prices = np.array(datam[1])
                    high_prices = np.array(datam[2])
                    low_prices = np.array(datam[3])
                    close_prices = np.array(datam[4])

                    ticker = client.get_tickers(category='linear', symbol=symbol)
                    precio = float(ticker['result']['list'][0]['lastPrice'])
                    price24hPcnt = float(ticker['result']['list'][0]['price24hPcnt']) * 100
                    openInterest = float(ticker['result']['list'][0]['openInterest'])
                    fundingRate = float(ticker['result']['list'][0]['fundingRate'])
                    macd1, macdsignal1, macdhist1, macd2, macdsignal2, macdhist2= calcular_macd(close_prices)

                    cci = calcular_cci(high_prices, low_prices, close_prices)

                    # # Calcular soporte y resistencia
                    # soporte, resistencia, sr =  0, 0, 0

                    # if timeframe == 5:
                    #     soporte, resistencia = detectar_soportes_resistencias(high_prices, low_prices, period=50)
                    # if timeframe == 240:
                    #     soporte, resistencia = detectar_soportes_resistencias(high_prices, low_prices, period=20)

                    # if timeframe != 5 and timeframe != 240:
                    #     soporte, resistencia = detectar_soportes_resistencias(high_prices, low_prices, period=100)

                    # Llamar a la función para detectar cambio de tendencia
                    tendencia = detectar_cambio_tendencia(open_prices, high_prices, low_prices, close_prices)
                    tendencia2 = detectar_tendencia_bb_cci(high_prices, low_prices, close_prices)
                    
                    log_message = f"{symbol:<18} Price: {precio:<15.5f}\tp24h: {price24hPcnt:<3.2f}\t{str(precio >= data['UpperBand']):<5}\t{str(precio <= data['LowerBand']):<5}\tBB_W: {data['BB_Width_%']:<3.0f}\tRSI: {rsi:<3.0f}\tt1:{tendencia:<2}\tt2:{tendencia2:<2}"
                    logger(log_message)
                    
                    #timeframe;date;symbol;price;price24hPcnt;fundingRate;UpperBand;LowerBand;UpperBandCross;LowerBandCross;BB_Width_%;openInterest;rsi;cci;tendencia;tendencia2,macd1, macdsignal1, macdhist1, macd2, macdsignal2, macdhist2
                    t_log_message = f"{symbol};{precio:.5f};{price24hPcnt:.2f};{fundingRate:.4f};{data['UpperBand']:.5f};{data['LowerBand']:.5f};{precio >= data['UpperBand']};{precio <= data['LowerBand']};{data['BB_Width_%']:.2f};{openInterest:.0f};{rsi:.2f};{cci:.0f};{tendencia};{tendencia2};{macd1:.5f};{macdsignal1:.5f};{macdhist1:.5f};{macd2:.5f};{macdsignal2:.5f};{macdhist2:.5f}"
                    t_logger(t_log_message)

                    bb_width = data['BB_Width_%']
                    if bb_width < Bollinger_bands_width:
                        time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                        continue;
                        
                    if precio > data['UpperBand'] and rsi > top_rsi:

                        if len(opened_positions_short) >= max_ops_short:
                            logger(f"{symbol:<18} operaciones abiertas en short {len(opened_positions_short)} | maximo configurado es {max_ops_short}.")
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        # Datos de la moneda precio y pasos.
                        step = client.get_instruments_info(category="linear", symbol=symbol)
                        precision_step = float(step['result']['list'][0]["lotSizeFilter"]["qtyStep"])

                        saldo_usdt = obtener_saldo_usdt()
                        usdt = saldo_usdt * (account_percentage / 100)
                        if usdt < 10:
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        precision = precision_step
                        qty = usdt / precio
                        qty = qty_precision(qty, precision)
                        if qty.is_integer():
                            qty = int(qty)
                        logger(f"{symbol} Cantidad de monedas a vender: " + str(qty))
                        #analizar_posible_orden(symbol, "Sell", "Market", qty, data, rsi)
                        analizar_posible_orden_patron_velas(symbol, "Sell", "Market", qty, data, rsi)

                    if precio < data['LowerBand'] and rsi < bottom_rsi:

                        if len(opened_positions_long) >= max_ops_long:
                            logger(f"{symbol:<18} operaciones abiertas en long {len(opened_positions_long)} | maximo configurado es {max_ops_long}.")
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        # Datos de la moneda precio y pasos.
                        step = client.get_instruments_info(category="linear", symbol=symbol)
                        precision_step = float(step['result']['list'][0]["lotSizeFilter"]["qtyStep"])

                        saldo_usdt = obtener_saldo_usdt()
                        usdt = saldo_usdt * (account_percentage / 100)

                        if usdt < 10:
                            continue

                        precision = precision_step
                        qty = usdt / precio
                        qty = qty_precision(qty, precision)
                        if qty.is_integer():
                            qty = int(qty)
                        logger(f"{symbol} Cantidad de monedas a comprar: " + str(qty))
                        # analizar_posible_orden(symbol, "Buy", "Market", qty, data, rsi)
                        analizar_posible_orden_patron_velas(symbol, "Buy", "Market", qty, data, rsi)

            except Exception as e:
                logger(f"Error en el bot {symbol}: {e}")
                time.sleep(60)

         time.sleep(random.randint(sleep_rand_from, sleep_rand_to))


reload_config_process = threading.Thread(target=reload_config)
reload_config_process.start()

# Lista de otros símbolos a buscar
otros_simbolos = obtener_simbolos_mayor_volumen(cnt_symbols)

hilos = []
for simbolo in otros_simbolos:
    hilo = threading.Thread(target=operar, args=([simbolo],))
    hilos.append(hilo)
    hilo.start()



# # Crear una cola para gestionar las tareas
# task_queue = queue.Queue()

# # Definir una función para procesar las tareas de la cola
# def procesar_tareas():
#     while True:
#         simbolo = task_queue.get()
#         if simbolo is None:
#             break

#         print(f"Procesando tarea para {simbolo}")
#         operar([simbolo])
#         task_queue.task_done()

# # Crear un ThreadPoolExecutor con un número fijo de hilos
# num_workers = 10
# with ThreadPoolExecutor(max_workers=num_workers) as executor:
#     # Enviar tareas al pool de hilos
#     for _ in range(num_workers):
#         executor.submit(procesar_tareas)

#     # Añadir los símbolos a la cola de tareas
#     otros_simbolos = obtener_simbolos_mayor_volumen(cnt_symbols)
#     # otros_simbolos = obtener_simbolos_mayor_open_interest(cnt_symbols)
#     for simbolo in otros_simbolos:
#         task_queue.put(simbolo)

#     # Esperar a que todas las tareas se completen
#     task_queue.join()


