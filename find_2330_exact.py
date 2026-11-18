import httpx

async def find():
    url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=open_data"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        lines = r.text.split("\n")
        print(f"Total Lines: {len(lines)}")
        for line in lines:
            parts = line.replace('"', '').split(",")
            if len(parts) >= 10 and parts[1].strip() == "2330":
                print(f"FOUND TSMC: {line}")
                for i, p in enumerate(parts):
                    print(f"Index {i}: {p}")
                return
        print("TSMC 2330 NOT FOUND IN CSV")

if __name__ == "__main__":
    import asyncio
    asyncio.run(find())
