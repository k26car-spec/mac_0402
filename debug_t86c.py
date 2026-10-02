import httpx, asyncio

async def check():
    # 指定抓取 2026/04/24 (上週五) 的法人資料
    url = "https://www.twse.com.tw/fund/T86?response=open_data&date=20260424"
    async with httpx.AsyncClient() as c:
        r = await c.get(url, timeout=30)
        lines = r.text.split("\n")
        print(f"Total lines: {len(lines)}")
        found = {}
        for line in lines[1:]:
            parts = line.replace('"','').replace(',','').split(",") if ',' not in line.replace('"','') else line.replace('"','').split(",")
            # 數值欄位含逗號, 需特殊處理
        # 改用 csv
        import csv, io
        reader = csv.reader(io.StringIO(r.text))
        rows = list(reader)
        print(f"Header: {rows[0][:5]}")
        for row in rows[1:]:
            if len(row) > 10 and row[0].strip() in ['2330','3037','2454','2317']:
                print(f"  {row[0].strip()} {row[1].strip()} 投信買賣超={row[10].strip()}")

asyncio.run(check())
