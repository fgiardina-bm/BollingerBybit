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
from config import reload_config
from sr import *

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
    global max_ops_long, max_ops_short, account_usdt_limit

    logger(f"Operando con un % de saldo de {account_percentage} primera operacion {saldo_usdt_inicial * (account_percentage / 100)}")

    while True:

         for symbol in simbolos:
            try:
                # reload_config()
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

                    if len(opened_positions) >= max_ops:
                        logger(f"Se alcanzó el límite de posiciones abiertas | {max_ops}.")
                        time.sleep(60)
                        continue


                    # Obtener datos historicos
                    datam = obtener_datos_historicos(symbol, timeframe)
                    # Calcular bandas de bollinger
                    data = calcular_bandas_bollinger(datam)
                    # Calcular RSI
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
                    
                    log_message = f"{symbol:<18} Price: {precio:<15.5f}\tp24h: {price24hPcnt:<3.2f}\t{str(precio >= data['UpperBand']):<5}\t{str(precio <= data['LowerBand']):<5}\tBB_W: {data['BB_Width_%']:<3.0f}\tRSI: {rsi:<3.0f}\tt1:{tendencia:<2}\tt2:{tendencia2:<2}\tBBW: {Bollinger_bands_width}\tmon: {monitoring}"
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
                        if saldo_usdt < account_usdt_limit:
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

                        if saldo_usdt < account_usdt_limit:
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

def operar2(simbolos):
    global opened_positions, opened_positions_short, opened_positions_long
    global saldo_usdt_inicial
    global api_key, api_secret, timeframe, tp_porcent, sl_porcent, cnt_symbols
    global account_percentage, top_rsi, bottom_rsi, sleep_rand_from, sleep_rand_to
    global sl_callback_percentage, verify_rsi, Bollinger_bands_width, monitoring, max_ops
    global opened_positions_long, opened_positions_short
    global max_ops_long, max_ops_short,account_usdt_limit

    logger(f"Operando con un % de saldo de {account_percentage} primera operacion {saldo_usdt_inicial * (account_percentage / 100)}")

    while True:

         for symbol in simbolos:
            try:
                # reload_config()
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
                            result_sl = establecer_stop_loss2(symbol, stop_loss_price)
                            result_tp = establecer_take_profit2(symbol,take_profit_price, "Sell")
                            if result_sl and result_tp:
                                logger(f"{symbol} Stop loss y take profit activados")
                            
                        else:
                            stop_loss_price = precio_de_entrada * (1 + sl_porcent / 100)
                            take_profit_price = precio_de_entrada * (1 - tp_porcent / 100)
                            result_sl = establecer_stop_loss2(symbol, stop_loss_price)
                            result_tp = establecer_take_profit2(symbol, take_profit_price, "Buy")
                            if result_sl and result_tp:
                                logger(f"{symbol} Stop loss y take profit activados")
                                
                    else:
                        logger(f"Hay una posicion abierta en {symbol} espero 60 segundos")
                        time.sleep(60)
                else:

                    if symbol in opened_positions:
                        opened_positions.remove(symbol)

                    if len(opened_positions) >= max_ops:
                        logger(f"Se alcanzó el límite de posiciones abiertas | {max_ops}.")
                        time.sleep(60)
                        continue


                    # Obtener datos historicos
                    datam = obtener_datos_historicos(symbol, timeframe)
                   
                    open_prices = np.array(datam[1])
                    high_prices = np.array(datam[2])
                    low_prices = np.array(datam[3])
                    close_prices = np.array(datam[4])

                    ticker = client.get_tickers(category='linear', symbol=symbol)
                    precio = float(ticker['result']['list'][0]['lastPrice'])
                    price24hPcnt = float(ticker['result']['list'][0]['price24hPcnt']) * 100
                    
                    ipatron_velas_martillo_bajista = patron_velas_martillo_bajista(open_prices, high_prices, low_prices, close_prices)
                    ipatron_velas_martillo_alcista = patron_velas_martillo_alcista(open_prices, high_prices, low_prices, close_prices)

                    rsi = talib.RSI(close_prices, timeperiod=14)

                    log_message = f"{symbol:<18} Price: {precio:<15.5f}\tp24h: {price24hPcnt:<3.2f}\trsi: {rsi[-1]:.1f}\tbajista: {ipatron_velas_martillo_bajista}\talcista: {ipatron_velas_martillo_alcista}"
                    logger(log_message)
                
                        
                    if ipatron_velas_martillo_bajista:

                        if len(opened_positions_short) >= max_ops_short:
                            logger(f"{symbol:<18} operaciones abiertas en short {len(opened_positions_short)} | maximo configurado es {max_ops_short}.")
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        # Datos de la moneda precio y pasos.
                        step = client.get_instruments_info(category="linear", symbol=symbol)
                        precision_step = float(step['result']['list'][0]["lotSizeFilter"]["qtyStep"])

                        saldo_usdt = obtener_saldo_usdt()
                        usdt = saldo_usdt * (account_percentage / 100)
                        if saldo_usdt < account_usdt_limit:
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        precision = precision_step
                        qty = usdt / precio
                        qty = qty_precision(qty, precision)
                        if qty.is_integer():
                            qty = int(qty)
                        logger(f"{symbol} Cantidad de monedas a vender: " + str(qty))
                        crear_orden(symbol, "Sell", "Market", qty)
                        if monitoring == 1:
                            # Iniciar el monitoreo de la operación
                            precio_entrada = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                            hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_entrada, "Sell", qty))
                            hilo_monitoreo.start()

                    if ipatron_velas_martillo_alcista:

                        if len(opened_positions_long) >= max_ops_long:
                            logger(f"{symbol:<18} operaciones abiertas en long {len(opened_positions_long)} | maximo configurado es {max_ops_long}.")
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        # Datos de la moneda precio y pasos.
                        step = client.get_instruments_info(category="linear", symbol=symbol)
                        precision_step = float(step['result']['list'][0]["lotSizeFilter"]["qtyStep"])

                        saldo_usdt = obtener_saldo_usdt()
                        usdt = saldo_usdt * (account_percentage / 100)

                        if saldo_usdt < account_usdt_limit:
                            continue

                        precision = precision_step
                        qty = usdt / precio
                        qty = qty_precision(qty, precision)
                        if qty.is_integer():
                            qty = int(qty)
                        logger(f"{symbol} Cantidad de monedas a comprar: " + str(qty))
                        crear_orden(symbol, "Buy", "Market", qty)
                        if monitoring == 1:
                            # Iniciar el monitoreo de la operación
                            precio_entrada = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                            hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_entrada, "Buy", qty))
                            hilo_monitoreo.start()

            except Exception as e:
                logger(f"Error en el bot {symbol}: {e}")
                time.sleep(60)

         time.sleep(random.randint(sleep_rand_from, sleep_rand_to))

def operar3(simbolos):
    global opened_positions, opened_positions_short, opened_positions_long
    global saldo_usdt_inicial
    global api_key, api_secret, timeframe, tp_porcent, sl_porcent, cnt_symbols
    global account_percentage, top_rsi, bottom_rsi, sleep_rand_from, sleep_rand_to
    global sl_callback_percentage, verify_rsi, Bollinger_bands_width, monitoring, max_ops
    global opened_positions_long, opened_positions_short
    global max_ops_long, max_ops_short,account_usdt_limit

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

                    if len(opened_positions) >= max_ops:
                        logger(f"Se alcanzó el límite de posiciones abiertas | {max_ops}.")
                        time.sleep(60)
                        continue


                    # Obtener datos historicos
                    datam = obtener_datos_historicos(symbol, timeframe)
                    # Calcular bandas de bollinger
                    data = calcular_bandas_bollinger(datam)
                    # Calcular RSI
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

                    cci = calcular_cci(high_prices, low_prices, close_prices)

                    # Llamar a la función para detectar cambio de tendencia
                    tendencia = detectar_cambio_tendencia(open_prices, high_prices, low_prices, close_prices)
                    
                    log_message = f"{symbol:<18} Price: {precio:<15.5f}\tp24h: {price24hPcnt:<5.2f}\t{str(precio >= data['UpperBand']):<5}\t{str(precio <= data['LowerBand']):<5}\tBB_W: {data['BB_Width_%']:<3.0f}\tRSI: {rsi:<3.0f}\tstrategy: {strategy}"
                    logger(log_message)
                    
                    #timeframe;date;symbol;price;price24hPcnt;fundingRate;UpperBand;LowerBand;UpperBandCross;LowerBandCross;BB_Width_%;openInterest;rsi;cci;tendencia;tendencia2,macd1, macdsignal1, macdhist1, macd2, macdsignal2, macdhist2
                    t_log_message = f"{symbol};{precio:.5f};{price24hPcnt:.2f};{fundingRate:.4f};{data['UpperBand']:.5f};{data['LowerBand']:.5f};{precio >= data['UpperBand']};{precio <= data['LowerBand']};{data['BB_Width_%']:.2f};{openInterest:.0f};{rsi:.2f};{cci:.0f};{tendencia}"
                    t_logger(t_log_message)

                    bb_width = data['BB_Width_%']
                    if bb_width < Bollinger_bands_width:
                        time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                        continue;
                        
                    if precio >= data['UpperBand'] and rsi >= top_rsi:
                        logger(f"{symbol} {precio > data['LowerBand']} {rsi} {top_rsi}")
                        if len(opened_positions_short) >= max_ops_short:
                            logger(f"{symbol:<18} operaciones abiertas en short {len(opened_positions_short)} | maximo configurado es {max_ops_short}.")
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        # Datos de la moneda precio y pasos.
                        step = client.get_instruments_info(category="linear", symbol=symbol)
                        precision_step = float(step['result']['list'][0]["lotSizeFilter"]["qtyStep"])

                        saldo_usdt = obtener_saldo_usdt()
                        usdt = saldo_usdt * (account_percentage / 100)
                        logger(f"saldo_usdt: {saldo_usdt} usdt: {usdt}")
                        if saldo_usdt < account_usdt_limit:
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        precision = precision_step
                        qty = usdt / precio
                        qty = qty_precision(qty, precision)
                        if qty.is_integer():
                            qty = int(qty)
                        logger(f"{symbol} Cantidad de monedas a vender: " + str(qty))
                        analizar_posible_orden_macd_syr(symbol, "Sell", "Market", qty, data, rsi)

                    if precio <= data['LowerBand'] and rsi <= bottom_rsi:
                        logger(f"{symbol} {precio < data['LowerBand']} {rsi} {bottom_rsi}")
                        if len(opened_positions_long) >= max_ops_long:
                            logger(f"{symbol:<18} operaciones abiertas en long {len(opened_positions_long)} | maximo configurado es {max_ops_long}.")
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        
                        # Datos de la moneda precio y pasos.
                        step = client.get_instruments_info(category="linear", symbol=symbol)
                        precision_step = float(step['result']['list'][0]["lotSizeFilter"]["qtyStep"])

                        saldo_usdt = obtener_saldo_usdt()
                        usdt = saldo_usdt * (account_percentage / 100)
                        logger(f"saldo_usdt: {saldo_usdt} usdt: {usdt}")
                        if saldo_usdt < account_usdt_limit:
                            continue

                        precision = precision_step
                        qty = usdt / precio
                        qty = qty_precision(qty, precision)
                        if qty.is_integer():
                            qty = int(qty)
                        logger(f"{symbol} Cantidad de monedas a comprar: " + str(qty))
                        analizar_posible_orden_macd_syr(symbol, "Buy", "Market", qty, data, rsi)

            except Exception as e:
                logger(f"Error en el bot {symbol}: {e}")
                time.sleep(60)

         time.sleep(random.randint(sleep_rand_from, sleep_rand_to))

