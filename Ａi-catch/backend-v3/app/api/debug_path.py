
import os
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
# 模擬 lstm.py 的位置: backend-v3/app/api/debug.py
# 所以跟 lstm.py 一樣層級

ORB_WATCHLIST_FILE = os.path.join(PROJECT_ROOT, "data", "orb_watchlist.json")

print(f"PROJECT_ROOT: {PROJECT_ROOT}")
print(f"ORB_WATCHLIST_FILE: {ORB_WATCHLIST_FILE}")
print(f"Exists? {os.path.exists(ORB_WATCHLIST_FILE)}")

if os.path.exists(ORB_WATCHLIST_FILE):
    with open(ORB_WATCHLIST_FILE, 'r') as f:
        data = json.load(f)
        print(f"Watchlist content: {data.get('watchlist')}")
