import asyncio
import json
import time
import ccxt
import websockets
import redis
from binance import AsyncClient, DepthCacheManager, BinanceSocketManager
import os

if os.name == 'nt':
    import requests
else:
    import pycurl
    from io import BytesIO
    import certifi


async def upbit_ws_client(coin_list, redis_obj):
    uri = 'wss://api.upbit.com/websocket/v1'
    async with websockets.connect(uri) as websocket:
        subscribe_fmt = [
            {'ticket': 'bbchip13'},
            {'format': 'SIMPLE'}
        ]
        subscribe_fmt += [
            {
                'type': 'ticker',
                'codes': ['KRW-{}'.format(coin_name)],
                'isOnlyRealtime': True
            } for coin_name in coin_list
        ] 

        subscribe_data = json.dumps(subscribe_fmt)
        await websocket.send(subscribe_data)

        while True:
            res = await websocket.recv()
            res = json.loads(res)
            coin_name = res['cd'].replace('KRW-', '')
            price = res['tp']
            # print(coin_name, price)

            redis_obj.set('UPBIT_'+coin_name, price)
            
            redis_obj.set('UPBIT_READY', 1)


async def binance_ws_client(coin_list, redis_obj):
    client = await AsyncClient.create()

    while True:
        usd_price = get_usd_price()

        for coin_name in coin_list:
            res = await client.get_symbol_ticker(
                # symbol=['BTCUSDT', 'ETHUSDT']
                symbol=coin_name+'USDT'
            )
            res['symbol'] = res['symbol'].replace('USDT', '')
            res['price'] = float(res['price']) * usd_price
            coin_name = res['symbol']
            price = res['price']
            # print(coin_name, price)

            redis_obj.set('BINANCE_'+coin_name, price)
        redis_obj.set('BINANCE_READY', 1)


def get_upbit_coin_list():
    upbit_exchange_id = 'upbit'
    upbit_exchange_class = getattr(ccxt, upbit_exchange_id)
    upbit_exchange = upbit_exchange_class({
        'apiKey': 'YOUR_APP_KEY',
        'secret': 'YOUR_SECRET',
    })

    upbit_coin_dict = {
        k:v for k, v in upbit_exchange.load_markets().items() 
            if '/KRW' in k
    }
    upbit_coin_list = [
        name.replace('/KRW', '') for name in list(upbit_coin_dict.keys())
    ]
    return upbit_coin_list


def get_binance_coin_list():
    binance_exchange_id = 'binance'
    binance_exchange_class = getattr(ccxt, binance_exchange_id)
    binance_exchange = binance_exchange_class({
        'apiKey': 'YOUR_APP_KEY',
        'secret': 'YOUR_SECRET',
    })

    binance_coin_dict = {
        k:v for k, v in binance_exchange.load_markets().items() 
            if '/USDT' in k and v['active'] == True
    }
    binance_coin_list = [
        name.replace('/USDT', '') for name in list(binance_coin_dict.keys())
    ]
    return binance_coin_list


def get_usd_price():
    url = 'https://quotation-api-cdn.dunamu.com/v1/forex/recent?codes=FRX.KRWUSD'
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
    if os.name == 'nt':
        exchange =requests.get(url, headers=headers).json()
        return exchange[0]['basePrice']
    else:
        buffer = BytesIO()
        c = pycurl.Curl()

        c.setopt(c.URL, url)
        c.setopt(c.WRITEDATA, buffer)
        c.setopt(c.CAINFO, certifi.where())
        c.setopt(pycurl.HTTPHEADER, [
            'Content-type:application/json;charset=utf-8',
            'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'
        ])

        c.perform()
        # print('Status: %d' % c.getinfo(c.RESPONSE_CODE))
        # print('TOTAL_TIME: %f' % c.getinfo(c.TOTAL_TIME))
        c.close()

        body = buffer.getvalue()
        result = json.loads(body)
        return result[0]['basePrice']


def main_loop(overlapped_coin_list, redis_obj):
    while True:
        print(int(redis_obj.get('UPBIT_READY')))
        if redis_obj.get('UPBIT_READY') == 1 and redis_obj.get('UPBIT_READY') == 1:
            for coin_name in overlapped_coin_list:
                upbit_price = redis_obj.get('UPBIT_{}'.format(coin_name))
                binance_price = redis_obj.get('BINANCE_{}'.format(coin_name))
                price_ratio = (upbit_price / binance_price) - 1
                print(coin_name, price_ratio)
        else:
            time.sleep(1)


if __name__ == "__main__":
    redis_object = redis.StrictRedis(host='localhost', port=6379, db=0)
    redis_object.set('UPBIT_READY', 0)
    redis_object.set('BINANCE_READY', 0)

    upbit_coin_list = get_upbit_coin_list()
    binance_coin_list = get_binance_coin_list()
    overlapped_coin_list = list(set(upbit_coin_list)&set(binance_coin_list)) 

    tasks = [
        asyncio.ensure_future(
            binance_ws_client(overlapped_coin_list, redis_object),
        ),
        asyncio.ensure_future(
            upbit_ws_client(overlapped_coin_list, redis_object)
        ),
        asyncio.ensure_future(
            main_loop(overlapped_coin_list, redis_object)
        )        
    ]
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(asyncio.wait(tasks))

