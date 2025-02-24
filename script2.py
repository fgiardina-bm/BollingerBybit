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
    
    with config_lock:
        logger(f"Operando con un % de saldo de {account_percentage} primera operacion {saldo_usdt_inicial * (account_percentage / 100)}")

    while True:

        for symbol in simbolos:
            get_opened_positions(symbol=symbol)
            print(f"long {len(opened_positions_long)} - short {len(opened_positions_short)}")
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