def operar4(simbolos):
    global opened_positions, opened_positions_short, opened_positions_long
    global saldo_usdt_inicial
    global api_key, api_secret, timeframe, tp_porcent, sl_porcent, cnt_symbols
    global account_percentage, top_rsi, bottom_rsi, sleep_rand_from, sleep_rand_to
    global sl_callback_percentage, verify_rsi, Bollinger_bands_width, monitoring, max_ops
    global opened_positions_long, opened_positions_short
    global max_ops_long, max_ops_short,account_usdt_limit

    logger(f"Operando con un % de saldo de {account_percentage} primera operacion {saldo_usdt_inicial * (account_percentage / 100)}")

    while True:

         for symbol in simbolos:
            try:
                # reload_config()
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
                            result_sl = establecer_stop_loss2(symbol, stop_loss_price)
                            result_tp = establecer_take_profit2(symbol,take_profit_price, "Sell")
                            if result_sl and result_tp:
                                logger(f"{symbol} Stop loss y take profit activados")
                            
                        else:
                            stop_loss_price = precio_de_entrada * (1 + sl_porcent / 100)
                            take_profit_price = precio_de_entrada * (1 - tp_porcent / 100)
                            result_sl = establecer_stop_loss2(symbol, stop_loss_price)
                            result_tp = establecer_take_profit2(symbol, take_profit_price, "Buy")
                            if result_sl and result_tp:
                                logger(f"{symbol} Stop loss y take profit activados")
                                
                    else:
                        logger(f"Hay una posicion abierta en {symbol} espero 60 segundos")
                        time.sleep(60)
                else:

                    if symbol in opened_positions:
                        opened_positions.remove(symbol)

                    if len(opened_positions) >= max_ops:
                        logger(f"Se alcanzó el límite de posiciones abiertas | {max_ops}.")
                        time.sleep(60)
                        continue


                    # Obtener datos historicos
                    datam = obtener_datos_historicos(symbol, timeframe)
                   
                    open_prices = np.array(datam[1])
                    high_prices = np.array(datam[2])
                    low_prices = np.array(datam[3])
                    close_prices = np.array(datam[4])

                    ticker = client.get_tickers(category='linear', symbol=symbol)
                    precio = float(ticker['result']['list'][0]['lastPrice'])
                    price24hPcnt = float(ticker['result']['list'][0]['price24hPcnt']) * 100
                    
                    rsi = talib.RSI(close_prices, timeperiod=14)

                    log_message = f"{symbol:<18} Price: {precio:<15.5f}\tp24h: {price24hPcnt:<3.2f}\trsi: {rsi[-1]:.1f}"
                    logger(log_message)
                
                    data = calcular_bandas_bollinger(datam)
                    bb_width = data['BB_Width_%']
                    if bb_width < Bollinger_bands_width:
                        time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                        continue;
                        
                    if macd_bajista(np.array(datam[4])):
                    # if macd_alcista(np.array(datam[4])):

                        if len(opened_positions_short) >= max_ops_short:
                            logger(f"{symbol:<18} operaciones abiertas en short {len(opened_positions_short)} | maximo configurado es {max_ops_short}.")
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        # Datos de la moneda precio y pasos.
                        step = client.get_instruments_info(category="linear", symbol=symbol)
                        precision_step = float(step['result']['list'][0]["lotSizeFilter"]["qtyStep"])

                        saldo_usdt = obtener_saldo_usdt()
                        usdt = saldo_usdt * (account_percentage / 100)
                        if saldo_usdt < account_usdt_limit:
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        precision = precision_step
                        qty = usdt / precio
                        qty = qty_precision(qty, precision)
                        if qty.is_integer():
                            qty = int(qty)
                        logger(f"{symbol} Cantidad de monedas a vender: " + str(qty))
                        crear_orden(symbol, "Sell", "Market", qty)
                        if monitoring == 1:
                            # Iniciar el monitoreo de la operación
                            precio_entrada = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                            time.sleep(1)
                            hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas_macd, args=(symbol, precio_entrada, "Sell", qty))
                            hilo_monitoreo.start()

                    if macd_alcista(np.array(datam[4])):
                    # if macd_bajista(np.array(datam[4])):

                        if len(opened_positions_long) >= max_ops_long:
                            logger(f"{symbol:<18} operaciones abiertas en long {len(opened_positions_long)} | maximo configurado es {max_ops_long}.")
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        # Datos de la moneda precio y pasos.
                        step = client.get_instruments_info(category="linear", symbol=symbol)
                        precision_step = float(step['result']['list'][0]["lotSizeFilter"]["qtyStep"])

                        saldo_usdt = obtener_saldo_usdt()
                        usdt = saldo_usdt * (account_percentage / 100)

                        if saldo_usdt < account_usdt_limit:
                            continue

                        precision = precision_step
                        qty = usdt / precio
                        qty = qty_precision(qty, precision)
                        if qty.is_integer():
                            qty = int(qty)
                        logger(f"{symbol} Cantidad de monedas a comprar: " + str(qty))
                        crear_orden(symbol, "Buy", "Market", qty)
                        if monitoring == 1:
                            # Iniciar el monitoreo de la operación
                            time.sleep(1)
                            precio_entrada = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                            hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas_macd, args=(symbol, precio_entrada, "Buy", qty))
                            hilo_monitoreo.start()

            except Exception as e:
                logger(f"Error en el bot {symbol}: {e}")
                time.sleep(60)

         time.sleep(random.randint(sleep_rand_from, sleep_rand_to))


def operar5(simbolos):
    global opened_positions, opened_positions_short, opened_positions_long
    global saldo_usdt_inicial
    global api_key, api_secret, timeframe, tp_porcent, sl_porcent, cnt_symbols
    global account_percentage, top_rsi, bottom_rsi, sleep_rand_from, sleep_rand_to
    global sl_callback_percentage, verify_rsi, Bollinger_bands_width, monitoring, max_ops
    global opened_positions_long, opened_positions_short
    global max_ops_long, max_ops_short,account_usdt_limit

    logger(f"Operando con un % de saldo de {account_percentage} primera operacion {saldo_usdt_inicial * (account_percentage / 100)}")

    while True:

         for symbol in simbolos:
            try:
                # reload_config()
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
                            result_sl = establecer_stop_loss2(symbol, stop_loss_price)
                            result_tp = establecer_take_profit2(symbol,take_profit_price, "Sell")
                            if result_sl and result_tp:
                                logger(f"{symbol} Stop loss y take profit activados")
                            
                        else:
                            stop_loss_price = precio_de_entrada * (1 + sl_porcent / 100)
                            take_profit_price = precio_de_entrada * (1 - tp_porcent / 100)
                            result_sl = establecer_stop_loss2(symbol, stop_loss_price)
                            result_tp = establecer_take_profit2(symbol, take_profit_price, "Buy")
                            if result_sl and result_tp:
                                logger(f"{symbol} Stop loss y take profit activados")
                                
                    else:
                        logger(f"Hay una posicion abierta en {symbol} espero 60 segundos")
                        time.sleep(60)
                else:

                    if symbol in opened_positions:
                        opened_positions.remove(symbol)

                    if len(opened_positions) >= max_ops:
                        logger(f"Se alcanzó el límite de posiciones abiertas | {max_ops}.")
                        time.sleep(60)
                        continue


                    # Obtener datos historicos
                    datam = obtener_datos_historicos(symbol, timeframe)
                   
                    open_prices = np.array(datam[1])
                    high_prices = np.array(datam[2])
                    low_prices = np.array(datam[3])
                    close_prices = np.array(datam[4])

                    ticker = client.get_tickers(category='linear', symbol=symbol)
                    precio = float(ticker['result']['list'][0]['lastPrice'])
                    price24hPcnt = float(ticker['result']['list'][0]['price24hPcnt']) * 100
                    
                    ipatron_velas_martillo_bajista = is_strong_bearish_signal(open_prices, high_prices, low_prices, close_prices)
                    ipatron_velas_martillo_alcista = is_strong_bullish_signal(open_prices, high_prices, low_prices, close_prices)

                    rsi = talib.RSI(close_prices, timeperiod=14)

                    log_message = f"{symbol:<18} Price: {precio:<15.5f}\tp24h: {price24hPcnt:<3.2f}\trsi: {rsi[-1]:.1f}\tbajista: {ipatron_velas_martillo_bajista}\talcista: {ipatron_velas_martillo_alcista}"
                    logger(log_message)
                
                        
                    if ipatron_velas_martillo_bajista:

                        if len(opened_positions_short) >= max_ops_short:
                            logger(f"{symbol:<18} operaciones abiertas en short {len(opened_positions_short)} | maximo configurado es {max_ops_short}.")
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        # Datos de la moneda precio y pasos.
                        step = client.get_instruments_info(category="linear", symbol=symbol)
                        precision_step = float(step['result']['list'][0]["lotSizeFilter"]["qtyStep"])

                        saldo_usdt = obtener_saldo_usdt()
                        usdt = saldo_usdt * (account_percentage / 100)
                        if saldo_usdt < account_usdt_limit:
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        precision = precision_step
                        qty = usdt / precio
                        qty = qty_precision(qty, precision)
                        if qty.is_integer():
                            qty = int(qty)
                        logger(f"{symbol} Cantidad de monedas a vender: " + str(qty))
                        crear_orden(symbol, "Sell", "Market", qty)
                        if monitoring == 1:
                            # Iniciar el monitoreo de la operación
                            precio_entrada = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                            hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_entrada, "Sell", qty))
                            hilo_monitoreo.start()

                    if ipatron_velas_martillo_alcista:

                        if len(opened_positions_long) >= max_ops_long:
                            logger(f"{symbol:<18} operaciones abiertas en long {len(opened_positions_long)} | maximo configurado es {max_ops_long}.")
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        # Datos de la moneda precio y pasos.
                        step = client.get_instruments_info(category="linear", symbol=symbol)
                        precision_step = float(step['result']['list'][0]["lotSizeFilter"]["qtyStep"])

                        saldo_usdt = obtener_saldo_usdt()
                        usdt = saldo_usdt * (account_percentage / 100)

                        if saldo_usdt < account_usdt_limit:
                            continue

                        precision = precision_step
                        qty = usdt / precio
                        qty = qty_precision(qty, precision)
                        if qty.is_integer():
                            qty = int(qty)
                        logger(f"{symbol} Cantidad de monedas a comprar: " + str(qty))
                        crear_orden(symbol, "Buy", "Market", qty)
                        if monitoring == 1:
                            # Iniciar el monitoreo de la operación
                            precio_entrada = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                            hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_entrada, "Buy", qty))
                            hilo_monitoreo.start()

            except Exception as e:
                logger(f"Error en el bot {symbol}: {e}")
                time.sleep(60)

         time.sleep(random.randint(sleep_rand_from, sleep_rand_to))



