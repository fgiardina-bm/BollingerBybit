import requests
import json
from datetime import datetime
from collections import defaultdict

def encontrar_mayores_bloques_orderbook(rango_porcentaje=10.0, agrupacion_ticks=50):
    """
    Encuentra los mayores bloques de soporte y resistencia en un rango del 10%
    
    Args:
        rango_porcentaje (float): Porcentaje de rango a analizar (10% = ±10%)
        agrupacion_ticks (int): Agrupar precios cada X USDT
    """
    print("🔍 Buscando MAYORES BLOQUES en orderbook BTC/USDT (Rango 10%)...")
    
    # Obtener orderbook
    url = "https://api.binance.com/api/v3/depth"
    params = {'symbol': 'BTCUSDT', 'limit': 5000}
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        # Precio actual
        precio_actual = float(data['bids'][0][0])
        
        # Calcular rangos del 10%
        rango_superior = precio_actual * (1 + rango_porcentaje/100)
        rango_inferior = precio_actual * (1 - rango_porcentaje/100)
        
        print(f"💰 Precio actual: ${precio_actual:,.2f}")
        print(f"📊 Rango de análisis 10%: ${rango_inferior:,.2f} - ${rango_superior:,.2f}")
        print(f"🎯 Diferencia: ±${(precio_actual * rango_porcentaje/100):,.0f} USDT")
        
        # Agrupar órdenes por niveles
        niveles_compra = defaultdict(lambda: {'cantidad': 0, 'valor_usd': 0, 'ordenes': 0})
        niveles_venta = defaultdict(lambda: {'cantidad': 0, 'valor_usd': 0, 'ordenes': 0})
        
        # Procesar BIDS (órdenes de compra) - SOPORTES
        for bid in data['bids']:
            precio = float(bid[0])
            cantidad = float(bid[1])
            
            if rango_inferior <= precio <= precio_actual:
                nivel = int(precio / agrupacion_ticks) * agrupacion_ticks
                niveles_compra[nivel]['cantidad'] += cantidad
                niveles_compra[nivel]['valor_usd'] += precio * cantidad
                niveles_compra[nivel]['ordenes'] += 1
        
        # Procesar ASKS (órdenes de venta) - RESISTENCIAS
        for ask in data['asks']:
            precio = float(ask[0])
            cantidad = float(ask[1])
            
            if precio_actual <= precio <= rango_superior:
                nivel = int(precio / agrupacion_ticks) * agrupacion_ticks
                niveles_venta[nivel]['cantidad'] += cantidad
                niveles_venta[nivel]['valor_usd'] += precio * cantidad
                niveles_venta[nivel]['ordenes'] += 1
        
        # ENCONTRAR EL MAYOR BLOQUE DE SOPORTE
        if niveles_compra:
            mayor_soporte = max(niveles_compra.items(), key=lambda x: x[1]['valor_usd'])
            precio_soporte = mayor_soporte[0]
            datos_soporte = mayor_soporte[1]
            distancia_soporte = ((precio_actual - precio_soporte) / precio_actual) * 100
            
            print(f"\n🟢 MAYOR BLOQUE DE SOPORTE:")
            print(f"   💪 Precio: ${precio_soporte:,.0f}")
            print(f"   📊 Volumen: {datos_soporte['cantidad']:.2f} BTC")
            print(f"   💰 Valor: ${datos_soporte['valor_usd']:,.0f}")
            print(f"   📈 Órdenes: {datos_soporte['ordenes']:,}")
            print(f"   📍 Distancia: {distancia_soporte:.2f}% por debajo del precio actual")
        
        # ENCONTRAR EL MAYOR BLOQUE DE RESISTENCIA
        if niveles_venta:
            mayor_resistencia = max(niveles_venta.items(), key=lambda x: x[1]['valor_usd'])
            precio_resistencia = mayor_resistencia[0]
            datos_resistencia = mayor_resistencia[1]
            distancia_resistencia = ((precio_resistencia - precio_actual) / precio_actual) * 100
            
            print(f"\n🔴 MAYOR BLOQUE DE RESISTENCIA:")
            print(f"   💪 Precio: ${precio_resistencia:,.0f}")
            print(f"   📊 Volumen: {datos_resistencia['cantidad']:.2f} BTC")
            print(f"   💰 Valor: ${datos_resistencia['valor_usd']:,.0f}")
            print(f"   📈 Órdenes: {datos_resistencia['ordenes']:,}")
            print(f"   📍 Distancia: {distancia_resistencia:.2f}% por encima del precio actual")
        
        # MOSTRAR TOP 5 DE CADA LADO
        print(f"\n📊 TOP 5 BLOQUES DE SOPORTE (Mayor volumen):")
        print("Rank  Precio      Volumen BTC  Valor USD       Distancia %")
        print("-" * 60)
        
        soportes_top = sorted(niveles_compra.items(), key=lambda x: x[1]['valor_usd'], reverse=True)[:5]
        for i, (nivel, datos) in enumerate(soportes_top):
            distancia = ((precio_actual - nivel) / precio_actual) * 100
            print(f"{i+1:2d}.   ${nivel:>8,.0f}    {datos['cantidad']:>8.2f}    ${datos['valor_usd']:>12,.0f}    {distancia:>6.2f}%")
        
        print(f"\n📊 TOP 5 BLOQUES DE RESISTENCIA (Mayor volumen):")
        print("Rank  Precio      Volumen BTC  Valor USD       Distancia %")
        print("-" * 60)
        
        resistencias_top = sorted(niveles_venta.items(), key=lambda x: x[1]['valor_usd'], reverse=True)[:5]
        for i, (nivel, datos) in enumerate(resistencias_top):
            distancia = ((nivel - precio_actual) / precio_actual) * 100
            print(f"{i+1:2d}.   ${nivel:>8,.0f}    {datos['cantidad']:>8.2f}    ${datos['valor_usd']:>12,.0f}    {distancia:>6.2f}%")
        
        # RESUMEN EJECUTIVO
        print(f"\n" + "="*70)
        print(f"🎯 RESUMEN EJECUTIVO - MAYORES BLOQUES EN RANGO 10%:")
        print(f"="*70)
        if niveles_compra and niveles_venta:
            print(f"🟢 SOPORTE MÁS FUERTE: ${precio_soporte:,.0f} ({distancia_soporte:.2f}% abajo)")
            print(f"   💰 Valor del bloque: ${datos_soporte['valor_usd']:,.0f}")
            print(f"🔴 RESISTENCIA MÁS FUERTE: ${precio_resistencia:,.0f} ({distancia_resistencia:.2f}% arriba)")
            print(f"   💰 Valor del bloque: ${datos_resistencia['valor_usd']:,.0f}")
            
            # Análisis de fuerza relativa
            if datos_soporte['valor_usd'] > datos_resistencia['valor_usd']:
                diferencia = ((datos_soporte['valor_usd'] - datos_resistencia['valor_usd']) / datos_resistencia['valor_usd']) * 100
                print(f"⚖️  El SOPORTE es {diferencia:.1f}% más fuerte que la RESISTENCIA")
            else:
                diferencia = ((datos_resistencia['valor_usd'] - datos_soporte['valor_usd']) / datos_soporte['valor_usd']) * 100
                print(f"⚖️  La RESISTENCIA es {diferencia:.1f}% más fuerte que el SOPORTE")
        
        return {
            'precio_actual': precio_actual,
            'mayor_soporte': {'precio': precio_soporte, 'datos': datos_soporte} if niveles_compra else None,
            'mayor_resistencia': {'precio': precio_resistencia, 'datos': datos_resistencia} if niveles_venta else None
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    # Ejecutar análisis
    resultado = encontrar_mayores_bloques_orderbook(rango_porcentaje=10.0, agrupacion_ticks=100)