import asyncio
import sys
import os

# Add root to sys.path
sys.path.insert(0, '/Users/Mac/Documents/ETF/AI/Ａi-catch')

from fubon_client import fubon_client

async def test():
    await fubon_client.connect()
    
    if fubon_client.is_connected:
        try:
            intraday = fubon_client.sdk.marketdata.rest_client.stock.intraday
            print(f"Intraday methods: {dir(intraday)}")
            
            # Check for candles
            if hasattr(intraday, 'candles'):
                 print("Intraday has candles!")
                 res = await asyncio.to_thread(intraday.candles, symbol="2330")
                 print(f"Intraday candles: {res}")
            else:
                 print("Intraday does NOT have candles attribute")
                 
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
