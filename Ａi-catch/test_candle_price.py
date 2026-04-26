import asyncio
import sys
import os
from datetime import datetime

# Add root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from fubon_client import fubon_client

async def test():
    print("Connecting to Fubon...")
    success = await fubon_client.connect()
    if not success:
        print("Failed to connect")
        return
    
    print("Fetching intraday candles for 2337...")
    today = datetime.now().strftime('%Y-%m-%d')
    c = await fubon_client.get_candles('2337', from_date=today, to_date=today, timeframe='1')
    if c:
        print(f"Last Candle: {c[-1]}")
    else:
        print("No candles for today. Trying historical...")
        c = await fubon_client.get_candles('2337', timeframe='D')
        if c:
            print(f"Last Daily Candle: {c[-1]}")

if __name__ == "__main__":
    asyncio.run(test())
