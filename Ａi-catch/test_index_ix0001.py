import asyncio
import sys
import os

# Add root to sys.path
sys.path.insert(0, '/Users/Mac/Documents/ETF/AI/Ａi-catch')

from fubon_client import fubon_client

async def test():
    await fubon_client.connect()
    
    # Try common index symbols
    symbols = ["IX0001", "TSE001", "^TWII"]
    
    for symbol in symbols:
        print(f"Testing {symbol}...")
        try:
            # Try via SDK directly to avoid yfinance fallback in get_quote
            if hasattr(fubon_client.sdk, 'marketdata'):
                res = await asyncio.to_thread(
                    fubon_client.sdk.marketdata.rest_client.stock.intraday.quote,
                    symbol=symbol
                )
                print(f"Fubon SDK response for {symbol}: {res}")
            else:
                print("MarketData not available")
        except Exception as e:
            print(f"Error for {symbol}: {e}")

if __name__ == "__main__":
    asyncio.run(test())