def operar6(simbolos):
    global opened_positions, opened_positions_short, opened_positions_long
    global saldo_usdt_inicial
    global api_key, api_secret, timeframe, tp_porcent, sl_porcent, cnt_symbols
    global account_percentage, top_rsi, bottom_rsi, sleep_rand_from, sleep_rand_to
    global sl_callback_percentage, verify_rsi, Bollinger_bands_width, monitoring, max_ops
    global opened_positions_long, opened_positions_short
    global max_ops_long, max_ops_short, sr_fib_tolerancia, sr_fib_velas,account_usdt_limit

    logger(f"Operando con un % de saldo de {account_percentage} primera operacion {saldo_usdt_inicial * (account_percentage / 100)}")

    while True:

         for symbol in simbolos:
            try:
                # reload_config()
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
                            result_sl = establecer_stop_loss2(symbol, stop_loss_price)
                            result_tp = establecer_take_profit2(symbol,take_profit_price, "Sell")
                            if result_sl and result_tp:
                                logger(f"{symbol} Stop loss y take profit activados")
                            
                        else:
                            stop_loss_price = precio_de_entrada * (1 + sl_porcent / 100)
                            take_profit_price = precio_de_entrada * (1 - tp_porcent / 100)
                            result_sl = establecer_stop_loss2(symbol, stop_loss_price)
                            result_tp = establecer_take_profit2(symbol, take_profit_price, "Buy")
                            if result_sl and result_tp:
                                logger(f"{symbol} Stop loss y take profit activados")
                                
                    else:
                        logger(f"Hay una posicion abierta en {symbol} espero 60 segundos")
                        time.sleep(60)
                else:

                    if symbol in opened_positions:
                        opened_positions.remove(symbol)

                    if len(opened_positions) >= max_ops:
                        logger(f"Se alcanzó el límite de posiciones abiertas | {max_ops}.")
                        time.sleep(60)
                        continue


                    # Obtener datos historicos
                    datam = obtener_datos_historicos(symbol, timeframe)
                   
                    open_prices = np.array(datam[1])
                    high_prices = np.array(datam[2])
                    low_prices = np.array(datam[3])
                    close_prices = np.array(datam[4])
                    volumes = np.array(datam[5])

                    data = calcular_bandas_bollinger(datam)
                    bb_width = data['BB_Width_%']
                    if bb_width < Bollinger_bands_width:
                        time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                        continue;
                        

                    # Crear un DataFrame de pandas con los datos
                    df = pd.DataFrame({
                        'open': open_prices,
                        'high': high_prices,
                        'low': low_prices,
                        'close': close_prices,
                        'volume': volumes
                    })

                    ticker = client.get_tickers(category='linear', symbol=symbol)
                    precio = float(ticker['result']['list'][0]['lastPrice'])
                    price24hPcnt = float(ticker['result']['list'][0]['price24hPcnt']) * 100
                    
                    patron_confirmado_bajista, cerca_soporte,cerca_resistencia,volumen_aumento,cerca_fib = confirmar_patron_con_soporte_resistencia(symbol, df, 'bajista', sr_fib_velas, sr_fib_tolerancia)
                    patron_confirmado_alcista, cerca_soporte,cerca_resistencia,volumen_aumento,cerca_fib = confirmar_patron_con_soporte_resistencia(symbol, df, 'alcista', sr_fib_velas, sr_fib_tolerancia)

                    rsi = talib.RSI(close_prices, timeperiod=14)

                    log_message = f"{symbol:<18} Price: {precio:<15.5f}\tp24h: {price24hPcnt:<3.2f}\trsi: {rsi[-1]:.1f}\tbajista: {patron_confirmado_bajista}\talcista: {patron_confirmado_alcista}\ts:{cerca_soporte},r:{cerca_resistencia},v:{volumen_aumento},f:{cerca_fib}"
                    logger(log_message)
                
                        
                    if patron_confirmado_bajista and rsi[-1] > top_rsi:

                        if len(opened_positions_short) >= max_ops_short:
                            logger(f"{symbol:<18} operaciones abiertas en short {len(opened_positions_short)} | maximo configurado es {max_ops_short}.")
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        # Datos de la moneda precio y pasos.
                        step = client.get_instruments_info(category="linear", symbol=symbol)
                        precision_step = float(step['result']['list'][0]["lotSizeFilter"]["qtyStep"])

                        saldo_usdt = obtener_saldo_usdt()
                        usdt = saldo_usdt * (account_percentage / 100)
                        if saldo_usdt < account_usdt_limit:
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        precision = precision_step
                        qty = usdt / precio
                        qty = qty_precision(qty, precision)
                        if qty.is_integer():
                            qty = int(qty)
                        logger(f"{symbol} Cantidad de monedas a vender: " + str(qty))
                        crear_orden(symbol, "Sell", "Market", qty)
                        if monitoring == 1:
                            # Iniciar el monitoreo de la operación
                            precio_entrada = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                            hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_entrada, "Sell", qty))
                            hilo_monitoreo.start()

                    if patron_confirmado_alcista and rsi[-1] < bottom_rsi:

                        if len(opened_positions_long) >= max_ops_long:
                            logger(f"{symbol:<18} operaciones abiertas en long {len(opened_positions_long)} | maximo configurado es {max_ops_long}.")
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        # Datos de la moneda precio y pasos.
                        step = client.get_instruments_info(category="linear", symbol=symbol)
                        precision_step = float(step['result']['list'][0]["lotSizeFilter"]["qtyStep"])

                        saldo_usdt = obtener_saldo_usdt()
                        usdt = saldo_usdt * (account_percentage / 100)

                        if saldo_usdt < account_usdt_limit:
                            continue

                        precision = precision_step
                        qty = usdt / precio
                        qty = qty_precision(qty, precision)
                        if qty.is_integer():
                            qty = int(qty)
                        logger(f"{symbol} Cantidad de monedas a comprar: " + str(qty))
                        crear_orden(symbol, "Buy", "Market", qty)
                        if monitoring == 1:
                            # Iniciar el monitoreo de la operación
                            precio_entrada = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                            hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_entrada, "Buy", qty))
                            hilo_monitoreo.start()

            except Exception as e:
                logger(f"Error en el bot {symbol}: {e}")
                time.sleep(60)

         time.sleep(random.randint(sleep_rand_from, sleep_rand_to))


