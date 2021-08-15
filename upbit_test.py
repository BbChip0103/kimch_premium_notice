import asyncio
import websockets
import json
import ccxt


async def upbit_ws_client(callback):
    uri = 'wss://api.upbit.com/websocket/v1'
    async with websockets.connect(uri) as websocket:
        subscribe_fmt = [
            {'ticket': 'bbchip13'},
            {
                'type': 'ticker',
                'codes': ['KRW-XRP'],
                'isOnlyRealtime': True
            },
            {
                'type': 'ticker',
                'codes': ['KRW-BTC'],
                'isOnlyRealtime': True
            },
            {'format': 'SIMPLE'}
        ]
        subscribe_data = json.dumps(subscribe_fmt)
        await websocket.send(subscribe_data)

        while True:
            await callback(await websocket.recv())


async def response_message(res, **kwargs):
    # print(json.loads(args))
#    print(res)
    coin_inform = json.loads(res)
    print(coin_inform['cd'], coin_inform['tp'])
#    print()

upbit_exchange_id = 'upbit'
upbit_exchange_class = getattr(ccxt, upbit_exchange_id)
upbit_exchange = upbit_exchange_class({
    'apiKey': 'YOUR_APP_KEY',
    'secret': 'YOUR_SECRET',
})

upbit_coin_dict = {
    k:v for k, v in upbit_exchange.load_markets().items() 
      if '/krw' in k.lower()
}
upbit_coin_list = [name.replace('/KRW', '') for name in list(upbit_coin_dict.keys())]

# print(len(upbit_coin_list), upbit_coin_list[:3])

tasks = [
    asyncio.ensure_future(upbit_ws_client(response_message)),
]
event_loop = asyncio.get_event_loop()
event_loop.run_until_complete(asyncio.wait(tasks))
# event_loop.stop()

