import asyncio
import httpx
from xml.etree import ElementTree
import urllib.parse

async def test_httpx():
    query = "2330 台積電 目標價 OR 評估"
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(url)
        root = ElementTree.fromstring(resp.text)
        for item in root.findall('.//item')[:3]:
            print(item.find('title').text)

asyncio.run(test_httpx())
