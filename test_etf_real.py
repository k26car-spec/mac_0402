import httpx

async def check():
    for s in ["00981A.TW", "00981A.TWO", "00981A"]:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{s}?interval=1d&range=1d"
        try:
            r = await client.get(url, headers={'User-Agent': 'Mozilla'})
            print(f"Testing {s}: {r.status_code}")
            if r.status_code == 200:
                print(r.text[:200])
        except: pass

async def main():
    async with httpx.AsyncClient() as c:
        global client
        client = c
        await check()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
