import requests
resp = requests.get("https://openapi.twse.com.tw/v1/holidaySchedule/holidaySchedule")
print(resp.json()[:5])
