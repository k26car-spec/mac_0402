import urllib.request
import urllib.parse
from xml.etree import ElementTree
import ssl

def get_google_news(query):
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    print(f"Fetching from: {url}")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        xml_data = urllib.request.urlopen(req, context=ctx).read()
        root = ElementTree.fromstring(xml_data)
        items = root.findall('.//item')
        for item in items[:5]:
            title = item.find('title').text
            pubDate = item.find('pubDate').text
            print(f"- {title} ({pubDate})")
    except Exception as e:
        print(f"Error: {e}")

get_google_news("2330 台積電 目標價 OR 評估 OR 法人")
