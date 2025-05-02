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


def operar_grid_avanzado(simbolo, num_ordenes=30, porcentaje_account=10, distancia_entre_ordenes=0.5, max_perdida_porcentaje=2):
    """
    Implementación avanzada de un Grid Bot para Bybit con gestión dinámica y protección contra riesgos.
    
    Args:
        simbolo (str): Par de trading (ej. "BTCUSDT")
        num_ordenes (int): Cantidad total de órdenes en la cuadrícula
        porcentaje_account (float): Porcentaje de la cuenta a invertir en total
        distancia_entre_ordenes (float): Porcentaje de distancia entre cada orden
        max_perdida_porcentaje (float): Porcentaje máximo de pérdida permitido
    """
    global saldo_usdt_inicial, client, grid_distancia_factor
    
    # Obtener información del mercado
    ticker = client.get_tickers(category='linear', symbol=simbolo)
    precio_actual = float(ticker['result']['list'][0]['lastPrice'])
    
    # Información sobre la precisión del símbolo
    step_info = client.get_instruments_info(category="linear", symbol=simbolo)
    precision_step = float(step_info['result']['list'][0]["lotSizeFilter"]["qtyStep"])
    
    # Calcular el saldo disponible para el grid
    saldo_usdt = obtener_saldo_usdt()
    usdt_total = saldo_usdt * (porcentaje_account / 100)
    max_perdida_absoluta = saldo_usdt * (max_perdida_porcentaje / 100)  # Pérdida máxima permitida
    
    logger(f"Iniciando Grid Bot para {simbolo}")
    logger(f"Precio actual: {precio_actual}")
    logger(f"Total a invertir: {usdt_total} USDT")
    logger(f"Pérdida máxima permitida: {max_perdida_absoluta} USDT")
    
    # Cancelar órdenes existentes para este símbolo
    try:
        client.cancel_all_orders(category="linear", symbol=simbolo)
        logger(f"Órdenes previas canceladas para {simbolo}")
    except Exception as e:
        logger(f"Error al cancelar órdenes: {e}")
    
    # 1. Detección de tendencias fuertes para ajustar el grid
    datam = obtener_datos_historicos(simbolo, timeframe)
    open_prices = np.array(datam[1])
    high_prices = np.array(datam[2])
    low_prices = np.array(datam[3])
    close_prices = np.array(datam[4])
    df = pd.DataFrame({
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices
    })
    
    # Calcular indicadores para detectar tendencia
    df['ADX'] = talib.ADX(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)
    df['SMA50'] = talib.SMA(close_prices, timeperiod=50)
    df['SMA200'] = talib.SMA(close_prices, timeperiod=200)
    
    tendencia_fuerte = False
    tendencia_direccion = "neutral"
    
    # Comprobar si hay una tendencia fuerte (ADX > 25)
    if df['ADX'].iloc[-1] > 25:
        tendencia_fuerte = True
        # Determinar dirección de la tendencia (alcista o bajista)
        if df['SMA50'].iloc[-1] > df['SMA200'].iloc[-1]:
            tendencia_direccion = "alcista"
            logger(f"Tendencia alcista fuerte detectada en {simbolo}, ADX: {df['ADX'].iloc[-1]:.2f}")
        else:
            tendencia_direccion = "bajista"
            logger(f"Tendencia bajista fuerte detectada en {simbolo}, ADX: {df['ADX'].iloc[-1]:.2f}")
    
    # 2. Ajustar el grid basado en la volatilidad usando ATR
    atr = talib.ATR(high_prices, low_prices, close_prices, timeperiod=14)
    atr_actual = atr[-1]
    volatilidad_porcentaje = (atr_actual / precio_actual) * 100
    
    # Ajustar distancia entre órdenes según volatilidad
    distancia_ajustada = distancia_entre_ordenes
    if volatilidad_porcentaje > 1.5:  # Si la volatilidad es alta
        distancia_ajustada = distancia_entre_ordenes * 1.5
        logger(f"Volatilidad alta: {volatilidad_porcentaje:.2f}%, aumentando distancia entre órdenes a {distancia_ajustada:.2f}%")
    elif volatilidad_porcentaje < 0.5:  # Si la volatilidad es baja
        distancia_ajustada = max(0.2, distancia_entre_ordenes * 0.8)
        logger(f"Volatilidad baja: {volatilidad_porcentaje:.2f}%, disminuyendo distancia entre órdenes a {distancia_ajustada:.2f}%")
    
    # 3. Ajustar distribución de órdenes según tendencia
    num_ordenes_long = num_ordenes // 2
    num_ordenes_short = num_ordenes - num_ordenes_long
    
    # Si hay tendencia fuerte, distribuir más órdenes en esa dirección
    if tendencia_fuerte:
        if tendencia_direccion == "alcista":
            num_ordenes_long = int(num_ordenes * 0.7)
            num_ordenes_short = num_ordenes - num_ordenes_long
            logger(f"Ajustando grid para tendencia alcista: {num_ordenes_long} long, {num_ordenes_short} short")
        else:
            num_ordenes_short = int(num_ordenes * 0.7)
            num_ordenes_long = num_ordenes - num_ordenes_short
            logger(f"Ajustando grid para tendencia bajista: {num_ordenes_long} long, {num_ordenes_short} short")
    
    # Calcular cantidad por orden con la nueva distribución
    usdt_por_orden = usdt_total / num_ordenes
    
    # 4. Crear órdenes long (por debajo del precio actual)
    for i in range(num_ordenes_long):
        # Cada orden está a 'distancia_ajustada'% por debajo de la anterior
        # Apply increasing distance factor (1.05) for orders that are further away
        distance_factor = grid_distancia_factor ** i  # This will be 1.0, 1.05 , 1.1025, 1.157625, etc.
        precio_orden = precio_actual * (1 - ((i+1) * distancia_ajustada * distance_factor / 100))
        precio_orden = qty_step(precio_orden, simbolo)  # Ajustar al paso de precio
        
        # Calcular cantidad a comprar
        qty = usdt_por_orden / precio_orden
        qty = qty_precision(qty, precision_step)
        if qty.is_integer():
            qty = int(qty)
            
        # Precio de toma de beneficios (TP) - Dinámico basado en volatilidad
        tp_distancia = distancia_ajustada * (1 + (atr_actual / precio_actual))
        tp_precio = precio_orden * (1 + (tp_distancia / 100))
        tp_precio = qty_step(tp_precio, simbolo)
        
        try:
            # Colocar orden limit de compra
            if test_mode == 0:
                response = client.place_order(
                    category="linear",
                    symbol=simbolo,
                    side="Buy",
                    orderType="Limit",
                    price=str(precio_orden),
                    qty=str(qty),
                    timeInForce="GTC",
                    reduceOnly=False,
                    closeOnTrigger=False
                )
                logger(f"Orden LONG #{i+1}: Precio={precio_orden}, Cantidad={qty}, TP={tp_precio}")
            else:
                logger(f"[TEST] Orden LONG #{i+1}: Precio={precio_orden}, Cantidad={qty}, TP={tp_precio}")
        except Exception as e:
            logger(f"Error al crear orden LONG #{i+1}: {e}")
    
    # 5. Crear órdenes short (por encima del precio actual)
    for i in range(num_ordenes_short):
        # Cada orden está a 'distancia_ajustada'% por encima de la anterior
        distance_factor = grid_distancia_factor ** i  # This will be 1.0, 1.05 , 1.1025, 1.157625, etc.
        precio_orden = precio_actual * (1 + ((i+1) * distancia_ajustada * distance_factor / 100))
        precio_orden = qty_step(precio_orden, simbolo)
        
        # Calcular cantidad a vender
        qty = usdt_por_orden / precio_orden
        qty = qty_precision(qty, precision_step)
        if qty.is_integer():
            qty = int(qty)
            
        # Precio de toma de beneficios (TP) - Dinámico basado en volatilidad
        tp_distancia = distancia_ajustada * (1 + (atr_actual / precio_actual))
        tp_precio = precio_orden * (1 - (tp_distancia / 100))
        tp_precio = qty_step(tp_precio, simbolo)
        
        try:
            # Colocar orden limit de venta
            if test_mode == 0:
                response = client.place_order(
                    category="linear",
                    symbol=simbolo,
                    side="Sell",
                    orderType="Limit",
                    price=str(precio_orden),
                    qty=str(qty),
                    timeInForce="GTC",
                    reduceOnly=False,
                    closeOnTrigger=False
                )
                logger(f"Orden SHORT #{i+1}: Precio={precio_orden}, Cantidad={qty}, TP={tp_precio}")
            else:
                logger(f"[TEST] Orden SHORT #{i+1}: Precio={precio_orden}, Cantidad={qty}, TP={tp_precio}")
        except Exception as e:
            logger(f"Error al crear orden SHORT #{i+1}: {e}")
    
    logger(f"Grid Bot iniciado con {num_ordenes_long} órdenes LONG y {num_ordenes_short} órdenes SHORT")
    
    # Devolver información del grid para monitoreo
    return {
        "simbolo": simbolo,
        "precio_actual": precio_actual,
        "usdt_total": usdt_total,
        "num_ordenes": num_ordenes,
        "num_long": num_ordenes_long,
        "num_short": num_ordenes_short,
        "distancia": distancia_ajustada,
        "volatilidad": volatilidad_porcentaje,
        "tendencia": tendencia_direccion,
        "max_perdida_porcentaje": max_perdida_porcentaje,
    }