def operar7(simbolos,sr):
    global opened_positions, opened_positions_short, opened_positions_long
    global saldo_usdt_inicial
    global api_key, api_secret, timeframe, tp_porcent, sl_porcent, cnt_symbols
    global account_percentage, top_rsi, bottom_rsi, sleep_rand_from, sleep_rand_to
    global sl_callback_percentage, verify_rsi, Bollinger_bands_width, monitoring, max_ops
    global opened_positions_long, opened_positions_short
    global max_ops_long, max_ops_short, sr_fib_tolerancia, sr_fib_velas,account_usdt_limit, order_book_limit, order_book_delay_divisor

    logger(f"Operando con un % de saldo de {account_percentage} primera operacion {saldo_usdt_inicial * (account_percentage / 100)}")

    bucle_cnt = 0
    while True:
         bucle_cnt += 1 
         for symbol in simbolos:
            try:
                # reload_config()
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
                            result_sl = establecer_stop_loss2(symbol, stop_loss_price)
                            result_tp = establecer_take_profit2(symbol,take_profit_price, "Sell")
                            if result_sl and result_tp:
                                logger(f"{symbol} Stop loss y take profit activados")
                            
                        else:
                            stop_loss_price = precio_de_entrada * (1 + sl_porcent / 100)
                            take_profit_price = precio_de_entrada * (1 - tp_porcent / 100)
                            result_sl = establecer_stop_loss2(symbol, stop_loss_price)
                            result_tp = establecer_take_profit2(symbol, take_profit_price, "Buy")
                            if result_sl and result_tp:
                                logger(f"{symbol} Stop loss y take profit activados")
                                
                    else:
                        logger(f"Hay una posicion abierta en {symbol} espero 60 segundos")
                        time.sleep(60)
                else:

                    if symbol in opened_positions:
                        opened_positions.remove(symbol)

                    if len(opened_positions) >= max_ops:
                        logger(f"Se alcanzó el límite de posiciones abiertas | {max_ops}.")
                        time.sleep(60)
                        continue


                    # Obtener datos historicos
                    datam = obtener_datos_historicos(symbol, timeframe)
                   
                    open_prices = np.array(datam[1])
                    high_prices = np.array(datam[2])
                    low_prices = np.array(datam[3])
                    close_prices = np.array(datam[4])
                    volumes = np.array(datam[5])

                    data = calcular_bandas_bollinger(datam)
                    bb_width = data['BB_Width_%']
                    if bb_width < Bollinger_bands_width:
                        time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                        continue;
                        

                    # Crear un DataFrame de pandas con los datos
                    df = pd.DataFrame({
                        'open': open_prices,
                        'high': high_prices,
                        'low': low_prices,
                        'close': close_prices,
                        'volume': volumes
                    })

                    ticker = client.get_tickers(category='linear', symbol=symbol)
                    precio = float(ticker['result']['list'][0]['lastPrice'])
                    price24hPcnt = float(ticker['result']['list'][0]['price24hPcnt']) * 100
                    buy_volume = float(ticker['result']['list'][0]['bid1Size'])
                    sell_volume = float(ticker['result']['list'][0]['ask1Size'])
                    delta_volume = buy_volume - sell_volume

                    if bucle_cnt >= random.randint(200, 300):
                        sr = get_syr(symbol)
                        bucle_cnt = 0

                    sma_50 = df['close'].rolling(window=50).mean()
                    sma_200 = df['close'].rolling(window=200).mean()
                    
                    df['ADX'] = talib.ADX(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)
                    fuerte_tendencia = df['ADX'].iloc[-1] > 25 

                    patron_confirmado_bajista, cerca_soporte_resistencia,volumen_aumento,price_in_bollinger,UpperBandDiff,LowerBandDiff,UpperTolerance,LowerTolerance = confirmar_patron_con_soporte_resistencia_3niveles(symbol, df, 'bajista', sr , data, sr_fib_velas, sr_fib_tolerancia)
                    patron_confirmado_alcista, cerca_soporte_resistencia,volumen_aumento,price_in_bollinger,UpperBandDiff,LowerBandDiff,UpperTolerance,LowerTolerance = confirmar_patron_con_soporte_resistencia_3niveles(symbol, df, 'alcista', sr, data, sr_fib_velas, sr_fib_tolerancia)

                    rsi = talib.RSI(close_prices, timeperiod=14)


                    log_message = f"{symbol:<18} Price: {precio:<15.5f}\trsi: {rsi[-1]:<3.0f}\tb:{patron_confirmado_bajista:<5}\ta:{patron_confirmado_alcista:<5}\tsr:{cerca_soporte_resistencia:<5}|v:{volumen_aumento:<5}|pb:{price_in_bollinger:<5}|{sma_50.iloc[-1] > sma_200.iloc[-1]}|{sma_50.iloc[-1]:<3.5f}|{sma_200.iloc[-1]:<3.5f}|{fuerte_tendencia}"
                    logger(log_message)
                
                        
                    if patron_confirmado_bajista and rsi[-1] > top_rsi:

                        if len(opened_positions_short) >= max_ops_short:
                            logger(f"{symbol:<18} operaciones abiertas en short {len(opened_positions_short)} | maximo configurado es {max_ops_short}.")
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        # Datos de la moneda precio y pasos.
                        step = client.get_instruments_info(category="linear", symbol=symbol)
                        precision_step = float(step['result']['list'][0]["lotSizeFilter"]["qtyStep"])

                        saldo_usdt = obtener_saldo_usdt()
                        usdt = saldo_usdt * (account_percentage / 100)
                        if saldo_usdt < account_usdt_limit:
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        precision = precision_step
                        qty = usdt / precio
                        qty = qty_precision(qty, precision)
                        if qty.is_integer():
                            qty = int(qty)
                        logger(f"{symbol} Cantidad de monedas a vender: " + str(qty))
                        crear_orden(symbol, "Sell", "Market", qty)
                        if monitoring == 1:
                            # Iniciar el monitoreo de la operación
                            precio_entrada = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                            hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_entrada, "Sell", qty))
                            hilo_monitoreo.start()

                    if patron_confirmado_alcista and rsi[-1] < bottom_rsi:

                        if len(opened_positions_long) >= max_ops_long:
                            logger(f"{symbol:<18} operaciones abiertas en long {len(opened_positions_long)} | maximo configurado es {max_ops_long}.")
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        # Datos de la moneda precio y pasos.
                        step = client.get_instruments_info(category="linear", symbol=symbol)
                        precision_step = float(step['result']['list'][0]["lotSizeFilter"]["qtyStep"])

                        saldo_usdt = obtener_saldo_usdt()
                        usdt = saldo_usdt * (account_percentage / 100)

                        if saldo_usdt < account_usdt_limit:
                            continue

                        precision = precision_step
                        qty = usdt / precio
                        qty = qty_precision(qty, precision)
                        if qty.is_integer():
                            qty = int(qty)
                        logger(f"{symbol} Cantidad de monedas a comprar: " + str(qty))
                        crear_orden(symbol, "Buy", "Market", qty)
                        if monitoring == 1:
                            # Iniciar el monitoreo de la operación
                            precio_entrada = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                            hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_entrada, "Buy", qty))
                            hilo_monitoreo.start()

            except Exception as e:
                print(e)
                logger(f"Error en el bot {symbol}: {e}")
                time.sleep(60)

         time.sleep(random.randint(sleep_rand_from, sleep_rand_to))


