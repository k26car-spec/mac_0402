import httpx, asyncio

async def check():
    # 查詢台積電個股三大法人資料
    async with httpx.AsyncClient() as c:
        url = "https://www.twse.com.tw/fund/TWT38U?response=open_data&date=20260424&stockNo=2330"
        r = await c.get(url, timeout=15)
        print(f"Status: {r.status_code}")
        print(f"Content: {r.text[:300]}")

asyncio.run(check())
