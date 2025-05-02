import os
from dotenv import load_dotenv
import time
import threading

# Definir constantes para las claves de las variables de entorno
API_KEY = "API_KEY"
API_SECRET = "API_SECRET"
TIMEFRAME = "TIMEFRAME"
TP_PORCENT = "TP_PORCENT"
SL_PORCENT = "SL_PORCENT"
CNT_SYMBOLS = "CNT_SYMBOLS"
ACCOUNT_PERCENTAGE = "ACCOUNT_PERCENTAGE"
TOP_RSI = "TOP_RSI"
BOTTOM_RSI = "BOTTOM_RSI"
SLEEP_RAND_FROM = "SLEEP_RAND_FROM"
SLEEP_RAND_TO = "SLEEP_RAND_TO"
SL_CALLBACK_PERCENTAGE = "SL_CALLBACK_PERCENTAGE"
VERIFY_RSI = "VERIFY_RSI"
BB_WIDTH = "BB_WIDTH"
MONITORING = "MONITORING"
MAX_OPS = "MAX_OPS"
MAX_OPS_SHORT = "MAX_OPS_SHORT"
MAX_OPS_LONG = "MAX_OPS_LONG"

# Configuracion de la API
api_key = os.getenv(API_KEY)
api_secret = os.getenv(API_SECRET)
timeframe = int(os.getenv(TIMEFRAME, "5"))

tp_porcent = float(os.getenv(TP_PORCENT, 2))
sl_porcent = float(os.getenv(SL_PORCENT, 1))

cnt_symbols = int(os.getenv(CNT_SYMBOLS, 20))
account_percentage = int(os.getenv(ACCOUNT_PERCENTAGE, 4))
account_usdt_limit = int(os.getenv("ACCOUNT_USDT_LIMIT", 10))

top_rsi = int(os.getenv(TOP_RSI, 87))
bottom_rsi = int(os.getenv(BOTTOM_RSI, 13))

sleep_rand_from = int(os.getenv(SLEEP_RAND_FROM, 10))
sleep_rand_to = int(os.getenv(SLEEP_RAND_TO, 20))

sl_callback_percentage = float(os.getenv(SL_CALLBACK_PERCENTAGE, 1))
verify_rsi = int(os.getenv(VERIFY_RSI, 5))
Bollinger_bands_width = int(os.getenv(BB_WIDTH, 5))
monitoring = int(os.getenv(MONITORING, 1))
max_ops = int(os.getenv(MAX_OPS, 1))
max_ops_short = int(os.getenv(MAX_OPS_SHORT, 2))
max_ops_long = int(os.getenv(MAX_OPS_LONG, 2))
strategy = int(os.getenv("STRATEGY", 1))
sr_fib_tolerancia = float(os.getenv("SR_FIB_TOLERANCIA", 0.01))
sr_fib_velas = int(os.getenv("SR_FIB_VELAS", 50))

test_mode = int(os.getenv("TEST_MODE", 0))
order_book_limit = int(os.getenv("ORDER_BOOK_LIMIT", 1000))
order_book_delay_divisor = int(os.getenv("ORDER_BOOK_DELAY_DIVISOR", 1))
black_list_symbols = os.getenv("BLACK_LIST_SYMBOLS", "BNXUSDT").split(",")
sl_multiplicador = float(os.getenv("SL_MULTIPLICADOR", 0.5))
tp_multiplicador = float(os.getenv("TP_MULTIPLICADOR", 1.5))
sl_percentaje_account = float(os.getenv("SL_PERCENTAJE_ACCOUNT", 2.0))

detectar_incluir_bbands = int(os.getenv("DETECTAR_INCLUIR_BBANDS", 1))
detectar_incluir_rsi = int(os.getenv("DETECTAR_INCLUIR_RSI", 1))
detectar_incluir_sr = int(os.getenv("DETECTAR_INCLUIR_SR", 1))
detectar_incluir_patron_velas = int(os.getenv("DETECTAR_INCLUIR_PATRON_VELAS", 1))
detectar_incluir_volume = int(os.getenv("DETECTAR_INCLUIR_VOLUME", 1))
detectar_incluir_emas = int(os.getenv("DETECTAR_INCLUIR_EMAS", 1))
detectar_incluir_adx = int(os.getenv("DETECTAR_INCLUIR_ADX", 1))    

sl_callback_progresive = float(os.getenv("SL_CALLBACK_PROGRESIVE", 0.7))
symbols_from = os.getenv("SYMBOLS_FROM", 'binance')

grid_symbol = os.getenv("GRID_SYMBOL", 'BTCUSDT')
grid_num_ordenes = int(os.getenv("GRID_NUM_ORDENES", 10))
grid_porcentaje_cuenta = float(os.getenv("GRID_PORCENTAJE_CUENTA", 100.0))
grid_distancia = float(os.getenv("GRID_DISTANCIA", 0.05))
grid_max_perdida = float(os.getenv("GRID_MAX_PERDIDA", 2))
grid_distancia_factor = float(os.getenv("GRID_DISTANCIA_FACTOR", 1.05))



