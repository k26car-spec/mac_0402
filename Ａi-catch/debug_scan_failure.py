
import asyncio
import logging
import sys
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root
sys.path.insert(0, "/Users/Mac/Documents/ETF/AI/Ａi-catch")

from fubon_client import fubon_client

SCAN_LIST_FAST = [
    '2330','2317','2454','2382'
]

async def test_batch():
    print("Testing batch connection...")
    if not fubon_client.is_connected:
        print("Connecting...")
        await fubon_client.connect()
    
    print(f"Fetching {len(SCAN_LIST_FAST)} stocks...")
    results = await fubon_client.batch_get_quotes(SCAN_LIST_FAST)
    
    success_count = 0
    for code, data in results.items():
        if data:
            print(f"✅ {code}: {data.get('price')} (Source: {data.get('dataSource')})")
            success_count += 1
        else:
            print(f"❌ {code}: Failed")
            
    print(f"\nSuccess: {success_count}/{len(SCAN_LIST_FAST)}")

if __name__ == "__main__":
    asyncio.run(test_batch())
