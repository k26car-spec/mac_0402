import asyncio
import sys
import os

# Add root to sys.path
sys.path.insert(0, '/Users/Mac/Documents/ETF/AI/Ａi-catch')

from fubon_client import fubon_client

async def test():
    await fubon_client.connect()
    
    # Try common index symbols
    symbols = ["TSE001", "OTC001"]
    
    for symbol in symbols:
        print(f"Testing {symbol}...")
        try:
            quote = await fubon_client.get_quote(symbol)
            if quote:
                print(f"Quote for {symbol}: {quote}")
            else:
                print(f"No quote for {symbol}")
        except Exception as e:
            print(f"Error for {symbol}: {e}")

if __name__ == "__main__":
    asyncio.run(test())
