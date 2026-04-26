#!/usr/bin/env python3
"""
測試富邦 API 股票名稱獲取功能
"""
import asyncio
import aiohttp

API_BASE = "http://localhost:8000"

# 測試股票列表
TEST_STOCKS = [
    "2330", "2317", "2454", "2337", "2344", "2303",
    "3034", "2379", "2603", "2609", "3231"
]


async def test_fubon_quote(session, stock_code):
    """測試富邦 quote API"""
    try:
        async with session.get(
            f"{API_BASE}/api/fubon/quote/{stock_code}",
            timeout=aiohttp.ClientTimeout(total=3)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                name = data.get("name") or data.get("stock_name") or "N/A"
                print(f"✅ [Fubon Quote] {stock_code}: {name}")
                return name
            else:
                print(f"❌ [Fubon Quote] {stock_code}: HTTP {resp.status}")
                return None
    except Exception as e:
        print(f"⚠️ [Fubon Quote] {stock_code}: {str(e)}")
        return None


async def test_fubon_stock_name(session, stock_code):
    """測試富邦 stock-name API"""
    try:
        async with session.get(
            f"{API_BASE}/api/fubon/stock-name/{stock_code}",
            timeout=aiohttp.ClientTimeout(total=3)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                name = data.get("name") or data.get("stock_name") or "N/A"
                print(f"✅ [Fubon Name] {stock_code}: {name}")
                return name
            else:
                print(f"❌ [Fubon Name] {stock_code}: HTTP {resp.status}")
                return None
    except Exception as e:
        print(f"⚠️ [Fubon Name] {stock_code}: {str(e)}")
        return None


async def test_analysis_api(session, stock_code):
    """測試 stock-analysis/stock-name API"""
    try:
        async with session.get(
            f"{API_BASE}/api/stock-analysis/stock-name/{stock_code}",
            timeout=aiohttp.ClientTimeout(total=3)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                name = data.get("name", "N/A")
                print(f"✅ [Analysis] {stock_code}: {name}")
                return name
            else:
                print(f"❌ [Analysis] {stock_code}: HTTP {resp.status}")
                return None
    except Exception as e:
        print(f"⚠️ [Analysis] {stock_code}: {str(e)}")
        return None


async def main():
    """主測試函數"""
    print("=" * 60)
    print("🔍 測試富邦 API 股票名稱獲取功能")
    print("=" * 60)
    print()

    async with aiohttp.ClientSession() as session:
        for stock_code in TEST_STOCKS:
            print(f"\n📊 測試股票: {stock_code}")
            print("-" * 40)
            
            # 測試三個不同的 API
            await test_fubon_quote(session, stock_code)
            await asyncio.sleep(0.2)
            
            # 如果有 stock-name 專用端點
            await test_fubon_stock_name(session, stock_code)
            await asyncio.sleep(0.2)
            
            # 備用 API
            await test_analysis_api(session, stock_code)
            await asyncio.sleep(0.5)

    print()
    print("=" * 60)
    print("✅ 測試完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