def operar8(simbolos,sr):
    global opened_positions, opened_positions_short, opened_positions_long
    global saldo_usdt_inicial
    global api_key, api_secret, timeframe, tp_porcent, sl_porcent, cnt_symbols
    global account_percentage, top_rsi, bottom_rsi, sleep_rand_from, sleep_rand_to
    global sl_callback_percentage, verify_rsi, Bollinger_bands_width, monitoring, max_ops
    global opened_positions_long, opened_positions_short
    global max_ops_long, max_ops_short, sr_fib_tolerancia, sr_fib_velas,account_usdt_limit, order_book_limit, order_book_delay_divisor
    global sl_multiplicador, tp_multiplicador
    global sl_percentaje_account

    sop_res = sr
    logger(f"Operando con un % de saldo de {account_percentage} primera operacion {saldo_usdt_inicial * (account_percentage / 100)}")

    bucle_cnt = 0
    while True:
         bucle_cnt += 1 
         for symbol in simbolos:
            try:
                posiciones = get_opened_positions(symbol=symbol)
                if float(posiciones['result']['list'][0]['size']) != 0:

                    if symbol not in opened_positions:
                        opened_positions.append(symbol)

                    logger("Hay una posicion abierta en " + symbol)
                    if not verificar_posicion_abierta_solo_stop_loss(symbol):
                        logger(f"{symbol}: verifico posicion abierta con detalles: {verificar_posicion_abierta_details(symbol)}")

                        precio_de_entrada = float(posiciones['result']['list'][0]['avgPrice'])

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
                        
                        if posiciones['result']['list'][0]['side']  == 'Buy':
                            stop_loss_short,atr_actual,multiplicador_atr,lastprice = establecer_stop_loss_dinamico(df, sl_multiplicador, tipo_trade='long', timeframe=timeframe)
                            logger(f"{symbol} stop_loss_short: {stop_loss_short} atr_actual: {atr_actual} multiplicador_atr: {multiplicador_atr} lastprice: {lastprice}")
                            result_sl = establecer_stop_loss2(symbol, stop_loss_short)

                            if result_sl:
                                logger(f"{symbol} Stop loss activado")

                                if monitoring == 1:
                                    # Iniciar el monitoreo de la operación
                                    # Calcular el % absoluto entre stop loss y precio de entrada
                                    sl_porcentaje = abs((stop_loss_short - precio_de_entrada) / precio_de_entrada * 100)
                                    logger(f"{symbol} Porcentaje de SL: {sl_porcentaje:.2f}%")
                                    hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_de_entrada, "Buy", sl_porcentaje))
                                    hilo_monitoreo.start()
                            
                        else:
                            stop_loss_long,atr_actual,multiplicador_atr,lastprice = establecer_stop_loss_dinamico(df, sl_multiplicador, tipo_trade='short', timeframe=timeframe)
                            logger(f"{symbol} stop_loss_long: {stop_loss_long} atr_actual: {atr_actual} multiplicador_atr: {multiplicador_atr} lastprice: {lastprice}")
                            result_sl = establecer_stop_loss2(symbol, stop_loss_long)

                            if result_sl:
                                logger(f"{symbol} Stop loss activado")

                                if monitoring == 1:
                                    # Iniciar el monitoreo de la operación
                                    # Calcular el % absoluto entre stop loss y precio de entrada
                                    sl_porcentaje = abs((stop_loss_long - precio_de_entrada) / precio_de_entrada * 100)
                                    logger(f"{symbol} Porcentaje de SL: {sl_porcentaje:.2f}%")
                                    hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_de_entrada, "Sell", sl_porcentaje))
                                    hilo_monitoreo.start()
                                
                    else:
                        logger(f"Hay una posicion abierta en {symbol} espero 60 segundos")
                        time.sleep(60)
                else:

                    if symbol in opened_positions:
                        opened_positions.remove(symbol)

                    if len(opened_positions) >= max_ops:
                        logger(f"Se alcanzó el límite de posiciones abiertas | {max_ops}.")
                        time.sleep(60)
                        continue

                    if bucle_cnt < 2:
                        logger(f"no OPERAR aun | {bucle_cnt}.")
                        time.sleep(20)
                        continue

                    # Obtener datos historicos
                    datam = obtener_datos_historicos(symbol, timeframe)
                   
                    open_prices = np.array(datam[1])
                    high_prices = np.array(datam[2])
                    low_prices = np.array(datam[3])
                    close_prices = np.array(datam[4])
                    volumes = np.array(datam[5])

                    data = calcular_bandas_bollinger(datam)
                    bb_width = data['BB_Width_%']
                    if bb_width < Bollinger_bands_width:
                        time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                        continue;
                        

                    # Crear un DataFrame de pandas con los datos
                    df = pd.DataFrame({
                        'open': open_prices,
                        'high': high_prices,
                        'low': low_prices,
                        'close': close_prices,
                        'volume': volumes
                    })

                    ticker = client.get_tickers(category='linear', symbol=symbol)
                    precio = float(ticker['result']['list'][0]['lastPrice'])
                    fundingRate = float(ticker['result']['list'][0]['fundingRate'])

                    if abs(fundingRate) > 0.0015:  # 0.1% as decimal
                        logger(f"{symbol} Funding rate demasiado alto: {(fundingRate*100):.4f}, saltando")
                        time.sleep(random.randint(sleep_rand_from*2, sleep_rand_to*2))
                        continue

                    if bucle_cnt >= random.randint(100, 150):
                        sop_res = get_syr(symbol)
                        bucle_cnt = 0

                    signal_long  = detectar_reversion_alcista(df, sop_res['soportes_total'], top_rsi, bottom_rsi)
                    signal_short  = detectar_reversion_bajista(df, sop_res['resistencias_total'], top_rsi, bottom_rsi)

                    rsi = talib.RSI(close_prices, timeperiod=14)

                    # Calcular la distancia porcentual hasta el soporte más cercano
                    closest_support = None
                    min_distance_percent = float('inf')
                    if len(sop_res['soportes_total']) > 0:
                        for support in sop_res['soportes_total']:
                            distance_percent = abs(precio - support) / precio * 100
                            if distance_percent < min_distance_percent:
                                min_distance_percent = distance_percent
                                closest_support = support

                    # Calcular la distancia porcentual hasta la resistencia más cercana
                    closest_resistance = None
                    min_resistance_distance = float('inf')
                    if len(sop_res['resistencias_total']) > 0:
                        for resistance in sop_res['resistencias_total']:
                            distance_percent = abs(precio - resistance) / precio * 100
                            if distance_percent < min_resistance_distance:
                                min_resistance_distance = distance_percent
                                closest_resistance = resistance


                    log_message = f"{symbol:<18} Price: {precio:<15.5f}\trsi: {rsi[-1]:<3.1f}\tb:{signal_short.iloc[-1]}\ta:{signal_long.iloc[-1]}\tff: {(fundingRate*100):.4f}\tsupport: {min_distance_percent:.2f}%\tresistance: {min_resistance_distance:.2f}%"
                    logger(log_message)
                
                        
                    if signal_short.iloc[-1] == 1:

                        if len(opened_positions_short) >= max_ops_short:
                            logger(f"{symbol:<18} operaciones abiertas en short {len(opened_positions_short)} | maximo configurado es {max_ops_short}.")
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        # Datos de la moneda precio y pasos.
                        step = client.get_instruments_info(category="linear", symbol=symbol)
                        precision_step = float(step['result']['list'][0]["lotSizeFilter"]["qtyStep"])

                        saldo_usdt = obtener_saldo_usdt()
                        usdt = saldo_usdt * (account_percentage / 100)
                        if saldo_usdt < account_usdt_limit:
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        # Calcular ATR para ajustar el tamaño de la posición
                        atr = talib.ATR(high_prices, low_prices, close_prices, timeperiod=14)
                        atr_actual = atr[-1]
                        logger(f"{symbol} ATR actual: {atr_actual:.5f}")

                        # Ajustar el importe de USDT según el ATR
                        # Si el ATR es muy grande, reducimos la exposición para limitar el riesgo
                        max_atr_riesgo = precio * 0.03  # Considera un 3% como ATR de referencia
                        logger(f"{symbol} ATR máximo permitido: {max_atr_riesgo:.5f}")
                        if atr_actual > max_atr_riesgo:
                            # Reducir el importe proporcionalmente al exceso de ATR
                            factor_reduccion = max_atr_riesgo / atr_actual
                            usdt = usdt * factor_reduccion
                            logger(f"{symbol} ATR elevado: {atr_actual:.5f}, reduciendo posición por factor: {factor_reduccion:.2f}")

                        # Calcular el stop loss y verificar máxima pérdida
                        stop_loss_estimado, _, _, _ = establecer_stop_loss_dinamico(df, sl_multiplicador, tipo_trade='short', timeframe=timeframe)
                        max_perdida_permitida = saldo_usdt * (sl_percentaje_account /  100)  # Máximo 2% del saldo total
                        perdida_estimada = abs((precio - stop_loss_estimado) * (usdt / precio))
                        logger(f"{symbol} Pérdida estimada: {perdida_estimada:.2f} USDT")
                        logger(f"{symbol} Pérdida máxima permitida: {max_perdida_permitida:.2f} USDT")

                        if perdida_estimada > max_perdida_permitida:
                            factor_reduccion = max_perdida_permitida / perdida_estimada
                            usdt = usdt * factor_reduccion
                            logger(f"{symbol} Reduciendo posición para limitar pérdida: {perdida_estimada:.2f} USDT a {max_perdida_permitida:.2f} USDT")

                        logger(f"{symbol} usdt final a invertir: {usdt}")

                        if usdt < 5:
                            logger(f"{symbol} Posición insuficiente para operar usdt: {usdt}")
                            continue
                        
                        precision = precision_step
                        qty = usdt / precio
                        qty = qty_precision(qty, precision)
                        if qty.is_integer():
                            qty = int(qty)
                        logger(f"{symbol} Cantidad de monedas a vender: " + str(qty))

                        stop_loss_param,_,_,_ = establecer_stop_loss_dinamico(df, sl_multiplicador, tipo_trade='short', timeframe=timeframe)
                        take_profit_param,_,_,_ = establecer_take_profit_dinamico(df, tp_multiplicador, tipo_trade='short', timeframe=timeframe)
                        crear_orden_con_stoploss_takeprofit(symbol, "Sell", "Market", qty,stop_loss_param,take_profit_param)
                        if monitoring == 1:
                            # Iniciar el monitoreo de la operación
                            precio_entrada = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                            # Calcular el % absoluto entre stop loss y precio de entrada
                            sl_porcentaje = abs((stop_loss_param - precio_entrada) / precio_entrada * 100)
                            logger(f"{symbol} Porcentaje de SL: {sl_porcentaje:.2f}%")
                            hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_entrada, "Sell", sl_porcentaje))
                            hilo_monitoreo.start()

                    if signal_long.iloc[-1] == 1:

                        if len(opened_positions_long) >= max_ops_long:
                            logger(f"{symbol:<18} operaciones abiertas en long {len(opened_positions_long)} | maximo configurado es {max_ops_long}.")
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        # Datos de la moneda precio y pasos.
                        step = client.get_instruments_info(category="linear", symbol=symbol)
                        precision_step = float(step['result']['list'][0]["lotSizeFilter"]["qtyStep"])

                        saldo_usdt = obtener_saldo_usdt()
                        usdt = saldo_usdt * (account_percentage / 100)

                        if saldo_usdt < account_usdt_limit:
                            continue

                        # Calcular ATR para ajustar el tamaño de la posición
                        atr = talib.ATR(high_prices, low_prices, close_prices, timeperiod=14)
                        atr_actual = atr[-1]
                        logger(f"{symbol} ATR actual: {atr_actual:.5f}")

                        # Ajustar el importe de USDT según el ATR
                        # Si el ATR es muy grande, reducimos la exposición para limitar el riesgo
                        max_atr_riesgo = precio * 0.03  # Considera un 1% como ATR de referencia
                        logger(f"{symbol} ATR máximo permitido: {max_atr_riesgo:.5f}")
                        if atr_actual > max_atr_riesgo:
                            # Reducir el importe proporcionalmente al exceso de ATR
                            factor_reduccion = max_atr_riesgo / atr_actual
                            usdt = usdt * factor_reduccion
                            logger(f"{symbol} ATR elevado: {atr_actual:.5f}, reduciendo posición por factor: {factor_reduccion:.2f}")


                        # Calcular el stop loss y verificar máxima pérdida
                        stop_loss_estimado, _, _, _ = establecer_stop_loss_dinamico(df, sl_multiplicador, tipo_trade='long', timeframe=timeframe)
                        max_perdida_permitida = saldo_usdt * (sl_percentaje_account /  100)   # Máximo 2% del saldo total
                        perdida_estimada = abs((precio - stop_loss_estimado) * (usdt / precio))
                        logger(f"{symbol} Pérdida estimada: {perdida_estimada:.2f} USDT")
                        logger(f"{symbol} Pérdida máxima permitida: {max_perdida_permitida:.2f} USDT")

                        if perdida_estimada > max_perdida_permitida:
                            factor_reduccion = max_perdida_permitida / perdida_estimada
                            usdt = usdt * factor_reduccion
                            logger(f"{symbol} Reduciendo posición para limitar pérdida: {perdida_estimada:.2f} USDT a {max_perdida_permitida:.2f} USDT")

                        logger(f"{symbol} usdt final a invertir: {usdt}")
                        
                        if usdt < 5:
                            logger(f"{symbol} Posición insuficiente para operar usdt: {usdt}")
                            continue

                        precision = precision_step
                        qty = usdt / precio
                        qty = qty_precision(qty, precision)
                        if qty.is_integer():
                            qty = int(qty)

                        logger(f"{symbol} Cantidad de monedas a comprar: " + str(qty))
                        stop_loss_param,_,_,_ = establecer_stop_loss_dinamico(df, sl_multiplicador, tipo_trade='long', timeframe=timeframe)
                        take_profit_param,_,_,_ = establecer_take_profit_dinamico(df, tp_multiplicador, tipo_trade='long', timeframe=timeframe)
                        crear_orden_con_stoploss_takeprofit(symbol, "Buy", "Market", qty,stop_loss_param,take_profit_param)

                        if monitoring == 1:
                            # Iniciar el monitoreo de la operación
                            precio_entrada = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                            # Calcular el % absoluto entre stop loss y precio de entrada
                            sl_porcentaje = abs((stop_loss_param - precio_entrada) / precio_entrada * 100)
                            logger(f"{symbol} Porcentaje de SL: {sl_porcentaje:.2f}%")
                            hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_entrada, "Buy", sl_porcentaje))
                            hilo_monitoreo.start()

            except Exception as e:
                print(e)
                logger(f"Error en el bot {symbol}: {e}")
                time.sleep(60)

         time.sleep(random.randint(sleep_rand_from, sleep_rand_to))

