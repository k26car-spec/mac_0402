import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add root to sys.path
sys.path.insert(0, '/Users/Mac/Documents/ETF/AI/Ａi-catch')

from fubon_client import fubon_client

async def test():
    symbol = "3231"
    print(f"Testing 5m candles for {symbol}...")
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Test Fubon Client
    candles = await fubon_client.get_candles(symbol, today, today, "5")
    print("\n--- Fubon Client 5m Candles ---")
    if candles:
        print(f"Count: {len(candles)}")
        if len(candles) > 0:
            print("First candle:", candles[0])
            print("Last candle:", candles[-1])
    else:
        print("Candles is None")
        
    # Test yfinance directly
    import yfinance as yf
    print("\n--- yfinance 5m Data ---")
    ticker = yf.Ticker(f"{symbol}.TW")
    hist = ticker.history(period="5d", interval="5m")
    print("\nHistory (last 5 rows):")
    print(hist.tail())
    
if __name__ == "__main__":
    asyncio.run(test())
