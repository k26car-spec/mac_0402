import asyncio
from app.services.stock_comprehensive_analyzer import analyze_stock_comprehensive
import json
async def test():
    try:
        res = await analyze_stock_comprehensive("2330", quick_mode=True)
        print("Success JSON:", json.dumps(res, default=str)[:100])
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(test())