def operar9(simbolos):
    global opened_positions, opened_positions_short, opened_positions_long
    global saldo_usdt_inicial
    global api_key, api_secret, timeframe, tp_porcent, sl_porcent, cnt_symbols
    global account_percentage, top_rsi, bottom_rsi, sleep_rand_from, sleep_rand_to
    global sl_callback_percentage, verify_rsi, Bollinger_bands_width, monitoring, max_ops
    global opened_positions_long, opened_positions_short
    global max_ops_long, max_ops_short, sr_fib_tolerancia, sr_fib_velas,account_usdt_limit, order_book_limit, order_book_delay_divisor
    global sl_multiplicador, tp_multiplicador
    global sl_percentaje_account

    logger(f"Operando con un % de saldo de {account_percentage} primera operacion {saldo_usdt_inicial * (account_percentage / 100)}")

    bucle_cnt = 0
    while True:
         bucle_cnt += 1 
         for symbol in simbolos:
            try:
                posiciones = get_opened_positions(symbol=symbol)
                if float(posiciones['result']['list'][0]['size']) != 0:

                    if symbol not in opened_positions:
                        opened_positions.append(symbol)

                    logger("Hay una posicion abierta en " + symbol)
                    if not verificar_posicion_abierta_solo_stop_loss(symbol):
                        logger(f"{symbol}: verifico posicion abierta con detalles: {verificar_posicion_abierta_details(symbol)}")

                        precio_de_entrada = float(posiciones['result']['list'][0]['avgPrice'])

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
                        
                        if posiciones['result']['list'][0]['side']  == 'Buy':
                            stop_loss_short,atr_actual,multiplicador_atr,lastprice = establecer_stop_loss_dinamico(df, sl_multiplicador, tipo_trade='long', timeframe=timeframe)
                            logger(f"{symbol} stop_loss_short: {stop_loss_short} atr_actual: {atr_actual} multiplicador_atr: {multiplicador_atr} lastprice: {lastprice}")
                            result_sl = establecer_stop_loss2(symbol, stop_loss_short)

                            if result_sl:
                                logger(f"{symbol} Stop loss activado")

                                if monitoring == 1:
                                    # Iniciar el monitoreo de la operación
                                    # Calcular el % absoluto entre stop loss y precio de entrada
                                    sl_porcentaje = abs((stop_loss_short - precio_de_entrada) / precio_de_entrada * 100)
                                    logger(f"{symbol} Porcentaje de SL: {sl_porcentaje:.2f}%")
                                    hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_de_entrada, "Buy", sl_porcentaje))
                                    hilo_monitoreo.start()
                            
                        else:
                            stop_loss_long,atr_actual,multiplicador_atr,lastprice = establecer_stop_loss_dinamico(df, sl_multiplicador, tipo_trade='short', timeframe=timeframe)
                            logger(f"{symbol} stop_loss_long: {stop_loss_long} atr_actual: {atr_actual} multiplicador_atr: {multiplicador_atr} lastprice: {lastprice}")
                            result_sl = establecer_stop_loss2(symbol, stop_loss_long)

                            if result_sl:
                                logger(f"{symbol} Stop loss activado")

                                if monitoring == 1:
                                    # Iniciar el monitoreo de la operación
                                    # Calcular el % absoluto entre stop loss y precio de entrada
                                    sl_porcentaje = abs((stop_loss_long - precio_de_entrada) / precio_de_entrada * 100)
                                    logger(f"{symbol} Porcentaje de SL: {sl_porcentaje:.2f}%")
                                    hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_de_entrada, "Sell", sl_porcentaje))
                                    hilo_monitoreo.start()
                                
                    else:
                        logger(f"Hay una posicion abierta en {symbol} espero 300 segundos")
                        time.sleep(300)
                else:

                    if symbol in opened_positions:
                        opened_positions.remove(symbol)

                    if len(opened_positions) >= max_ops:
                        logger(f"Se alcanzó el límite de posiciones abiertas | {max_ops}.")
                        time.sleep(60)
                        continue

                    if bucle_cnt < 2:
                        logger(f"no OPERAR aun | {bucle_cnt}.")
                        time.sleep(20)
                        continue


                    # Obtener datos historicos
                    datam = obtener_datos_historicos(symbol, timeframe)
                   
                    open_prices = np.array(datam[1])
                    high_prices = np.array(datam[2])
                    low_prices = np.array(datam[3])
                    close_prices = np.array(datam[4])
                    volumes = np.array(datam[5])

                    # Crear un DataFrame de pandas con los datos
                    df = pd.DataFrame({
                        'open': open_prices,
                        'high': high_prices,
                        'low': low_prices,
                        'close': close_prices,
                        'volume': volumes
                    })

                    ticker = client.get_tickers(category='linear', symbol=symbol)
                    precio = float(ticker['result']['list'][0]['lastPrice'])
                    fundingRate = float(ticker['result']['list'][0]['fundingRate'])

                    if abs(fundingRate) > 0.0015:  # 0.1% as decimal
                        logger(f"{symbol} Funding rate demasiado alto: {(fundingRate*100):.4f}, saltando")
                        time.sleep(random.randint(sleep_rand_from*2, sleep_rand_to*2))
                        continue

    
                    ema5 = talib.EMA(close_prices, timeperiod=5)[-1]
                    ema10 = talib.EMA(close_prices, timeperiod=10)[-1]
                    
                    # Check for EMA crossover
                    previous_ema5 = talib.EMA(close_prices[:-1], timeperiod=5)[-1]
                    previous_ema10 = talib.EMA(close_prices[:-1], timeperiod=10)[-1]

                    # Long signal: EMA5 crosses above EMA10
                    signal_long = previous_ema5 <= previous_ema10 and ema5 > ema10

                    # Short signal: EMA5 crosses below EMA10
                    signal_short = previous_ema5 >= previous_ema10 and ema5 < ema10

                    # Calculate the distance to nearest support and resistance
                    rsi = talib.RSI(close_prices, timeperiod=14)[-1]

                    # Add bullish/bearish confirmation with RSI
                    # For long signals, RSI should be below bottom_rsi (oversold)
                    # For short signals, RSI should be above top_rsi (overbought)
                    signal_long = signal_long & (rsi < bottom_rsi)
                    signal_short = signal_short & (rsi > top_rsi)

                    log_message = f"{symbol:<18} Price: {precio:<15.5f}\tema5: {ema5:.3f}\tema10:{ema10:.3f}\tprevious_ema5: {(previous_ema5):.3f}\tprevious_ema10: {(previous_ema10):.3f}"
                    logger(log_message)
                
                        
                    if signal_short:

                        if len(opened_positions_short) >= max_ops_short:
                            logger(f"{symbol:<18} operaciones abiertas en short {len(opened_positions_short)} | maximo configurado es {max_ops_short}.")
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        # Datos de la moneda precio y pasos.
                        step = client.get_instruments_info(category="linear", symbol=symbol)
                        precision_step = float(step['result']['list'][0]["lotSizeFilter"]["qtyStep"])

                        saldo_usdt = obtener_saldo_usdt()
                        usdt = saldo_usdt * (account_percentage / 100)
                        if saldo_usdt < account_usdt_limit:
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        # Calcular ATR para ajustar el tamaño de la posición
                        atr = talib.ATR(high_prices, low_prices, close_prices, timeperiod=14)
                        atr_actual = atr[-1]
                        logger(f"{symbol} ATR actual: {atr_actual:.5f}")

                        # Ajustar el importe de USDT según el ATR
  
                        # Calcular el stop loss y verificar máxima pérdida
                        stop_loss_estimado, _, _, _ = establecer_stop_loss_dinamico(df, sl_multiplicador, tipo_trade='short', timeframe=timeframe)
                        max_perdida_permitida = saldo_usdt * (sl_percentaje_account /  100)  # Máximo 2% del saldo total
                        perdida_estimada = abs((precio - stop_loss_estimado) * (usdt / precio))
                        logger(f"{symbol} Pérdida estimada: {perdida_estimada:.2f} USDT")
                        logger(f"{symbol} Pérdida máxima permitida: {max_perdida_permitida:.2f} USDT")

                        if perdida_estimada > max_perdida_permitida:
                            factor_reduccion = max_perdida_permitida / perdida_estimada
                            usdt = usdt * factor_reduccion
                            logger(f"{symbol} Reduciendo posición para limitar pérdida: {perdida_estimada:.2f} USDT a {max_perdida_permitida:.2f} USDT")

                        logger(f"{symbol} usdt final a invertir: {usdt}")

                        if usdt < 5:
                            logger(f"{symbol} Posición insuficiente para operar usdt: {usdt}")
                            continue
                        
                        precision = precision_step
                        qty = usdt / precio
                        qty = qty_precision(qty, precision)
                        if qty.is_integer():
                            qty = int(qty)
                        logger(f"{symbol} Cantidad de monedas a vender: " + str(qty))

                        stop_loss_param,_,_,_ = establecer_stop_loss_dinamico(df, sl_multiplicador, tipo_trade='short', timeframe=timeframe)
                        take_profit_param,_,_,_ = establecer_take_profit_dinamico(df, tp_multiplicador, tipo_trade='short', timeframe=timeframe)
                        analizar_posible_orden_ema(symbol, "Sell", "Market", qty,stop_loss_param,take_profit_param)
                      

                    if signal_long:

                        if len(opened_positions_long) >= max_ops_long:
                            logger(f"{symbol:<18} operaciones abiertas en long {len(opened_positions_long)} | maximo configurado es {max_ops_long}.")
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        # Datos de la moneda precio y pasos.
                        step = client.get_instruments_info(category="linear", symbol=symbol)
                        precision_step = float(step['result']['list'][0]["lotSizeFilter"]["qtyStep"])

                        saldo_usdt = obtener_saldo_usdt()
                        usdt = saldo_usdt * (account_percentage / 100)

                        if saldo_usdt < account_usdt_limit:
                            continue

                        # Calcular ATR para ajustar el tamaño de la posición
                        atr = talib.ATR(high_prices, low_prices, close_prices, timeperiod=14)
                        atr_actual = atr[-1]
                        logger(f"{symbol} ATR actual: {atr_actual:.5f}")

                        # Ajustar el importe de USDT según el ATR

                        # Calcular el stop loss y verificar máxima pérdida
                        stop_loss_estimado, _, _, _ = establecer_stop_loss_dinamico(df, sl_multiplicador, tipo_trade='long', timeframe=timeframe)
                        max_perdida_permitida = saldo_usdt * (sl_percentaje_account /  100)   # Máximo 2% del saldo total
                        perdida_estimada = abs((precio - stop_loss_estimado) * (usdt / precio))
                        logger(f"{symbol} Pérdida estimada: {perdida_estimada:.2f} USDT")
                        logger(f"{symbol} Pérdida máxima permitida: {max_perdida_permitida:.2f} USDT")

                        if perdida_estimada > max_perdida_permitida:
                            factor_reduccion = max_perdida_permitida / perdida_estimada
                            usdt = usdt * factor_reduccion
                            logger(f"{symbol} Reduciendo posición para limitar pérdida: {perdida_estimada:.2f} USDT a {max_perdida_permitida:.2f} USDT")

                        logger(f"{symbol} usdt final a invertir: {usdt}")
                        
                        if usdt < 5:
                            logger(f"{symbol} Posición insuficiente para operar usdt: {usdt}")
                            continue

                        precision = precision_step
                        qty = usdt / precio
                        qty = qty_precision(qty, precision)
                        if qty.is_integer():
                            qty = int(qty)

                        logger(f"{symbol} Cantidad de monedas a comprar: " + str(qty))
                        stop_loss_param,_,_,_ = establecer_stop_loss_dinamico(df, sl_multiplicador, tipo_trade='long', timeframe=timeframe)
                        take_profit_param,_,_,_ = establecer_take_profit_dinamico(df, tp_multiplicador, tipo_trade='long', timeframe=timeframe)
                        analizar_posible_orden_ema(symbol, "Buy", "Market", qty,stop_loss_param,take_profit_param)


            except Exception as e:
                print(e)
                logger(f"Error en el bot {symbol}: {e}")
                time.sleep(60)

         time.sleep(random.randint(sleep_rand_from, sleep_rand_to))


