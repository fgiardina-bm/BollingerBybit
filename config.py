import os
from dotenv import load_dotenv


# Configuracion de la API
api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")
timeframe = os.getenv("TIMEFRAME", "5")  # Intervalo de tiempo 1,3,5,15,30,60,120,240,360,720,D,M,W

tp_porcent = float(os.getenv("TP_PORCENT", 0.2))  # Take profit porcentaje
sl_porcent = float(os.getenv("SL_PORCENT", 0.4))  # Stop loss porcentaje

cnt_symbols = int(os.getenv("CNT_SYMBOLS", 20))  # Cantidad de simbolos a buscar
account_percentage = int(os.getenv("ACCOUNT_PERCENTAGE", 4))
top_rsi = int(os.getenv("TOP_RSI", 87))
bottom_rsi = int(os.getenv("BOTTOM_RSI", 13))

sleep_rand_from = int(os.getenv("SLEEP_RAND_FROM", 10))
sleep_rand_to = int(os.getenv("SLEEP_RAND_TO", 20))


sl_callback_percentage = int(os.getenv("SL_CALLBACK_PERCENTAGE", 1))
verify_rsi = int(os.getenv("VERIFY_RSI", 5))
Bollinger_bands_width = int(os.getenv("BB_WIDTH", 5))
monitoring = int(os.getenv("MONITORING", 0))

def reload_config():
  
    global api_key
    global api_secret
    global timeframe
    global tp_porcent
    global sl_porcent
    global cnt_symbols
    global account_percentage
    global top_rsi
    global bottom_rsi
    global sleep_rand_from
    global sleep_rand_to
    global sl_callback_percentage
    global verify_rsi
    global Bollinger_bands_width
    global monitoring

    config_path = '.env'

    if timeframe == 240:
        config_path = '.env4'

    load_dotenv(config_path, override=True)

    api_key = os.getenv("API_KEY")
    api_secret = os.getenv("API_SECRET")
    timeframe = os.getenv("TIMEFRAME", "5")  # Intervalo de tiempo 1,3,5,15,30,60,120,240,360,720,D,M,W

    tp_porcent = float(os.getenv("TP_PORCENT", 0.2))  # Take profit porcentaje
    sl_porcent = float(os.getenv("SL_PORCENT", 0.4))  # Stop loss porcentaje

    cnt_symbols = int(os.getenv("CNT_SYMBOLS", 20))  # Cantidad de simbolos a buscar
    account_percentage = int(os.getenv("ACCOUNT_PERCENTAGE", 4))
    top_rsi = int(os.getenv("TOP_RSI", 87))
    bottom_rsi = int(os.getenv("BOTTOM_RSI", 13))

    sleep_rand_from = int(os.getenv("SLEEP_RAND_FROM", 10))
    sleep_rand_to = int(os.getenv("SLEEP_RAND_TO", 20))

    sl_callback_percentage = int(os.getenv("SL_CALLBACK_PERCENTAGE", 1))
    verify_rsi = int(os.getenv("VERIFY_RSI", 5))
    Bollinger_bands_width = int(os.getenv("BB_WIDTH", 5))
    monitoring = int(os.getenv("MONITORING", 0))