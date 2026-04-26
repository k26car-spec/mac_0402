import urllib.request
import json
url = 'https://tw.stock.yahoo.com/q/h?s=2330'
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    print(urllib.request.urlopen(req).read().decode('utf-8')[:500])
except Exception as e:
    print(e)