config_lock = threading.Lock()

opened_positions = []
opened_positions_short = []
opened_positions_long = []

soportes_resistencias = {}


def reload_config():

    global api_key, api_secret, timeframe, tp_porcent, sl_porcent, cnt_symbols
    global account_percentage, top_rsi, bottom_rsi, sleep_rand_from, sleep_rand_to
    global sl_callback_percentage, verify_rsi, Bollinger_bands_width, monitoring, max_ops
    global opened_positions, opened_positions_short, opened_positions_long
    global max_ops_short, max_ops_long, strategy, sr_fib_tolerancia, test_mode, sr_fib_velas, account_usdt_limit
    global soportes_resistencias, order_book_limit, order_book_delay_divisor, black_list_symbols, sl_multiplicador, tp_multiplicador
    global sl_percentaje_account
    global detectar_incluir_bbands, detectar_incluir_rsi, detectar_incluir_sr, detectar_incluir_patron_velas, detectar_incluir_volume, detectar_incluir_emas, detectar_incluir_adx
    global sl_callback_progresive, symbols_from

    config_path = ".env"

    if timeframe == 60:
        config_path = ".env60"

    if timeframe == 240:
        config_path = ".env4"

    load_dotenv(config_path, override=True)

    try:
        api_key = os.getenv(API_KEY)
        api_secret = os.getenv(API_SECRET)
        test_mode = float(os.getenv("TEST_MODE", 0))

        timeframe = int(os.getenv(TIMEFRAME, "5"))

        tp_porcent = float(os.getenv(TP_PORCENT, 2))
        sl_porcent = float(os.getenv(SL_PORCENT, 1))

        cnt_symbols = int(os.getenv(CNT_SYMBOLS, 20))
        account_percentage = int(os.getenv(ACCOUNT_PERCENTAGE, 4))
        account_usdt_limit = int(os.getenv("ACCOUNT_USDT_LIMIT", 10))

        top_rsi = int(os.getenv(TOP_RSI, 87))
        bottom_rsi = int(os.getenv(BOTTOM_RSI, 13))

        sleep_rand_from = int(os.getenv(SLEEP_RAND_FROM, 10))
        sleep_rand_to = int(os.getenv(SLEEP_RAND_TO, 20))

        sl_callback_percentage = float(os.getenv(SL_CALLBACK_PERCENTAGE, 1))
        verify_rsi = int(os.getenv(VERIFY_RSI, 5))
        Bollinger_bands_width = int(os.getenv(BB_WIDTH, 5))
        monitoring = int(os.getenv(MONITORING, 1))
        max_ops = int(os.getenv(MAX_OPS, 1))
        max_ops_short = int(os.getenv(MAX_OPS_SHORT, 2))
        max_ops_long = int(os.getenv(MAX_OPS_LONG, 2))

        strategy = int(os.getenv("STRATEGY", 1))
        sr_fib_tolerancia = int(os.getenv("SR_FIB_TOLERANCIA", 0.01))
        sr_fib_velas = int(os.getenv("SR_FIB_VELAS", 50))
        order_book_limit = int(os.getenv("ORDER_BOOK_LIMIT", 1000))
        order_book_delay_divisor = int(os.getenv("ORDER_BOOK_DELAY_DIVISOR", 1))
        black_list_symbols = os.getenv("BLACK_LIST_SYMBOLS", "").split(",")
        sl_multiplicador = float(os.getenv("SL_MULTIPLICADOR", 2))
        tp_multiplicador = float(os.getenv("TP_MULTIPLICADOR", 1.5))
        sl_percentaje_account = float(os.getenv("SL_PERCENTAJE_ACCOUNT", 2.0))

        detectar_incluir_bbands = int(os.getenv("DETECTAR_INCLUIR_BBANDS", 1))
        detectar_incluir_rsi = int(os.getenv("DETECTAR_INCLUIR_RSI", 1))
        detectar_incluir_sr = int(os.getenv("DETECTAR_INCLUIR_SR", 1))
        detectar_incluir_patron_velas = int(os.getenv("DETECTAR_INCLUIR_PATRON_VELAS", 1))
        detectar_incluir_volume = int(os.getenv("DETECTAR_INCLUIR_VOLUME", 1))
        detectar_incluir_emas = int(os.getenv("DETECTAR_INCLUIR_EMAS", 1))
        detectar_incluir_adx = int(os.getenv("DETECTAR_INCLUIR_ADX", 1))   

        sl_callback_progresive = float(os.getenv("SL_CALLBACK_PROGRESIVE", 0.7))
        symbols_from = os.getenv("SYMBOLS_FROM", 'binance')

        soportes_resistencias = {}

    except ValueError as e:
        print(f"Error al convertir una variable de entorno: {e}")
