import httpx, asyncio
from datetime import datetime, timedelta

async def check():
    # 嘗試往前找最近一個有數據的交易日
    async with httpx.AsyncClient() as c:
        for days_back in range(0, 7):
            date = (datetime(2026, 4, 26) - timedelta(days=days_back)).strftime("%Y%m%d")
            url = f"https://www.twse.com.tw/fund/T86?response=open_data&date={date}"
            r = await c.get(url, timeout=30)
            import csv, io
            rows = list(csv.reader(io.StringIO(r.text)))
            data_rows = [row for row in rows[1:] if len(row) > 10 and row[0].strip()]
            print(f"Date {date}: {len(data_rows)} stocks, has 2330: {any(r[0].strip()=='2330' for r in data_rows)}")
            if len(data_rows) > 100:
                # 找到有效數據
                for row in data_rows:
                    if row[0].strip() in ['2330','3037','2454']:
                        print(f"  {row[0].strip()} {row[1].strip()} 投信={row[10].strip()}")
                break

asyncio.run(check())
