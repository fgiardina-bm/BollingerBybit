### Bot de bandas de Bollinger para Bybit

Este bot fue desarrollado para usar las bandas de bollinger en bybit, el bot abre operaciones simples con stop loss y take profit, lo puedes configurar como quieras. recuerda que debes usar las Apis de Bybit.

**Como usar el script**
- Descargar python [Aqui](https://www.python.org/ "Aqui")
- Descargar y modificar el Archivo config.py, el archivo lo puedes modificar con sublime text, el cual puedes descargar [Aqui](https://www.sublimetext.com/ "Aqui")
- Agrega la API KEY y la API SECRET
```python
# Configuracion de la API
api_key = "APIKEY"
api_secret = "APISECRET"
symbol = "XRPUSDT" # Moneda que deseas operar
timeframe = "5"  # Intervalo de tiempo 1,3,5,15,30,60,120,240,360,720,D,M,W
usdt = 10  # Cantidad de dolares para abrir posicion.

tp_porcent = 0.2  # Take profit porcentaje
sl_porcent = 0.4  # Stop loss porcentaje
```
- Antes de ejecutar el Script deberas instalar la libreria de Python de Bybit `pip install pybit`
- Una vez guardado el archivo debes ejecutarlo desde una terminal de windows o de tu sistema operativo que uses con el siguiente comando.
`python script.py`

**NOTA: Para que funcione bien no debes estar en modo Cobertura**

#### Contact
- Twitter: [https://twitter.com/ElGafasTrading](https://twitter.com/ElGafasTrading "https://twitter.com/ElGafasTrading")
- Instagram: [https://www.instagram.com/elgafastrading/](https://www.instagram.com/elgafastrading/ "https://www.instagram.com/elgafastrading/")
- Youtube: [https://www.youtube.com/@ElGafasTrading](https://www.youtube.com/@ElGafasTrading "https://www.youtube.com/@ElGafasTrading")
