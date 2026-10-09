import httpx
import json

async def check():
    symbols = ["2330.TW", "0050.TW", "2317.TW"]
    async with httpx.AsyncClient() as client:
        for s in symbols:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{s}?interval=1d&range=5d"
            r = await client.get(url, headers={'User-Agent': 'Mozilla'})
            data = r.json()
            price = data['chart']['result'][0]['indicators']['quote'][0]['close'][-1]
            print(f"{s}: {price}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(check())
