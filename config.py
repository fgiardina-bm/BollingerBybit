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
top_rsi = int(os.getenv(TOP_RSI, 87))
bottom_rsi = int(os.getenv(BOTTOM_RSI, 13))

sleep_rand_from = int(os.getenv(SLEEP_RAND_FROM, 10))
sleep_rand_to = int(os.getenv(SLEEP_RAND_TO, 20))

sl_callback_percentage = int(os.getenv(SL_CALLBACK_PERCENTAGE, 1))
verify_rsi = int(os.getenv(VERIFY_RSI, 5))
Bollinger_bands_width = int(os.getenv(BB_WIDTH, 5))
monitoring = int(os.getenv(MONITORING, 0))
max_ops = int(os.getenv(MAX_OPS, 1))
max_ops_short = int(os.getenv(MAX_OPS_SHORT, 2))
max_ops_long = int(os.getenv(MAX_OPS_LONG, 2))

config_lock = threading.Lock()

opened_positions = [];
opened_positions_short = [];
opened_positions_long = [];

def reload_config():

    global api_key, api_secret, timeframe, tp_porcent, sl_porcent, cnt_symbols
    global account_percentage, top_rsi, bottom_rsi, sleep_rand_from, sleep_rand_to
    global sl_callback_percentage, verify_rsi, Bollinger_bands_width, monitoring, max_ops
    global opened_positions, opened_positions_short, opened_positions_long
    global max_ops_short, max_ops_long
    
    while True:
        with config_lock:
            log_path = f"logs/log-{timeframe}-{time.strftime('%Y%m%d')}.txt"
            with open(log_path, "a") as log_file:
                log_file.write(str(timeframe) + '|' + time.strftime('%Y-%m-%d %H:%M:%S') + " reload_config\n")

            config_path = '.env'

            if timeframe == 240:
                config_path = '.env4'

            load_dotenv(config_path, override=True)

            try:
                api_key = os.getenv(API_KEY)
                api_secret = os.getenv(API_SECRET)
                timeframe = int(os.getenv(TIMEFRAME, "5"))

                tp_porcent = float(os.getenv(TP_PORCENT, 2))
                sl_porcent = float(os.getenv(SL_PORCENT, 1))

                cnt_symbols = int(os.getenv(CNT_SYMBOLS, 20))
                account_percentage = int(os.getenv(ACCOUNT_PERCENTAGE, 4))
                top_rsi = int(os.getenv(TOP_RSI, 87))
                bottom_rsi = int(os.getenv(BOTTOM_RSI, 13))

                sleep_rand_from = int(os.getenv(SLEEP_RAND_FROM, 10))
                sleep_rand_to = int(os.getenv(SLEEP_RAND_TO, 20))

                sl_callback_percentage = int(os.getenv(SL_CALLBACK_PERCENTAGE, 1))
                verify_rsi = int(os.getenv(VERIFY_RSI, 5))
                Bollinger_bands_width = int(os.getenv(BB_WIDTH, 5))
                monitoring = int(os.getenv(MONITORING, 0))
                max_ops = int(os.getenv(MAX_OPS, 1))
                max_ops_short = int(os.getenv(MAX_OPS_SHORT, 2))
                max_ops_long = int(os.getenv(MAX_OPS_LONG, 2))

            except ValueError as e:
                print(f"Error al convertir una variable de entorno: {e}")


        time.sleep(60)
  