def operar10(simbolos,sr): # nuevo calculo soporte y resistencia
    global opened_positions, opened_positions_short, opened_positions_long
    global saldo_usdt_inicial
    global api_key, api_secret, timeframe, tp_porcent, sl_porcent, cnt_symbols
    global account_percentage, top_rsi, bottom_rsi, sleep_rand_from, sleep_rand_to
    global sl_callback_percentage, verify_rsi, Bollinger_bands_width, monitoring, max_ops
    global opened_positions_long, opened_positions_short
    global max_ops_long, max_ops_short, sr_fib_tolerancia, sr_fib_velas,account_usdt_limit, order_book_limit, order_book_delay_divisor
    global sl_multiplicador, tp_multiplicador
    global sl_percentaje_account

    sop_res = sr
    logger(f"Operando con un % de saldo de {account_percentage} primera operacion {saldo_usdt_inicial * (account_percentage / 100)}")

    bucle_cnt = 0
    while True:
         bucle_cnt += 1 
         for symbol in simbolos:
            try:
                posiciones = get_opened_positions(symbol=symbol)
                if float(posiciones['result']['list'][0]['size']) != 0:

                    if symbol not in opened_positions:
                        opened_positions.append(symbol)

                    logger("Hay una posicion abierta en " + symbol)
                    if not verificar_posicion_abierta_solo_stop_loss(symbol):
                        logger(f"{symbol}: verifico posicion abierta con detalles: {verificar_posicion_abierta_details(symbol)}")

                        precio_de_entrada = float(posiciones['result']['list'][0]['avgPrice'])

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
                        
                        if posiciones['result']['list'][0]['side']  == 'Buy':
                            stop_loss_short,atr_actual,multiplicador_atr,lastprice = establecer_stop_loss_dinamico(df, sl_multiplicador, tipo_trade='long', timeframe=timeframe)
                            logger(f"{symbol} stop_loss_short: {stop_loss_short} atr_actual: {atr_actual} multiplicador_atr: {multiplicador_atr} lastprice: {lastprice}")
                            result_sl = establecer_stop_loss2(symbol, stop_loss_short)

                            if result_sl:
                                logger(f"{symbol} Stop loss activado")

                                if monitoring == 1:
                                    # Iniciar el monitoreo de la operación
                                    # Calcular el % absoluto entre stop loss y precio de entrada
                                    sl_porcentaje = abs((stop_loss_short - precio_de_entrada) / precio_de_entrada * 100)
                                    logger(f"{symbol} Porcentaje de SL: {sl_porcentaje:.2f}%")
                                    hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_de_entrada, "Buy", sl_porcentaje))
                                    hilo_monitoreo.start()
                            
                        else:
                            stop_loss_long,atr_actual,multiplicador_atr,lastprice = establecer_stop_loss_dinamico(df, sl_multiplicador, tipo_trade='short', timeframe=timeframe)
                            logger(f"{symbol} stop_loss_long: {stop_loss_long} atr_actual: {atr_actual} multiplicador_atr: {multiplicador_atr} lastprice: {lastprice}")
                            result_sl = establecer_stop_loss2(symbol, stop_loss_long)

                            if result_sl:
                                logger(f"{symbol} Stop loss activado")

                                if monitoring == 1:
                                    # Iniciar el monitoreo de la operación
                                    # Calcular el % absoluto entre stop loss y precio de entrada
                                    sl_porcentaje = abs((stop_loss_long - precio_de_entrada) / precio_de_entrada * 100)
                                    logger(f"{symbol} Porcentaje de SL: {sl_porcentaje:.2f}%")
                                    hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_de_entrada, "Sell", sl_porcentaje))
                                    hilo_monitoreo.start()
                                
                    else:
                        logger(f"Hay una posicion abierta en {symbol} espero 60 segundos")
                        time.sleep(60)
                else:

                    if symbol in opened_positions:
                        opened_positions.remove(symbol)

                    if len(opened_positions) >= max_ops:
                        logger(f"Se alcanzó el límite de posiciones abiertas | {max_ops}.")
                        time.sleep(60)
                        continue

                    if bucle_cnt < 2:
                        logger(f"no OPERAR aun | {bucle_cnt}.")
                        time.sleep(20)
                        continue

                    # Obtener datos historicos
                    datam = obtener_datos_historicos(symbol, timeframe)
                   
                    open_prices = np.array(datam[1])
                    high_prices = np.array(datam[2])
                    low_prices = np.array(datam[3])
                    close_prices = np.array(datam[4])
                    volumes = np.array(datam[5])

                    data = calcular_bandas_bollinger(datam)
                    bb_width = data['BB_Width_%']
                    if bb_width < Bollinger_bands_width:
                        time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                        continue;
                        

                    # Crear un DataFrame de pandas con los datos
                    df = pd.DataFrame({
                        'open': open_prices,
                        'high': high_prices,
                        'low': low_prices,
                        'close': close_prices,
                        'volume': volumes
                    })

                    ticker = client.get_tickers(category='linear', symbol=symbol)
                    precio = float(ticker['result']['list'][0]['lastPrice'])
                    fundingRate = float(ticker['result']['list'][0]['fundingRate'])

                    if abs(fundingRate) > 0.0015:  # 0.1% as decimal
                        logger(f"{symbol} Funding rate demasiado alto: {(fundingRate*100):.4f}, saltando")
                        time.sleep(random.randint(sleep_rand_from*2, sleep_rand_to*2))
                        continue

                    if bucle_cnt >= random.randint(30, 80):
                        sop_res = get_syr_n(symbol)
                        bucle_cnt = 2

                    signal_long  = detectar_reversion_alcista(df, sop_res['soportes_total'], top_rsi, bottom_rsi)
                    signal_short  = detectar_reversion_bajista(df, sop_res['resistencias_total'], top_rsi, bottom_rsi)

                    rsi = talib.RSI(close_prices, timeperiod=14)

                    # Calcular la distancia porcentual hasta el soporte más cercano
                    closest_support = None
                    min_distance_percent = float('inf')
                    if len(sop_res['soportes_total']) > 0:
                        for support in sop_res['soportes_total']:
                            distance_percent = abs(precio - support) / precio * 100
                            if distance_percent < min_distance_percent:
                                min_distance_percent = distance_percent
                                closest_support = support

                    # Calcular la distancia porcentual hasta la resistencia más cercana
                    closest_resistance = None
                    min_resistance_distance = float('inf')
                    if len(sop_res['resistencias_total']) > 0:
                        for resistance in sop_res['resistencias_total']:
                            distance_percent = abs(precio - resistance) / precio * 100
                            if distance_percent < min_resistance_distance:
                                min_resistance_distance = distance_percent
                                closest_resistance = resistance


                    log_message = f"{symbol:<18} Price: {precio:<15.5f}\trsi: {rsi[-1]:<3.1f}\tb:{signal_short.iloc[-1]}\ta:{signal_long.iloc[-1]}\tff: {(fundingRate*100):.4f}\tsupport: {min_distance_percent:.2f}%\tresistance: {min_resistance_distance:.2f}%"
                    logger(log_message)
                
                        
                    if signal_short.iloc[-1] == 1:

                        if len(opened_positions_short) >= max_ops_short:
                            logger(f"{symbol:<18} operaciones abiertas en short {len(opened_positions_short)} | maximo configurado es {max_ops_short}.")
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        # Datos de la moneda precio y pasos.
                        step = client.get_instruments_info(category="linear", symbol=symbol)
                        precision_step = float(step['result']['list'][0]["lotSizeFilter"]["qtyStep"])

                        saldo_usdt = obtener_saldo_usdt()
                        usdt = saldo_usdt * (account_percentage / 100)
                        if saldo_usdt < account_usdt_limit:
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        # Calcular ATR para ajustar el tamaño de la posición
                        atr = talib.ATR(high_prices, low_prices, close_prices, timeperiod=14)
                        atr_actual = atr[-1]
                        logger(f"{symbol} ATR actual: {atr_actual:.5f}")

                        # Ajustar el importe de USDT según el ATR
                        # Si el ATR es muy grande, reducimos la exposición para limitar el riesgo
                        max_atr_riesgo = precio * 0.03  # Considera un 3% como ATR de referencia
                        logger(f"{symbol} ATR máximo permitido: {max_atr_riesgo:.5f}")
                        if atr_actual > max_atr_riesgo:
                            # Reducir el importe proporcionalmente al exceso de ATR
                            factor_reduccion = max_atr_riesgo / atr_actual
                            usdt = usdt * factor_reduccion
                            logger(f"{symbol} ATR elevado: {atr_actual:.5f}, reduciendo posición por factor: {factor_reduccion:.2f}")

                        # Calcular el stop loss y verificar máxima pérdida
                        stop_loss_estimado, _, _, _ = establecer_stop_loss_dinamico(df, sl_multiplicador, tipo_trade='short', timeframe=timeframe)
                        max_perdida_permitida = saldo_usdt * (sl_percentaje_account /  100)  # Máximo 2% del saldo total
                        perdida_estimada = abs((precio - stop_loss_estimado) * (usdt / precio))
                        logger(f"{symbol} Pérdida estimada: {perdida_estimada:.2f} USDT")
                        logger(f"{symbol} Pérdida máxima permitida: {max_perdida_permitida:.2f} USDT")

                        if perdida_estimada > max_perdida_permitida:
                            factor_reduccion = max_perdida_permitida / perdida_estimada
                            usdt = usdt * factor_reduccion
                            logger(f"{symbol} Reduciendo posición para limitar pérdida: {perdida_estimada:.2f} USDT a {max_perdida_permitida:.2f} USDT")

                        logger(f"{symbol} usdt final a invertir: {usdt}")

                        if usdt < 5:
                            logger(f"{symbol} Posición insuficiente para operar usdt: {usdt}")
                            continue
                        
                        precision = precision_step
                        qty = usdt / precio
                        qty = qty_precision(qty, precision)
                        if qty.is_integer():
                            qty = int(qty)
                        logger(f"{symbol} Cantidad de monedas a vender: " + str(qty))

                        stop_loss_param,_,_,_ = establecer_stop_loss_dinamico(df, sl_multiplicador, tipo_trade='short', timeframe=timeframe)
                        take_profit_param,_,_,_ = establecer_take_profit_dinamico(df, tp_multiplicador, tipo_trade='short', timeframe=timeframe)
                        crear_orden_con_stoploss_takeprofit(symbol, "Sell", "Market", qty,stop_loss_param,take_profit_param)
                        if monitoring == 1:
                            # Iniciar el monitoreo de la operación
                            precio_entrada = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                            # Calcular el % absoluto entre stop loss y precio de entrada
                            sl_porcentaje = abs((stop_loss_param - precio_entrada) / precio_entrada * 100)
                            logger(f"{symbol} Porcentaje de SL: {sl_porcentaje:.2f}%")
                            hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_entrada, "Sell", sl_porcentaje))
                            hilo_monitoreo.start()

                    if signal_long.iloc[-1] == 1:

                        if len(opened_positions_long) >= max_ops_long:
                            logger(f"{symbol:<18} operaciones abiertas en long {len(opened_positions_long)} | maximo configurado es {max_ops_long}.")
                            time.sleep(random.randint(sleep_rand_from, sleep_rand_to))
                            continue

                        # Datos de la moneda precio y pasos.
                        step = client.get_instruments_info(category="linear", symbol=symbol)
                        precision_step = float(step['result']['list'][0]["lotSizeFilter"]["qtyStep"])

                        saldo_usdt = obtener_saldo_usdt()
                        usdt = saldo_usdt * (account_percentage / 100)

                        if saldo_usdt < account_usdt_limit:
                            continue

                        # Calcular ATR para ajustar el tamaño de la posición
                        atr = talib.ATR(high_prices, low_prices, close_prices, timeperiod=14)
                        atr_actual = atr[-1]
                        logger(f"{symbol} ATR actual: {atr_actual:.5f}")

                        # Ajustar el importe de USDT según el ATR
                        # Si el ATR es muy grande, reducimos la exposición para limitar el riesgo
                        max_atr_riesgo = precio * 0.03  # Considera un 1% como ATR de referencia
                        logger(f"{symbol} ATR máximo permitido: {max_atr_riesgo:.5f}")
                        if atr_actual > max_atr_riesgo:
                            # Reducir el importe proporcionalmente al exceso de ATR
                            factor_reduccion = max_atr_riesgo / atr_actual
                            usdt = usdt * factor_reduccion
                            logger(f"{symbol} ATR elevado: {atr_actual:.5f}, reduciendo posición por factor: {factor_reduccion:.2f}")


                        # Calcular el stop loss y verificar máxima pérdida
                        stop_loss_estimado, _, _, _ = establecer_stop_loss_dinamico(df, sl_multiplicador, tipo_trade='long', timeframe=timeframe)
                        max_perdida_permitida = saldo_usdt * (sl_percentaje_account /  100)   # Máximo 2% del saldo total
                        perdida_estimada = abs((precio - stop_loss_estimado) * (usdt / precio))
                        logger(f"{symbol} Pérdida estimada: {perdida_estimada:.2f} USDT")
                        logger(f"{symbol} Pérdida máxima permitida: {max_perdida_permitida:.2f} USDT")

                        if perdida_estimada > max_perdida_permitida:
                            factor_reduccion = max_perdida_permitida / perdida_estimada
                            usdt = usdt * factor_reduccion
                            logger(f"{symbol} Reduciendo posición para limitar pérdida: {perdida_estimada:.2f} USDT a {max_perdida_permitida:.2f} USDT")

                        logger(f"{symbol} usdt final a invertir: {usdt}")
                        
                        if usdt < 5:
                            logger(f"{symbol} Posición insuficiente para operar usdt: {usdt}")
                            continue

                        precision = precision_step
                        qty = usdt / precio
                        qty = qty_precision(qty, precision)
                        if qty.is_integer():
                            qty = int(qty)

                        logger(f"{symbol} Cantidad de monedas a comprar: " + str(qty))
                        stop_loss_param,_,_,_ = establecer_stop_loss_dinamico(df, sl_multiplicador, tipo_trade='long', timeframe=timeframe)
                        take_profit_param,_,_,_ = establecer_take_profit_dinamico(df, tp_multiplicador, tipo_trade='long', timeframe=timeframe)
                        crear_orden_con_stoploss_takeprofit(symbol, "Buy", "Market", qty,stop_loss_param,take_profit_param)

                        if monitoring == 1:
                            # Iniciar el monitoreo de la operación
                            precio_entrada = float(client.get_tickers(category='linear', symbol=symbol)['result']['list'][0]['lastPrice'])
                            # Calcular el % absoluto entre stop loss y precio de entrada
                            sl_porcentaje = abs((stop_loss_param - precio_entrada) / precio_entrada * 100)
                            logger(f"{symbol} Porcentaje de SL: {sl_porcentaje:.2f}%")
                            hilo_monitoreo = threading.Thread(target=monitorear_operaciones_abiertas, args=(symbol, precio_entrada, "Buy", sl_porcentaje))
                            hilo_monitoreo.start()

            except Exception as e:
                print(e)
                logger(f"Error en el bot {symbol}: {e}")
                time.sleep(60)

         time.sleep(random.randint(sleep_rand_from, sleep_rand_to))