def hay_ordenes_activas(simbolo):
    """
    Comprueba si existen órdenes activas para un símbolo determinado.
    
    Args:
        simbolo (str): Par de trading
        
    Returns:
        bool: True si hay órdenes activas, False en caso contrario
    """
    try:
        ordenes = client.get_open_orders(category="linear", symbol=simbolo)
        return len(ordenes['result']['list']) > 0
    except Exception as e:
        logger(f"Error al verificar órdenes activas para {simbolo}: {e}")
        return False

def monitorear_grid_avanzado(simbolo, info_grid):
    """
    Monitorea el grid y mantiene su funcionamiento óptimo.
    - Rebalancea según movimientos de precio
    - Ajusta órdenes según cambios de volatilidad
    - Cierra posiciones en caso de tendencia muy fuerte adversa
    - Monitorea PNL y ejecuta stop loss si supera -5% de la cuenta
    - Repone órdenes dinámicamente según se van ejecutando
    
    Args:
        simbolo (str): Par de trading
        info_grid (dict): Información del grid creado
    """
    global client,grid_hs_rebalanceo

    logger('monitorear_grid_avanzado', simbolo)
    ultimo_precio = info_grid["precio_actual"]
    ultima_volatilidad = info_grid["volatilidad"]
    ultimo_rebalanceo = time.time()
    ultima_verificacion_ordenes = time.time()
    max_perdida_porcentaje = info_grid["max_perdida_porcentaje"]
    
    # Obtener saldo total de la cuenta para cálculos de stop loss
    saldo_total_inicial = obtener_saldo_usdt()
    stop_loss_threshold = -0.05 * saldo_total_inicial  # Stop loss al -5% del saldo total
    
    # Información sobre la precisión del símbolo
    step_info = client.get_instruments_info(category="linear", symbol=simbolo)
    precision_step = float(step_info['result']['list'][0]["lotSizeFilter"]["qtyStep"])
    
    # Porcentaje de la cuenta a usar para cada nueva orden
    porcentaje_por_orden = info_grid["usdt_total"] / (info_grid["num_ordenes"] * saldo_total_inicial) * 100
    
    logger(f"Stop loss configurado: se cerrará la posición si PNL < {stop_loss_threshold} USDT")
    logger(f"Reposición de órdenes: {porcentaje_por_orden:.2f}% por orden")
    
    while True:
        try:
            # Verificar si debemos seguir monitoreando
            posiciones = get_opened_positions(symbol=simbolo)
            if len(posiciones['result']['list']) == 0 or float(posiciones['result']['list'][0]['size']) == 0 and not hay_ordenes_activas(simbolo):
                logger(f"No hay posiciones ni órdenes activas para {simbolo}. Finalizando monitoreo.")
                break
            
            # Obtener y mostrar PNL actual cada 1 minuto
            pnl_actual = float(posiciones['result']['list'][0]['unrealisedPnl'])
            pnl_porcentaje = (pnl_actual / saldo_total_inicial) * 100
            logger(f"PNL actual para {simbolo}: {pnl_actual:.4f} USDT ({pnl_porcentaje:.2f}% de la cuenta)")
            
            # Verificar si se debe ejecutar stop loss
            if pnl_actual < stop_loss_threshold:
                logger(f"¡STOP LOSS ACTIVADO! PNL ({pnl_actual:.4f} USDT) ha superado el límite de pérdida de {stop_loss_threshold:.4f} USDT")
                logger(f"Cerrando todas las posiciones y órdenes para {simbolo}...")
                
                # Cancelar todas las órdenes pendientes
                client.cancel_all_orders(category="linear", symbol=simbolo)
                
                # Cerrar posiciones existentes
                side = "Sell" if float(posiciones['result']['list'][0]['size']) > 0 else "Buy"
                size = abs(float(posiciones['result']['list'][0]['size']))
                
                if size > 0:
                    if test_mode == 0:
                        client.place_order(
                            category="linear",
                            symbol=simbolo,
                            side=side,
                            orderType="Market",
                            qty=str(size),
                            reduceOnly=True
                        )
                        logger(f"Posición de {simbolo} cerrada con orden de mercado {side} de {size}")
                    else:
                        logger(f"[TEST] Posición de {simbolo} cerrada con orden de mercado {side} de {size}")
                
                logger(f"Stop loss ejecutado para {simbolo}. Finalizando monitoreo.")
                break
            
            # Obtener precio actual 
            ticker = client.get_tickers(category='linear', symbol=simbolo)
            precio_actual = float(ticker['result']['list'][0]['lastPrice'])
            
            # Verificar y reponer órdenes cada 5 minutos
            # if time.time() - ultima_verificacion_ordenes > 300:  # 5 minutos
            #     logger(f"Verificando y reponiendo órdenes para {simbolo}...")
                
            #     # Obtener órdenes activas
            #     ordenes_activas = client.get_open_orders(category="linear", symbol=simbolo)
            #     num_ordenes_activas = len(ordenes_activas['result']['list'])
                
            #     # Obtener posición promedio de entrada
            #     posicion_side = "long" if float(posiciones['result']['list'][0]['size']) > 0 else "short"
            #     precio_entrada = float(posiciones['result']['list'][0]['avgPrice'])
                
            #     logger(f"Posición actual: {posicion_side.upper()} a precio promedio {precio_entrada}")
            #     logger(f"Órdenes activas: {num_ordenes_activas} de {info_grid['num_ordenes']}")
                
            #     # Verificar si necesitamos reponer órdenes
            #     if num_ordenes_activas < info_grid['num_ordenes'] * 0.7:  # Si tenemos menos del 70% de las órdenes originales
            #         # Calcular cuántas órdenes necesitamos reponer
            #         ordenes_a_reponer = info_grid['num_ordenes'] - num_ordenes_activas
            #         logger(f"Reponiendo {ordenes_a_reponer} órdenes...")
                    
            #         # Calcular el saldo disponible para nuevas órdenes
            #         saldo_actual = obtener_saldo_usdt()
            #         usdt_por_orden = saldo_actual * (porcentaje_por_orden / 100)
                    
            #         # Obtener ATR para ajustar distancias
            #         datam = obtener_datos_historicos(simbolo, timeframe)
            #         atr = talib.ATR(
            #             np.array(datam[2]),  # high
            #             np.array(datam[3]),  # low
            #             np.array(datam[4]),  # close
            #             timeperiod=14
            #         )
            #         atr_actual = atr[-1]
                    
            #         # Ajustar distancia según volatilidad
            #         distancia_ajustada = info_grid["distancia"]
            #         volatilidad_porcentaje = (atr_actual / precio_actual) * 100
            #         if volatilidad_porcentaje > 1.5:
            #             distancia_ajustada = info_grid["distancia"] * 1.5
            #         elif volatilidad_porcentaje < 0.5:
            #             distancia_ajustada = max(0.2, info_grid["distancia"] * 0.8)
                    
            #         # Si tenemos posición long, crear órdenes LONG por debajo del precio de entrada
            #         if posicion_side == "long":
            #             for i in range(min(ordenes_a_reponer, 5)):  # Limitamos a 5 órdenes por ciclo
            #                 # Calcular precio por debajo del precio de entrada
            #                 precio_orden = precio_entrada * (1 - ((i+1) * distancia_ajustada / 100))
            #                 precio_orden = qty_step(precio_orden, simbolo)
                            
            #                 # Solo crear orden si está por debajo del precio actual
            #                 if precio_orden < precio_actual * 0.99:  # 1% por debajo del precio actual
            #                     # Calcular cantidad a comprar
            #                     qty = usdt_por_orden / precio_orden
            #                     qty = qty_precision(qty, precision_step)
            #                     if qty.is_integer():
            #                         qty = int(qty)
                                
            #                     try:
            #                         if test_mode == 0:
            #                             response = client.place_order(
            #                                 category="linear",
            #                                 symbol=simbolo,
            #                                 side="Buy",
            #                                 orderType="Limit",
            #                                 price=str(precio_orden),
            #                                 qty=str(qty),
            #                                 timeInForce="GTC",
            #                                 reduceOnly=False,
            #                                 closeOnTrigger=False
            #                             )
            #                             logger(f"Nueva orden LONG: Precio={precio_orden}, Cantidad={qty}")
            #                         else:
            #                             logger(f"[TEST] Nueva orden LONG: Precio={precio_orden}, Cantidad={qty}")
            #                     except Exception as e:
            #                         logger(f"Error al crear nueva orden LONG: {e}")
                    
            #         # Si tenemos posición short, crear órdenes SHORT por encima del precio de entrada
            #         elif posicion_side == "short":
            #             for i in range(min(ordenes_a_reponer, 5)):  # Limitamos a 5 órdenes por ciclo
            #                 # Calcular precio por encima del precio de entrada
            #                 precio_orden = precio_entrada * (1 + ((i+1) * distancia_ajustada / 100))
            #                 precio_orden = qty_step(precio_orden, simbolo)
                            
            #                 # Solo crear orden si está por encima del precio actual
            #                 if precio_orden > precio_actual * 1.01:  # 1% por encima del precio actual
            #                     # Calcular cantidad a vender
            #                     qty = usdt_por_orden / precio_orden
            #                     qty = qty_precision(qty, precision_step)
            #                     if qty.is_integer():
            #                         qty = int(qty)
                                
            #                     try:
            #                         if test_mode == 0:
            #                             response = client.place_order(
            #                                 category="linear",
            #                                 symbol=simbolo,
            #                                 side="Sell",
            #                                 orderType="Limit",
            #                                 price=str(precio_orden),
            #                                 qty=str(qty),
            #                                 timeInForce="GTC",
            #                                 reduceOnly=False,
            #                                 closeOnTrigger=False
            #                             )
            #                             logger(f"Nueva orden SHORT: Precio={precio_orden}, Cantidad={qty}")
            #                         else:
            #                             logger(f"[TEST] Nueva orden SHORT: Precio={precio_orden}, Cantidad={qty}")
            #                     except Exception as e:
            #                         logger(f"Error al crear nueva orden SHORT: {e}")
                
            #     ultima_verificacion_ordenes = time.time()
            
            # Calcular cambio de precio porcentual
            cambio_porcentual = abs((precio_actual - ultimo_precio) / ultimo_precio * 100)
            logger(f"Precio actual: {precio_actual}, Cambio porcentual: {cambio_porcentual:.2f}%, {time.time() - ultimo_rebalanceo:.2f} segundos desde el último rebalanceo")
            
            # 1. Rebalancear si el precio se ha movido significativamente (>3%)
            if cambio_porcentual > 2 or (time.time() - ultimo_rebalanceo > grid_hs_rebalanceo * 3600):  # Rebalancear cada 1 horas o si hay cambio significativo
                logger(f"Rebalanceando grid de {simbolo}. Cambio de precio: {cambio_porcentual:.2f}%")
                
                # Cancelar todas las órdenes existentes
                client.cancel_all_orders(category="linear", symbol=simbolo)
                
                # Crear un nuevo grid centrado en el precio actual
                info_grid = operar_grid_avanzado(
                    simbolo, 
                    info_grid["num_ordenes"],
                    info_grid["usdt_total"] / obtener_saldo_usdt() * 100,  # Mantener el mismo porcentaje
                    info_grid["distancia"]
                )
                
                ultimo_precio = precio_actual
                ultimo_rebalanceo = time.time()
                ultima_verificacion_ordenes = time.time()  # Reiniciar también el tiempo de verificación de órdenes
                continue
            
            # 2. Verificar cambios en volatilidad
            datam = obtener_datos_historicos(simbolo, timeframe)
            atr = talib.ATR(
                np.array(datam[2]),  # high
                np.array(datam[3]),  # low
                np.array(datam[4]),  # close
                timeperiod=14
            )
            volatilidad_actual = (atr[-1] / precio_actual) * 100
            
            # Si la volatilidad cambia significativamente, ajustar la distancia entre órdenes
            if abs(volatilidad_actual - ultima_volatilidad) / ultima_volatilidad > 0.3:  # Cambio del 30% en volatilidad
                logger(f"Volatilidad cambiada significativamente para {simbolo}, de {ultima_volatilidad:.2f}% a {volatilidad_actual:.2f}%")
                
                # Ajustar distancia entre órdenes según nueva volatilidad
                if volatilidad_actual > ultima_volatilidad:
                    nueva_distancia = info_grid["distancia"] * (1 + (volatilidad_actual - ultima_volatilidad) / 100)
                    logger(f"Aumentando distancia entre órdenes a {nueva_distancia:.2f}%")
                else:
                    nueva_distancia = info_grid["distancia"] * (1 - (ultima_volatilidad - volatilidad_actual) / 200)
                    logger(f"Reduciendo distancia entre órdenes a {nueva_distancia:.2f}%")
                
                # Actualizar grid con nueva distancia
                client.cancel_all_orders(category="linear", symbol=simbolo)
                info_grid = operar_grid_avanzado(
                    simbolo, 
                    info_grid["num_ordenes"],
                    info_grid["usdt_total"] / obtener_saldo_usdt() * 100,
                    nueva_distancia
                )
                
                ultimo_precio = precio_actual
                ultima_volatilidad = volatilidad_actual
                ultimo_rebalanceo = time.time()
                ultima_verificacion_ordenes = time.time()
            
            # 3. Detectar tendencia muy fuerte que podría hacer que el grid sea ineficiente
            df = pd.DataFrame({
                'open': np.array(datam[1]),
                'high': np.array(datam[2]),
                'low': np.array(datam[3]),
                'close': np.array(datam[4])
            })
            
            # Calcular ADX para medir fuerza de la tendencia
            df['ADX'] = talib.ADX(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)
            
            # Si hay una tendencia muy fuerte (ADX > 40), considerar cerrar el grid
            if df['ADX'].iloc[-1] > 40:
                # Calcular dirección de la tendencia
                direccion = "alcista" if df['close'].iloc[-1] > df['close'].iloc[-5] else "bajista"
                logger(f"Tendencia {direccion} extremadamente fuerte detectada en {simbolo}, ADX: {df['ADX'].iloc[-1]:.2f}")
                
                # Notificar pero no cerrar automáticamente para evitar falsos positivos
                logger(f"¡ATENCIÓN! Considere cerrar el grid de {simbolo} o ajustar manualmente debido a la fuerte tendencia {direccion}")
            
            # Esperar antes de la próxima verificación
            time.sleep(60)
            
        except Exception as e:
            logger(f"Error en monitoreo del grid de {simbolo}: {e}")
            time.sleep(60)

