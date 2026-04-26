import requests
import json

def test_api():
    url = "http://localhost:8000/api/stock-analysis/technical/5m/3231"
    print(f"Calling {url}...")
    try:
        response = requests.get(url)
        print(f"Status: {response.status_code}")
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api()
