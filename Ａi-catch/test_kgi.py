import asyncio
import httpx
from xml.etree import ElementTree
import urllib.parse
import re

async def test_kgi_news():
    stock_code = "2330"
    query = f"{stock_code} (凱基 OR KGI) 目標價"
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(url)
        root = ElementTree.fromstring(resp.text)
        for item in root.findall('.//item')[:5]:
            title = item.find('title').text
            print(f"- {title}")
            # Try to extract target price
            match = re.search(r'(目標價|上看|調升至|維持).*?(\d{2,4})', title)
            if match:
                val = match.group(2)
                print(f"  --> Extracted target: {val}")

asyncio.run(test_kgi_news())
