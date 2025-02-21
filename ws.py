from pybit.unified_trading import WebSocket
from time import sleep

# docker run --rm -it -v ./ws.py:/app/script.py  -v ./pybit.log:/app/pybit.log --name bbpy fgiardina/bbpy   

# Set up logging (optional)
import logging
logging.basicConfig(filename="pybit.log", level=logging.DEBUG,
                    format="%(asctime)s %(levelname)s %(message)s")


ws = WebSocket(
    testnet=False,
    channel_type="linear",
    trace_logging=True,
)
# ws_private = WebSocket(
#     testnet=True,
#     channel_type="private",
#     api_key="...",
#     api_secret="...",
#     trace_logging=True,
# )


def handle_message(message):
    print(message)

# ws.trade_stream("BTCUSDT", handle_message)
# ws.ticker_stream("BTCUSDT", handle_message)
# ws.insurance_fund_stream("BTCUSDT", handle_message)
# ws.funding_rate_stream("BTCUSDT", handle_message)
# ws.liquidation_stream("BTCUSDT", handle_message)
# ws.position_stream("BTCUSDT", handle_message)
# ws.account_stream(handle_message)
# ws.wallet_stream(handle_message)
# ws.execution_stream("BTCUSDT", handle_message)


ws.orderbook_stream(50, "BTCUSDT", handle_message)
# ws_private.position_stream(handle_message)
# ws_private.order_stream(callback=handle_message)
while True:
    sleep(1)