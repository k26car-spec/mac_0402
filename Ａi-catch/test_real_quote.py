import asyncio
import sys
import os

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
    
    print("Fetching quote for 2337...")
    q = await fubon_client.get_quote('2337')
    print(f"Quote Result: {q}")
    
    print("\nFetching name for 2337...")
    name = await fubon_client.get_stock_name('2337')
    print(f"Name Result: {name}")

if __name__ == "__main__":
    asyncio.run(test())
