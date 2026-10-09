import httpx

async def debug():
    url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=open_data"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        lines = r.text.split("\n")
        print(f"Header: {lines[0]}")
        for line in lines[1:5]:
            if "2330" in line:
                print(f"Found 2330: {line}")
                break

if __name__ == "__main__":
    import asyncio
    asyncio.run(debug())
