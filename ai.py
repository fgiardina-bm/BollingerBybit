import pandas as pd
import numpy as np
import talib
import ccxt
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import RandomUnderSampler
from xgboost import XGBClassifier
from sklearn.exceptions import NotFittedError

def get_historical_data_binance(symbol="BTC/USDT", interval="1h", limit=500):
    """Obtiene datos de Binance usando ccxt."""
    exchange = ccxt.binance()
    ohlcv = exchange.fetch_ohlcv(symbol, interval, limit=limit)
    
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    
    return df

def generate_signals(df):
    """Calcula indicadores técnicos y genera señales de trading."""
    df["rsi"] = talib.RSI(df["close"], timeperiod=14)
    df["macd"], df["macdsignal"], _ = talib.MACD(df["close"], fastperiod=12, slowperiod=26, signalperiod=9)
    df["ema_9"] = talib.EMA(df["close"], timeperiod=9)  # Agregado nuevamente
    df["ema_12"] = talib.EMA(df["close"], timeperiod=12)
    df["ema_26"] = talib.EMA(df["close"], timeperiod=26)
    df["upper_bb"], df["middle_bb"], df["lower_bb"] = talib.BBANDS(df["close"], timeperiod=20)

    df["adx"] = talib.ADX(df["high"], df["low"], df["close"], timeperiod=14)

    # Generar señales de trading
    df["long_signal"] = ((df["macd"] > df["macdsignal"]) & (df["rsi"] < 40) & (df["close"] > df["ema_9"])).astype(int)
    df["short_signal"] = ((df["macd"] < df["macdsignal"]) & (df["rsi"] > 65) & (df["close"] < df["ema_9"])).astype(int)

    df["signal"] = df["long_signal"] - df["short_signal"]  # -1 para short, 0 neutral, 1 para long

    return df.dropna()

def train_model(df, use_xgboost=True):
    """Entrena el modelo de Machine Learning con SMOTE si hay suficientes datos."""
    
    features = ["open", "high", "low", "close", "volume", "rsi", "macd", "macdsignal", "ema_9", "ema_12", "adx", "upper_bb", "lower_bb"]
    features = [col for col in features if col in df.columns]  # Filtrar solo columnas existentes

    X = df[features]
    y = df["signal"].copy()

    print("\nDistribución antes del balanceo:\n", y.value_counts())

    # Ajustar las clases para XGBoost
    y = y.replace({-1: 2})  # Cambia -1 a 2 (XGBoost no acepta valores negativos en clasificación)

    min_samples = y.value_counts().min()
    
    if min_samples < 2:
        print("⚠ No hay suficientes datos en todas las clases. No se aplicará SMOTE.")
        X_resampled, y_resampled = X, y
        stratify_option = None
    else:
        print(f"✅ Aplicando SMOTE con k_neighbors={min(5, min_samples - 1)}...")
        smote = SMOTE(k_neighbors=min(1, min_samples - 1), random_state=42)
        X_resampled, y_resampled = smote.fit_resample(X, y)
        stratify_option = y_resampled if min_samples >= 2 else None

    # Escalar características
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_resampled)

    # Dividir en train/test
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y_resampled, test_size=0.2, random_state=42, stratify=stratify_option)

    # Selección de modelo
    model = XGBClassifier(n_estimators=200, use_label_encoder=False, eval_metric="mlogloss", random_state=42) if use_xgboost else RandomForestClassifier(n_estimators=200, random_state=42)

    # Entrenar modelo
    model.fit(X_train, y_train)

    # Evaluar precisión
    accuracy = model.score(X_test, y_test)
    print(f"✅ Precisión del modelo después del balanceo: {accuracy:.4f}")

    return model, scaler

def predict_signal(df, model, scaler):
    """Genera predicciones de señales con el modelo entrenado."""
    features = ["open", "high", "low", "close", "volume", "rsi", "macd", "macdsignal", "ema_9", "ema_12", "adx", "upper_bb", "lower_bb"]
    features = [col for col in features if col in df.columns]  # Evita errores por columnas faltantes

    try:
        X = df[features]
        X_scaled = scaler.transform(X)
        df["prediction"] = model.predict(X_scaled)

        # Volver a convertir 2 → -1 (short)
        df["prediction"] = df["prediction"].replace({2: -1})

        # Mostrar distribución de predicciones
        print("\nDistribución de predicciones en el dataset:")
        print(df["prediction"].value_counts())

        return df
    except KeyError as e:
        print(f"❌ Error: Faltan columnas en los datos para hacer predicciones: {e}")
        return df
    except NotFittedError:
        print("❌ Error: El modelo no ha sido entrenado. Entrene el modelo antes de predecir.")
        return df

# Ejecutar script
symbol = "TRUMP/USDT"
df = get_historical_data_binance(symbol, "1h", 500)
df = generate_signals(df)


# Seleccionar solo las columnas específicas que quieres ver
columns_to_keep = [
    "timestamp", "close", "rsi", "macd", "macdsignal", 
    "ema_9", "upper_bb", "middle_bb", "lower_bb", 
    "long_signal", "short_signal"
]

df = df[columns_to_keep]

# Mostrar el DataFrame después de generar las señales
print("\nVistazo general a los datos procesados:")
print(df.tail())
