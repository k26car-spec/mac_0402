import asyncio
import aiohttp
import json
import ssl
import certifi

async def test_twse_raw():
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36',
    }
    date_str = "20260331"
    url = f'https://www.twse.com.tw/rwd/zh/fund/T86?date={date_str}&selectType=ALLBUT0999&response=json'
    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, ssl=ssl_ctx) as resp:
            data = await resp.json()
            if 'data' in data and len(data['data']) > 0:
                row = data['data'][0]
                fields = data['fields']
                for i, (f, v) in enumerate(zip(fields, row)):
                    print(f"{i}: {f} = {v}")
            else:
                print(f"No data for {date_str}: {data}")

asyncio.run(test_twse_raw())
