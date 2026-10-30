import httpx

async def find():
    url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=open_data"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        lines = r.text.split("\n")
        header = lines[0]
        print(f"HEADER: {header}")
        for line in lines:
            if "2330" in line:
                print(f"RAW DATA: {line}")
                # 印出所有索引對應
                parts = line.replace('"', '').split(",")
                for i, p in enumerate(parts):
                    print(f"Index {i}: {p}")
                break

if __name__ == "__main__":
    import asyncio
    asyncio.run(find())
