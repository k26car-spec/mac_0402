import asyncio
from app.services.twse_crawler import twse_crawler
import time
from dotenv import load_dotenv

load_dotenv()

async def main():
    print("Fetching...")
    start = time.time()
    res = await twse_crawler.get_stock_institutional("2337", days=65)
    print("Done in", time.time() - start, "seconds.")
    print("Records found:", len(res))

if __name__ == "__main__":
    asyncio.run(main())
