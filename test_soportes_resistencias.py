"""
Módulo para el análisis de soportes y resistencias.
Permite detectar niveles importantes de precio en diferentes timeframes
y consolidarlos para encontrar los más significativos.
"""

import numpy as np
import pandas as pd
import matplotlib
# Configuración para entorno headless (sin interfaz gráfica) como Docker
matplotlib.use('Agg')  # Debe ejecutarse antes de importar pyplot
import matplotlib.pyplot as plt
from datetime import datetime
import argparse
import logging
from typing import Tuple, List, Optional, Dict, Any
import os

# Conexiones a APIs
from pybit.unified_trading import HTTP
import ccxt
from binance.client import Client

# Imports locales
from config import *
from functions import obtener_datos_historicos

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("soportes_resistencias.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("soportes_resistencias")

# Inicializar clientes
client = HTTP(api_key=api_key, api_secret=api_secret, testnet=False)
exchange = ccxt.binance()
clientb = Client("", "", tld="com")

class SoportesResistencias:
    """
    Clase para cálculo y análisis de niveles de soporte y resistencia.
    """
    
    def __init__(self, precios: np.ndarray):
        """
        Inicializa la clase con un array de precios.
        
        Args:
            precios: Array NumPy con los precios históricos.
        """
        self.precios = np.array(precios)
    
    def calcular_niveles(self, bins: int = 20) -> np.ndarray:
        """
        Encuentra los niveles de soporte y resistencia basándose en la frecuencia de precios cercanos.
        
        Args:
            bins: Número de bins para el histograma de precios.
            
        Returns:
            Array con los niveles importantes de soporte y resistencia.
        """
        hist, bin_edges = np.histogram(self.precios, bins=bins)
        niveles = (bin_edges[:-1] + bin_edges[1:]) / 2  # Centros de los bins
        niveles_importantes = niveles[hist > np.percentile(hist, 75)]  # Filtra los más significativos
        return niveles_importantes

    def consolidar_niveles(self, 
                           niveles_tf1: np.ndarray, 
                           niveles_tf2: np.ndarray, 
                           niveles_tf3: np.ndarray, 
                           tolerancia: float = 0.005) -> np.ndarray:
        """
        Encuentra niveles comunes entre los distintos periodos.
        
        Args:
            niveles_tf1: Niveles del primer timeframe.
            niveles_tf2: Niveles del segundo timeframe.
            niveles_tf3: Niveles del tercer timeframe.
            tolerancia: Porcentaje de proximidad para considerar dos niveles como el mismo (0.005 = 0.5%).
            
        Returns:
            Array con los niveles consolidados.
        """
        niveles_totales = np.concatenate([niveles_tf1, niveles_tf2, niveles_tf3])
        niveles_filtrados = []
        
        for nivel in niveles_totales:
            if not any(abs(nivel - n) < tolerancia * nivel for n in niveles_filtrados):
                niveles_filtrados.append(nivel)
                
        return np.array(sorted(niveles_filtrados))
        
    def encontrar_niveles_cercanos(self, 
                                  niveles: np.ndarray, 
                                  valor_actual: float,
                                  cnt: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Encuentra los dos soportes y dos resistencias más cercanas al valor actual.
        
        Args:
            niveles: Array con todos los niveles de soporte/resistencia.
            valor_actual: Precio actual del activo.
            
        Returns:
            Tupla con dos arrays: (soportes_cercanos, resistencias_cercanas)
        """
        niveles = np.array(niveles)
        soportes = niveles[niveles < valor_actual]
        resistencias = niveles[niveles > valor_actual]

        # Tomar los dos soportes más cercanos (ordenados de mayor a menor)
        soportes_cercanos = np.sort(soportes)[-cnt:] if len(soportes) >= cnt else soportes
        
        # Tomar las dos resistencias más cercanas (ordenados de menor a mayor)
        resistencias_cercanas = np.sort(resistencias)[:cnt] if len(resistencias) >= cnt else resistencias

        return soportes_cercanos, resistencias_cercanas
    
    def visualizar_niveles(self, 
                          precios: np.ndarray, 
                          niveles: np.ndarray, 
                          soportes_cercanos: np.ndarray, 
                          resistencias_cercanas: np.ndarray, 
                          valor_actual: float, 
                          titulo: str = "Niveles de Soporte y Resistencia",
                          guardar_ruta: Optional[str] = None) -> None:
        """
        Visualiza los precios históricos y los niveles de soporte y resistencia.
        
        Args:
            precios: Array con los precios históricos.
            niveles: Array con todos los niveles de S/R.
            soportes_cercanos: Array con los soportes cercanos al precio actual.
            resistencias_cercanas: Array con las resistencias cercanas al precio actual.
            valor_actual: Precio actual del activo.
            titulo: Título para el gráfico.
            guardar_ruta: Si se especifica, guarda la figura en esta ruta.
        """
        plt.figure(figsize=(14, 8))
        
        # Gráfico de precios
        plt.plot(range(len(precios)), precios, color='blue', alpha=0.6, label="Precio")
        
        # Línea de precio actual
        plt.axhline(valor_actual, color='black', linestyle='-', linewidth=1.5, 
                   label=f"Precio actual: {valor_actual:.4f}")
        
        # Dibujar todos los niveles
        for nivel in niveles:
            plt.axhline(nivel, color='gray', linestyle='--', alpha=0.3)
        
        # Destacar los soportes cercanos
        for soporte in soportes_cercanos:
            plt.axhline(soporte, color='green', linestyle='-', linewidth=1.5, 
                       label=f"Soporte: {soporte:.4f} ({((soporte/valor_actual)-1)*100:.2f}%)")
        
        # Destacar las resistencias cercanas
        for resistencia in resistencias_cercanas:
            plt.axhline(resistencia, color='red', linestyle='-', linewidth=1.5, 
                       label=f"Resistencia: {resistencia:.4f} ({((resistencia/valor_actual)-1)*100:.2f}%)")
        
        plt.title(titulo, fontsize=16)
        plt.xlabel("Periodos", fontsize=12)
        plt.ylabel("Precio", fontsize=12)
        plt.legend(loc='best')
        plt.grid(True, alpha=0.3)
        
        if guardar_ruta:
            plt.savefig(guardar_ruta)
            logger.info(f"Gráfico guardado en {guardar_ruta}")
            
        # No mostrar en Docker ya que no hay interfaz gráfica
        # plt.show() lo reemplazamos con:
        if 'DOCKER_CONTAINER' not in os.environ:
            plt.show()
        plt.close()  # Cerrar la figura para liberar memoria


def obtener_datos_binance(symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    """
    Obtiene datos históricos de Binance.
    
    Args:
        symbol: Símbolo del activo.
        timeframe: Intervalo de tiempo (1m, 5m, 15m, 1h, 1d, etc.).
        limit: Cantidad de velas a obtener.
        
    Returns:
        DataFrame con los datos OHLCV.
    """
    try:
        continuous_klines = clientb.futures_klines(
            symbol=symbol, interval=timeframe, limit=limit
        )

        data = []
        for ck in continuous_klines:
            item = {
                "open": float(ck[1]),
                "high": float(ck[2]),
                "low": float(ck[3]),
                "close": float(ck[4]),
                "volume": float(ck[5]),
            }
            data.append(item)

        df = pd.DataFrame(data)
        return df
    except Exception as e:
        logger.error(f"Error al obtener datos de Binance: {e}")
        return pd.DataFrame()


def obtener_precio_actual(symbol: str) -> float:
    """
    Obtiene el precio actual del activo.
    
    Args:
        symbol: Símbolo del activo.
        
    Returns:
        Precio actual como float.
    """
    try:
        ticker = client.get_tickers(category='linear', symbol=symbol)
        precio = float(ticker['result']['list'][0]['lastPrice'])
        return precio
    except Exception as e:
        logger.error(f"Error al obtener el precio actual de {symbol}: {e}")
        raise


def guardar_resultados(symbol: str, 
                      valor_actual: float, 
                      soportes: np.ndarray, 
                      resistencias: np.ndarray, 
                      nombre_archivo: str = None) -> None:
    """
    Guarda los resultados del análisis en un archivo de texto.
    
    Args:
        symbol: Símbolo del activo.
        valor_actual: Precio actual del activo.
        soportes: Array con los soportes cercanos.
        resistencias: Array con las resistencias cercanas.
        nombre_archivo: Nombre del archivo donde guardar los resultados.
    """
    if nombre_archivo is None:
        nombre_archivo = f"sr_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
    with open(nombre_archivo, 'w') as f:
        f.write(f"Análisis de Soportes y Resistencias\n")
        f.write(f"=================================\n")
        f.write(f"Símbolo: {symbol}\n")
        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Precio actual: {valor_actual:.4f}\n\n")
        
        f.write("Soportes:\n")
        for s in soportes:
            porcentaje = ((s/valor_actual)-1)*100
            f.write(f"  {s:.4f} ({porcentaje:.2f}%)\n")
        
        f.write("\nResistencias:\n")
        for r in resistencias:
            porcentaje = ((r/valor_actual)-1)*100
            f.write(f"  {r:.4f} ({porcentaje:.2f}%)\n")
            
    logger.info(f"Resultados guardados en {nombre_archivo}")


def parse_args() -> argparse.Namespace:
    """
    Parsea los argumentos de línea de comandos.
    
    Returns:
        Objeto con los argumentos parseados.
    """
    parser = argparse.ArgumentParser(description='Análisis de soportes y resistencias')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Símbolo a analizar')
    parser.add_argument('--frame1', type=str, default='240', help='Primer timeframe')
    parser.add_argument('--frame2', type=str, default='D', help='Segundo timeframe')
    parser.add_argument('--frame3', type=str, default='W', help='Tercer timeframe')
    parser.add_argument('--tolerancia', type=float, default=0.005, help='Tolerancia para consolidar niveles')
    parser.add_argument('--guardar', action='store_true', help='Guardar resultados y gráfico')
    parser.add_argument('--sin-grafico', action='store_true', help='No mostrar gráfico')
    return parser.parse_args()


def main() -> None:
    """
    Función principal que ejecuta el análisis de soportes y resistencias.
    """
    # Parsear argumentos
    args = parse_args()
    symbol = args.symbol
    frame1 = args.frame1
    frame2 = args.frame2
    frame3 = args.frame3
    tolerancia = args.tolerancia
    
    logger.info(f"Iniciando análisis para {symbol}")
    logger.info(f"Timeframes: {frame1}, {frame2}, {frame3}")
    
    try:
        # Obtener datos para diferentes timeframes
        logger.info(f"Obteniendo datos para timeframe {frame1}")
        data1 = obtener_datos_historicos(symbol, frame1, 200)
        if data1 is None or len(data1[4]) == 0:
            raise ValueError(f"No se pudieron obtener datos para {symbol} en timeframe {frame1}")
        i1 = np.array(data1[4])  # Precios de cierre
        
        logger.info(f"Obteniendo datos para timeframe {frame2}")
        data2 = obtener_datos_historicos(symbol, frame2, 100)
        if data2 is None or len(data2[4]) == 0:
            raise ValueError(f"No se pudieron obtener datos para {symbol} en timeframe {frame2}")
        i2 = np.array(data2[4])  # Precios de cierre
        
        logger.info(f"Obteniendo datos para timeframe {frame3}")
        data3 = obtener_datos_historicos(symbol, frame3, 50)
        if data3 is None or len(data3[4]) == 0:
            raise ValueError(f"No se pudieron obtener datos para {symbol} en timeframe {frame3}")
        i3 = np.array(data3[4])  # Precios de cierre
        
        # Calcular niveles de soporte y resistencia
        logger.info("Calculando niveles de S/R para cada timeframe")
        sr = SoportesResistencias(i1)
        niveles_1 = sr.calcular_niveles()
        
        sr = SoportesResistencias(i2)
        niveles_2 = sr.calcular_niveles()
        
        sr = SoportesResistencias(i3)
        niveles_3 = sr.calcular_niveles()
        
        # Consolidar niveles
        logger.info("Consolidando niveles de S/R")
        niveles_finales = sr.consolidar_niveles(niveles_1, niveles_2, niveles_3, tolerancia)
        
        # Obtener el valor actual
        logger.info("Obteniendo precio actual")
        valor_actual = obtener_precio_actual(symbol)
        
        # Encontrar soportes y resistencias cercanos
        logger.info("Identificando soportes y resistencias cercanos")
        soportes_cercanos, resistencias_cercanas = sr.encontrar_niveles_cercanos(niveles_finales, valor_actual, 3)
        
        # Mostrar resultados
        print(f"\nAnálisis de soporte y resistencia para {symbol}")
        print(f"Precio actual: {valor_actual:.4f}")
        
        print(f"\nResistencias cercanas:")
        for r in resistencias_cercanas:
            porcentaje = ((r/valor_actual)-1)*100
            print(f"  {r:.4f} ({porcentaje:.2f}%)")

        print(f"\nSoportes cercanos:")
        for s in soportes_cercanos:
            porcentaje = ((s/valor_actual)-1)*100
            print(f"  {s:.4f} ({porcentaje:.2f}%)")

        # Guardar resultados si se solicita
        if args.guardar:
            fecha_hora = datetime.now().strftime('%Y%m%d_%H%M%S')
            guardar_resultados(symbol, valor_actual, soportes_cercanos, resistencias_cercanas, 
                              f"sr_{symbol}_{fecha_hora}.txt")
            ruta_grafico = f"sr_{symbol}_{fecha_hora}.png"
        else:
            ruta_grafico = None
        
        # Visualizar niveles si no se solicita lo contrario
        if not args.sin_grafico:
            sr = SoportesResistencias(i1)  # Usar datos de timeframe más pequeño para visualización
            # Siempre guardar ruta en Docker para poder acceder a la imagen
            if 'DOCKER_CONTAINER' in os.environ and ruta_grafico is None:
                fecha_hora = datetime.now().strftime('%Y%m%d_%H%M%S')
                ruta_grafico = f"/app/output/sr_{symbol}_{fecha_hora}.png"
            
            sr.visualizar_niveles(
                i1, niveles_finales, soportes_cercanos, resistencias_cercanas, valor_actual,
                titulo=f"Niveles S/R para {symbol} (Timeframes: {frame1}, {frame2}, {frame3})",
                guardar_ruta=ruta_grafico
            )
        
        logger.info("Análisis completado exitosamente")
        
    except Exception as e:
        logger.error(f"Error al procesar datos: {e}", exc_info=True)
        print(f"Error: {e}")


if __name__ == "__main__":
    main()

# docker run --rm -it -v ./test_soportes_resistencias.py:/app/script.py -v ./config.py:/app/config.py -v ./functions.py:/app/functions.py --env-file .prod.env bot-bollinger-bybit python /app/script.py --symbol BTCUSDT --frame1 15 --frame2 60 --frame3 240 --tolerancia 0.005
# docker run --rm -it -v ./test_soportes_resistencias.py:/app/script.py -v ./config.py:/app/config.py -v ./functions.py:/app/functions.py -v ./output/:/app/output/ --env-file .prod.env bot-bollinger-bybit python /app/script.py --symbol RUNEUSDT --frame1 15 --frame2 60 --frame3 240 --tolerancia 0.005