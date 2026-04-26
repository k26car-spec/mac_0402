import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add root to sys.path
sys.path.insert(0, '/Users/Mac/Documents/ETF/AI/Ａi-catch')

from fubon_client import fubon_client

async def test():
    symbol = "3231"
    print(f"Fetching candles for {symbol}...")
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # We want to see what Fubon returns even if it's stale
    if not fubon_client.is_connected:
        await fubon_client.connect()
        
    if fubon_client.is_connected:
        # Manually call the Fubon SDK to see what's in there
        try:
            res = await asyncio.to_thread(
                fubon_client.sdk.marketdata.rest_client.stock.historical.candles,
                symbol=symbol,
                **{"from": "2026-01-01", "to": today},
                timeframe="5"
            )
            if res and hasattr(res, 'data'):
                data = res.data
                print(f"Total candles: {len(data)}")
                if len(data) > 0:
                    print("Last 5 candles:")
                    for c in data[-5:]:
                        print(c)
            else:
                print("No data in response")
        except Exception as e:
            print(f"Fubon SDK error: {e}")
    else:
        print("Fubon not connected")

if __name__ == "__main__":
    asyncio.run(test())
