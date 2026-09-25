import httpx, asyncio

async def check():
    url = "https://www.twse.com.tw/fund/T86?response=open_data"
    async with httpx.AsyncClient() as c:
        r = await c.get(url, timeout=30)
        lines = r.text.split("\n")
        print(f"Total lines: {len(lines)}")
        print(f"First 3 data rows:")
        for line in lines[1:4]:
            print(f"  {line[:100]}")
        # 顯示所有找到的代號
        found = []
        for line in lines[1:]:
            parts = line.replace('"','').split(",")
            if len(parts) > 10:
                found.append(parts[0].strip())
        print(f"Total tickers: {len(found)}")
        print(f"Sample tickers: {found[:5]}")
        print(f"2330 in list: {'2330' in found}")
        print(f"3037 in list: {'3037' in found}")

asyncio.run(check())
