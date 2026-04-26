from playwright.sync_api import sync_playwright
import json

def fetch_twse(date_str, stock_code):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        # TWSE T86 JSON API
        url = f"https://www.twse.com.tw/fund/T86?response=json&date={date_str}&selectType=ALLBUT0999"
        try:
            response = page.goto(url, wait_until="networkidle", timeout=15000)
            text = page.locator("body").inner_text()
            print("RESPONSE BODY:", text[:200])
        except Exception as e:
            print("Error:", e)
        finally:
            browser.close()

if __name__ == "__main__":
    fetch_twse("20250325", "2337")
