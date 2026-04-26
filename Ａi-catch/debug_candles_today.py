import asyncio
import sys
import os
from datetime import datetime

# Add root to sys.path
sys.path.insert(0, '/Users/Mac/Documents/ETF/AI/Ａi-catch')

from fubon_client import fubon_client

async def test():
    await fubon_client.connect()
    
    symbol = "2337"
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"Testing candles for {symbol} on {today}...")
    
    try:
        # Try historical client
        res_hist = await asyncio.to_thread(
            fubon_client.sdk.marketdata.rest_client.stock.historical.candles,
            symbol=symbol,
            **{"from": today, "to": today},
            timeframe="5"
        )
        print(f"Historical SDK response: {res_hist}")
        
        # Try intraday client
        res_intra = await asyncio.to_thread(
            fubon_client.sdk.marketdata.rest_client.stock.intraday.candles,
            symbol=symbol
        )
        print(f"Intraday SDK response size: {len(res_intra.get('data', [])) if isinstance(res_intra, dict) else 'N/A'}")
        if res_intra and isinstance(res_intra, dict) and res_intra.get('data'):
             print(f"Last intraday candle: {res_intra['data'][-1]}")
             
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
