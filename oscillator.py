import pandas as pd
import numpy as np
from scipy.special import erf

def calculate_amazing_oscillator(df, short_window=5, long_window=34):
    midpoint_price = (df['high'] + df['low']) / 2
    short_sma = midpoint_price.rolling(window=short_window, min_periods=1).mean()
    long_sma = midpoint_price.rolling(window=long_window, min_periods=1).mean()
    amazing_osc = short_sma - long_sma
    return amazing_osc


def calculate_custom_rsi(amazing_osc, osc_period=20):
    delta = amazing_osc.diff()
    rise = delta.clip(lower=0)
    fall = -delta.clip(upper=0)
    avg_rise = rise.rolling(window=osc_period, min_periods=1).mean()
    avg_fall = fall.rolling(window=osc_period, min_periods=1).mean()
    rs = avg_rise / avg_fall
    custom_rsi = 100 - (100 / (1 + rs))
    custom_rsi = custom_rsi - 50  # Ajuste para centrar en cero
    return custom_rsi

def calculate_durations(custom_rsi):
    cross_zero = (custom_rsi * custom_rsi.shift(1) < 0).astype(int)
    durations = cross_zero.groupby((cross_zero != cross_zero.shift()).cumsum()).cumsum()
    durations = durations[cross_zero == 1]
    return durations

def calculate_reversal_probability(durations, current_duration):
    mean_duration = durations.mean()
    std_duration = durations.std()
    if std_duration == 0:
        return 0.0
    z_score = (current_duration - mean_duration) / std_duration
    probability = 0.5 * (1 + erf(z_score / np.sqrt(2)))
    return probability * 100  # Convertir a porcentaje


def trend_reversal_probability(df):
    amazing_osc = calculate_amazing_oscillator(df)
    custom_rsi = calculate_custom_rsi(amazing_osc)
    durations = calculate_durations(custom_rsi)
    current_duration = durations.iloc[-1] if not durations.empty else 0
    reversal_probability = calculate_reversal_probability(durations, current_duration)
    return reversal_probability