def ejecutar_grid_bot(simbolo, num_ordenes=30, porcentaje_cuenta=10, distancia=0.5, max_perdida=2):
    """
    Función principal para ejecutar el grid bot.
    
    Args:
        simbolo (str): Par de trading (ej. "BTCUSDT")
        num_ordenes (int): Cantidad total de órdenes en el grid
        porcentaje_cuenta (float): Porcentaje de la cuenta a utilizar
        distancia (float): Distancia inicial entre órdenes (%)
        max_perdida (float): Porcentaje máximo de pérdida permitido
    """
    try:
        # Verificar si hay fondos suficientes
        saldo_usdt = obtener_saldo_usdt()
        if saldo_usdt < 20:  # Mínimo 100 USDT para operar
            logger(f"Saldo insuficiente ({saldo_usdt} USDT) para operar un grid bot")
            return False
        
        # Verificar que el símbolo existe y es operable
        try:
            info = client.get_instruments_info(category="linear", symbol=simbolo)
            if not info['result']['list']:
                logger(f"El símbolo {simbolo} no existe o no está disponible")
                return False
        except Exception as e:
            logger(f"Error al verificar el símbolo {simbolo}: {e}")
            return False
        
        # Configurar y crear el grid
        info_grid = operar_grid_avanzado(simbolo, num_ordenes, porcentaje_cuenta, distancia, max_perdida)
        
        # Iniciar monitoreo en un hilo separado
        # hilo_monitoreo = threading.Thread(target=monitorear_grid_avanzado, args=(simbolo, info_grid))
        # hilo_monitoreo.daemon = True
        # hilo_monitoreo.start()
        monitorear_grid_avanzado(simbolo, info_grid)
        logger(f"Grid Bot para {simbolo} iniciado correctamente")
        return True
        
    except Exception as e:
        logger(f"Error al iniciar Grid Bot para {simbolo}: {e}")
        return False


