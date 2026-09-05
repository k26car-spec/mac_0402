import httpx, asyncio

async def check():
    url = "https://www.twse.com.tw/fund/T86?response=open_data"
    async with httpx.AsyncClient() as c:
        r = await c.get(url, timeout=30)
        lines = r.text.split("\n")
        print(f"Header: {lines[0]}")
        # 找台積電
        for line in lines[1:]:
            if "2330" in line:
                parts = line.replace('"','').split(",")
                print(f"2330 Row: {line[:120]}")
                for i, p in enumerate(parts):
                    print(f"  [{i}] = {p}")
                break

asyncio.run(check())
