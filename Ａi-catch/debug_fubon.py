import asyncio
import logging
import sys
import os

# 將路徑加入 sys.path
sys.path.append(os.getcwd())

from fubon_client import fubon_client

async def main():
    logging.basicConfig(level=logging.INFO)
    print("Connecting to Fubon API...")
    success = await fubon_client.connect()
    if success:
        print("✅ Success!")
        quote = await fubon_client.get_quote("2330")
        print(f"Quote for 2330: {quote}")
    else:
        print("❌ Failed.")

if __name__ == "__main__":
    asyncio.run(main())
