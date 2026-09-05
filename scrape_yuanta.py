import httpx
import json

async def get_0050_real():
    # 元大 0050 持股明細 API (FundId=1066)
    url = "https://www.yuantaetfs.com/api/StkHold?FundId=1066"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.yuantaetfs.com/product/detail/1066/InvestmentFocus"
    }
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, headers=headers, timeout=15)
            data = r.json()
            # 提取 股票代碼 與 持股張數
            real_shares = { item['stk_code']: float(item['qty'].replace(',', '')) for item in data if 'stk_code' in item }
            print(json.dumps(real_shares))
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(get_0050_real())
