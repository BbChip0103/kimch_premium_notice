import asyncio
import json
import time
import ccxt

from binance import AsyncClient, DepthCacheManager, BinanceSocketManager

import os 

async def binance_ws_client(coin_list, callback_func):
    # initialise the client
    client = await AsyncClient.create()

    # run some simple requests
    # print(json.dumps(await client.get_exchange_info(), indent=2))

    while True:
        usd_price = get_usd_price()

        for coin_name in coin_list:
            res = await client.get_symbol_ticker(
                # symbol=['BTCUSDT', 'ETHUSDT']
                symbol=coin_name+'USDT'
            )
            res['symbol'] = res['symbol'].replace('USDT', '/USDT')
            res['price'] = float(res['price']) * usd_price
            print(res)

            # time.sleep(0.25)

    # await client.close_connection()


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


def binance_callback_func():
    pass


def get_usd_price():
    if os.name == 'nt':
        import requests
        url = 'https://quotation-api-cdn.dunamu.com/v1/forex/recent?codes=FRX.KRWUSD'
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
        exchange =requests.get(url, headers=headers).json()
        return exchange[0]['basePrice']
    else:
        import pycurl
        from io import BytesIO
        import certifi

        buffer = BytesIO()
        c = pycurl.Curl()

        url = 'https://quotation-api-cdn.dunamu.com/v1/forex/recent?codes=FRX.KRWUSD'
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}

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


if __name__ == "__main__":
    upbit_coin_list = get_upbit_coin_list()
    binance_coin_list = get_binance_coin_list()

    overlapped_coin_list = list(set(upbit_coin_list)&set(binance_coin_list)) 

    tasks = [
        asyncio.ensure_future(
            binance_ws_client(overlapped_coin_list, binance_callback_func)
        ),
    ]
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(asyncio.wait(tasks))
