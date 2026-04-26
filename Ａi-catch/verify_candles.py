import asyncio
import sys
import os
from datetime import datetime

# Add root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from fubon_client import fubon_client

async def test():
    print("Connecting...")
    await fubon_client.connect()
    print("Fetching 5m candles for 2337...")
    candles = await fubon_client.get_candles('2337', timeframe='5')
    if candles:
        print(f"Total candles: {len(candles)}")
        print(f"Last candle: {candles[-1]}")
    else:
        print("No candles returned")

if __name__ == "__main__":
    asyncio.run(test())
