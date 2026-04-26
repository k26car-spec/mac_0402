
import asyncio
import httpx

async def test_mis():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            mis_url = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_t00.tw"
            res = await client.get(mis_url)
            print(f"Status: {res.status_code}")
            print(f"Response: {res.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_mis())
