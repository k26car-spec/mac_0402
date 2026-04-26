import asyncio
import sys
import os

# Add root to sys.path
sys.path.insert(0, '/Users/Mac/Documents/ETF/AI/Ａi-catch')

from fubon_client import fubon_client

async def test():
    symbol = "3231"
    print(f"Testing {symbol}...")
    
    # Test Fubon Client
    quote = await fubon_client.get_quote(symbol)
    print("\n--- Fubon Client Quote ---")
    if quote:
        for k, v in quote.items():
            print(f"{k}: {v}")
    else:
        print("Quote is None")
        
    # Test yfinance directly
    import yfinance as yf
    print("\n--- yfinance Data ---")
    ticker = yf.Ticker(f"{symbol}.TW")
    hist = ticker.history(period="5d")
    print("\nHistory:")
    print(hist)
    print("\nInfo:")
    info = ticker.info
    print(f"previousClose: {info.get('previousClose')}")
    print(f"regularMarketPreviousClose: {info.get('regularMarketPreviousClose')}")

if __name__ == "__main__":
    asyncio.run(test())
