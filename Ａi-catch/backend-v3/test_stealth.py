#!/usr/bin/env python3
"""
使用 playwright-stealth 測試 Wantgoo Gossips API v3
"""

import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import json
import random

async def test_wantgoo_stealth():
    print("🚀 使用 playwright-stealth 測試 Wantgoo API (v3)...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='zh-TW',
            timezone_id='Asia/Taipei',
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        stealth = Stealth()
        await stealth.apply_stealth_async(page)
        
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)
        
        try:
            print("📄 正在載入 Wantgoo 頁面...")
            # 使用 domcontentloaded 代替 networkidle
            await page.goto('https://www.wantgoo.com/stock/5498', wait_until='domcontentloaded', timeout=30000)
            
            # 等待 JavaScript 完成
            print("⏳ 等待頁面 JavaScript 執行...")
            await page.wait_for_timeout(8000)
            
            # 模擬人類行為
            await page.mouse.move(random.randint(100, 500), random.randint(100, 300))
            await page.evaluate("window.scrollBy(0, 500)")
            await page.wait_for_timeout(2000)
            
            title = await page.title()
            url = page.url
            print(f"✅ 頁面載入成功: {title}")
            print(f"   URL: {url}")
            
            # 列出頁面上的所有 Cookie
            cookies = await context.cookies()
            print(f"\n🍪 當前 Cookie 數量: {len(cookies)}")
            
            # 嘗試從 DOM 直接提取新聞
            print("\n📄 從 DOM 提取新聞...")
            news_from_dom = await page.evaluate('''
                () => {
                    // 嘗試 gossips 區塊
                    const gossips = document.querySelector('ul#gossips');
                    if (gossips) {
                        const items = gossips.querySelectorAll('a.block-link');
                        if (items.length > 0) {
                            return {
                                source: 'gossips',
                                data: Array.from(items).slice(0, 5).map(a => ({
                                    title: a.querySelector('h4')?.innerText?.trim() || '',
                                    date: a.querySelector('time')?.innerText?.trim() || '',
                                    category: a.querySelector('.title-category')?.innerText?.trim() || '',
                                    url: a.href
                                }))
                            };
                        }
                    }
                    
                    // 備用：嘗試其他 block-link
                    const allLinks = document.querySelectorAll('a.block-link');
                    if (allLinks.length > 0) {
                        return {
                            source: 'all-links',
                            data: Array.from(allLinks).slice(0, 5).map(a => ({
                                title: (a.querySelector('h4') || a.querySelector('h3'))?.innerText?.trim() || '',
                                date: a.querySelector('time')?.innerText?.trim() || '',
                                url: a.href
                            }))
                        };
                    }
                    
                    // 返回頁面上的所有標題
                    const h4s = document.querySelectorAll('h4');
                    return {
                        source: 'h4-titles',
                        data: Array.from(h4s).slice(0, 10).map(h => h.innerText?.trim())
                    };
                }
            ''')
            
            print(f"\n📊 DOM 新聞結果:")
            print(json.dumps(news_from_dom, ensure_ascii=False, indent=2))
            
            if news_from_dom.get('data') and len(news_from_dom.get('data', [])) > 0:
                print(f"\n🎉 成功從 DOM 提取 {len(news_from_dom['data'])} 則新聞！")
            else:
                print("⚠️ 無法從 DOM 提取新聞")
                
                # 截圖調試
                await page.screenshot(path='/tmp/wantgoo_debug.png')
                print("已截圖保存至 /tmp/wantgoo_debug.png")
            
        except Exception as e:
            print(f"❌ 錯誤: {e}")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_wantgoo_stealth())
