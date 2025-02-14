import numpy as np
import pandas as pd

class SoportesResistencias:
    def __init__(self, precios):
        self.precios = np.array(precios)
    
    def calcular_niveles(self, bins=20):
        """
        Encuentra los niveles de soporte y resistencia basándose en la frecuencia de precios cercanos.
        """
        hist, bin_edges = np.histogram(self.precios, bins=bins)
        niveles = (bin_edges[:-1] + bin_edges[1:]) / 2  # Centros de los bins
        niveles_importantes = niveles[hist > np.percentile(hist, 75)]  # Filtra los más significativos
        return niveles_importantes

    def consolidar_niveles(self, niveles_4h, niveles_diario, niveles_semanal, tolerancia=0.005):
        """
        Encuentra niveles comunes entre los distintos periodos.
        """
        niveles_totales = np.concatenate([niveles_4h, niveles_diario, niveles_semanal])
        niveles_filtrados = []
        
        for nivel in niveles_totales:
            if not any(abs(nivel - n) < tolerancia * nivel for n in niveles_filtrados):
                niveles_filtrados.append(nivel)
                
        return np.array(niveles_filtrados)
    
# Ejemplo de uso con datos ficticios
cierres_4h = np.random.normal(30000, 500, 200)  # Simulación de precios
cierres_diario = np.random.normal(30000, 700, 100)
cierres_semanal = np.random.normal(30000, 1000, 50)

sr = SoportesResistencias(cierres_4h)
niveles_4h = sr.calcular_niveles()

sr = SoportesResistencias(cierres_diario)
niveles_diario = sr.calcular_niveles()

sr = SoportesResistencias(cierres_semanal)
niveles_semanal = sr.calcular_niveles()

niveles_finales = sr.consolidar_niveles(niveles_4h, niveles_diario, niveles_semanal)

print("Soportes y resistencias fuertes:", niveles_finales)

# docker run --rm -it -v ./test_soportes_resistencias.py:/app/script.py --env-file .prod.env bot-bollinger-bybit