def get_syr(symbol):
    global soportes_resistencias

    try: 
        s,r,va,st,rt,niveles = get_soportes_resistencia(symbol)
        item = {'soportes_cerca': s, 'resistencias_cerca': r, 'valor_actual': va, 'soportes_total': st, 'resistencias_total': rt, 'niveles': niveles}
        soportes_resistencias[symbol] = item

        logger(f"{symbol} ---- Obteniendo soportes y resistencias en 3 niveles ---- niveles: {item['niveles']}")
        return item
    except Exception as e:
        logger(f"Error en get_syr {symbol}: {e}")
        
    return {'soportes_cerca': [], 'resistencias_cerca': [], 'valor_actual': 0, 'soportes_total': [], 'resistencias_total': [], 'niveles': []}

def get_syr_n(symbol):
    global soportes_resistencias

    try: 
        df = obtener_datos_historicos_df(symbol, interval="240")
        niveles_fuertes = calcular_soportes_resistencias_fuertes(df, ventana=10, tolerancia=0.005, min_toques=1)
        item = {'soportes_cerca': niveles_fuertes['soportes'], 'resistencias_cerca': niveles_fuertes['resistencias'], 'valor_actual': 0, 'soportes_total': niveles_fuertes['soportes'], 'resistencias_total': niveles_fuertes['resistencias'], 'niveles': niveles_fuertes}
        soportes_resistencias[symbol] = item

        logger(f"{symbol} ---- Obteniendo soportes y resistencias en 1 nivels ---- nivel: {item['niveles']}")
        return item
    except Exception as e:
        logger(f"Error en get_syr_n {symbol}: {e}")
        
    return {'soportes_cerca': [], 'resistencias_cerca': [], 'valor_actual': 0, 'soportes_total': [], 'resistencias_total': [], 'niveles': []}


# Lista de otros símbolos a buscar
otros_simbolos = obtener_simbolos_mayor_volumen(cnt_symbols)


if strategy == 1:
    hilos = []
    for simbolo in otros_simbolos:
        hilo = threading.Thread(target=operar, args=([simbolo],))
        hilos.append(hilo)
        hilo.start()

if strategy == 2:
    hilos = []
    for simbolo in otros_simbolos:
        hilo = threading.Thread(target=operar2, args=([simbolo],))
        hilos.append(hilo)
        hilo.start()

if strategy == 3:
    hilos = []
    for simbolo in otros_simbolos:
        hilo = threading.Thread(target=operar3, args=([simbolo],))
        hilos.append(hilo)
        hilo.start()

if strategy == 4:
    hilos = []
    for simbolo in otros_simbolos:
        hilo = threading.Thread(target=operar4, args=([simbolo],))
        hilos.append(hilo)
        hilo.start()

if strategy == 5:
    hilos = []
    for simbolo in otros_simbolos:
        hilo = threading.Thread(target=operar5, args=([simbolo],))
        hilos.append(hilo)
        hilo.start()

if strategy == 6:
    hilos = []
    for simbolo in otros_simbolos:
        hilo = threading.Thread(target=operar6, args=([simbolo],))
        hilos.append(hilo)
        hilo.start()


if strategy == 7:
    for simbolo in otros_simbolos:
        item = get_syr(simbolo)

        hilo = threading.Thread(target=operar7, args=([simbolo],item,))
        hilos.append(hilo)
        hilo.start()

if strategy == 8: # varios
    hilos = []
    for simbolo in otros_simbolos:
        item = get_syr(simbolo)
        hilo = threading.Thread(target=operar8, args=([simbolo],item,)) 
        hilo.start()

if strategy == 9: # ema
    hilos = []
    for simbolo in otros_simbolos:
        hilo = threading.Thread(target=operar9, args=([simbolo],)) 
        hilo.start()



if strategy == 10: # ema
    hilos = []
    for simbolo in otros_simbolos:
        item = get_syr_n(simbolo)
        hilo = threading.Thread(target=operar10, args=([simbolo],item,)) 
        hilo.start()