def iniciar_grid_bot():
    """
    Inicia un Grid Bot con parámetros configurados por el usuario
    """
    # Solicitar parámetros
    simbolo = input("Introduce el símbolo (ej. BTCUSDT): ").upper()
    
    try:
        num_ordenes = int(input("Número de órdenes (recomendado 20-40): ") or "30")
        porcentaje_cuenta = float(input("Porcentaje de la cuenta a utilizar (1-100): ") or "100")
        distancia = float(input("Distancia entre órdenes en % (recomendado 0.5-2): ") or "0.5")
        max_perdida = float(input("Porcentaje máximo de pérdida permitido (1-5): ") or "2")
        
        if 2 <= num_ordenes <= 100 and 1 <= porcentaje_cuenta <= 1000 and 0.1 <= distancia <= 5 and 1 <= max_perdida <= 10:
            logger(f"Iniciando Grid Bot para {simbolo}")
            resultado = ejecutar_grid_bot(simbolo, num_ordenes, porcentaje_cuenta, distancia, max_perdida)
            if resultado:
                logger(f"Grid Bot iniciado exitosamente para {simbolo}")
                return True
            else:
                logger("No se pudo iniciar el Grid Bot")
                return False
        else:
            logger("Parámetros fuera de rango permitido")
            return False
    except ValueError:
        logger("Error en el formato de los parámetros")
        return False


# iniciar_grid_bot()