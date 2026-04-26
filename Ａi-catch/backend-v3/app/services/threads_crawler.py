"""
Threads/Instagram 社群爬蟲
透過 instagrapi 獲取 Instagram/Threads 上的股票討論

注意事項:
1. 需要安裝: pip install instagrapi
2. 需要 Instagram 帳號登入
3. 建議使用專用帳號，避免主帳號被限制
4. Instagram 可能會限制頻繁請求，建議每日執行一次

使用方式:
1. 設定環境變數:
   export IG_USERNAME="your_username"
   export IG_PASSWORD="your_password"

2. 或在 .env 文件中設定
"""

import os
import re
import logging
from typing import List, Dict, Optional
from datetime import datetime
from collections import Counter

logger = logging.getLogger(__name__)

# 股票代碼對照表
STOCK_KEYWORDS = {
    "台積電": "2330", "鴻海": "2317", "聯發科": "2454",
    "長榮": "2603", "陽明": "2609", "萬海": "2615",
    "長榮航": "2618", "華航": "2610",
    "廣達": "2382", "技嘉": "2376", "微星": "2377",
    "創意": "3443", "緯穎": "6669", "世芯": "3661",
    "聯詠": "3034", "瑞昱": "2379", "祥碩": "5269",
    "富邦金": "2881", "國泰金": "2882", "中信金": "2891",
    "玉山金": "2884", "兆豐金": "2886", "台新金": "2887",
    "台塑": "1301", "南亞": "1303", "統一": "1216",
}


class ThreadsCrawler:
    """Threads/Instagram 爬蟲"""
    
    def __init__(self):
        self.client = None
        self.logged_in = False
        self._init_client()
    
    def _init_client(self):
        """初始化 Instagram 客戶端"""
        try:
            from instagrapi import Client
            self.client = Client()
            logger.info("instagrapi 客戶端初始化成功")
        except ImportError:
            logger.warning("instagrapi 未安裝，Threads 爬蟲不可用")
            logger.info("請執行: pip install instagrapi")
            self.client = None
    
    def login(self, username: str = None, password: str = None) -> bool:
        """
        登入 Instagram
        
        Args:
            username: Instagram 用戶名 (或從環境變數讀取)
            password: Instagram 密碼 (或從環境變數讀取)
        """
        if not self.client:
            logger.error("instagrapi 未安裝")
            return False
        
        # 優先使用參數，其次環境變數
        username = username or os.getenv('IG_USERNAME')
        password = password or os.getenv('IG_PASSWORD')
        
        if not username or not password:
            logger.debug("Instagram 帳號未設定 (可選功能，不影響主要功能)")
            return False
        
        try:
            self.client.login(username, password)
            self.logged_in = True
            logger.info(f"✅ Instagram 登入成功: {username}")
            return True
        except Exception as e:
            logger.error(f"❌ Instagram 登入失敗: {e}")
            return False
    
    def crawl_stock_hashtags(self, hashtags: List[str] = None, amount: int = 20) -> List[Dict]:
        """
        爬取股票相關 Hashtag 的貼文
        
        Args:
            hashtags: 要搜尋的標籤列表
            amount: 每個標籤抓取的貼文數量
        """
        if not self.logged_in:
            if not self.login():
                return []
        
        if hashtags is None:
            hashtags = ["台股", "股票", "當沖", "短線", "航運股", "半導體", "AI概念股"]
        
        all_posts = []
        
        for tag in hashtags:
            try:
                logger.info(f"正在搜尋標籤: #{tag}")
                medias = self.client.hashtag_medias_recent(tag, amount=amount)
                
                for media in medias:
                    caption = media.caption_text if media.caption_text else ""
                    
                    # 提取貼文資訊
                    post = {
                        "source": "Instagram",
                        "hashtag": tag,
                        "title": caption[:100] + "..." if len(caption) > 100 else caption,
                        "full_text": caption,
                        "url": f"https://www.instagram.com/p/{media.code}/",
                        "likes": media.like_count,
                        "comments": media.comment_count,
                        "time": media.taken_at.strftime("%Y-%m-%d %H:%M") if media.taken_at else "",
                        "user": media.user.username if media.user else "",
                    }
                    
                    # 檢查是否來自 Threads (Threads 貼文通常會有特殊標記)
                    if hasattr(media, 'is_threads') and media.is_threads:
                        post["source"] = "Threads"
                    
                    all_posts.append(post)
                
                logger.info(f"#{tag} 取得 {len(medias)} 篇貼文")
                
            except Exception as e:
                logger.error(f"搜尋 #{tag} 失敗: {e}")
                continue
        
        logger.info(f"共爬取 {len(all_posts)} 篇社群貼文")
        return all_posts
    
    def extract_stock_mentions(self, posts: List[Dict]) -> Dict[str, int]:
        """
        從貼文中提取股票提及次數
        """
        mentions = Counter()
        
        for post in posts:
            text = post.get("full_text", "") + " " + post.get("title", "")
            
            # 方法1: 匹配股票名稱
            for name, code in STOCK_KEYWORDS.items():
                if name in text:
                    mentions[code] += 1
            
            # 方法2: 匹配 4 位數代碼
            codes = re.findall(r'(?<![0-9])([1-9][0-9]{3})(?![0-9])', text)
            for code in codes:
                # 驗證是否可能是股票代碼 (1xxx-9xxx)
                if code[0] in "123456789":
                    mentions[code] += 1
        
        return dict(mentions.most_common(30))
    
    def get_trending_stocks(self, amount: int = 20) -> List[Dict]:
        """
        獲取社群熱門股票
        
        Returns:
            熱門股票列表，按提及次數排序
        """
        # 爬取貼文
        posts = self.crawl_stock_hashtags(amount=amount)
        
        if not posts:
            logger.warning("未獲取到社群貼文")
            return []
        
        # 提取股票
        stock_counts = self.extract_stock_mentions(posts)
        
        # 整理結果
        trending = []
        for code, count in stock_counts.items():
            # 找出提及此股票的貼文
            sample_posts = [
                p["title"][:50] for p in posts 
                if code in p.get("full_text", "") or code in p.get("title", "")
            ][:3]
            
            trending.append({
                "code": code,
                "name": self._get_stock_name(code),
                "mentions": count,
                "source": "Instagram/Threads",
                "sample_posts": sample_posts
            })
        
        return trending
    
    def _get_stock_name(self, code: str) -> str:
        """根據代碼獲取股票名稱"""
        # 反向查找
        for name, c in STOCK_KEYWORDS.items():
            if c == code:
                return name
        return code
    
    def generate_social_report(self) -> Dict:
        """
        生成社群分析報告
        """
        if not self.logged_in:
            if not self.login():
                return {
                    "status": "error",
                    "message": "Instagram 未登入",
                    "timestamp": datetime.now().isoformat()
                }
        
        try:
            posts = self.crawl_stock_hashtags()
            stock_counts = self.extract_stock_mentions(posts)
            
            # 情緒分析 (簡單版)
            positive_keywords = ["看多", "買", "衝", "噴", "爆", "漲", "賺"]
            negative_keywords = ["看空", "賣", "跌", "崩", "虧", "空"]
            
            positive_count = 0
            negative_count = 0
            
            for post in posts:
                text = post.get("full_text", "")
                if any(kw in text for kw in positive_keywords):
                    positive_count += 1
                if any(kw in text for kw in negative_keywords):
                    negative_count += 1
            
            mood = "偏多" if positive_count > negative_count else "偏空" if negative_count > positive_count else "中性"
            
            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "source": "Instagram/Threads",
                "total_posts": len(posts),
                "sentiment": {
                    "positive": positive_count,
                    "negative": negative_count,
                    "mood": mood
                },
                "trending_stocks": [
                    {"code": code, "mentions": count}
                    for code, count in list(stock_counts.items())[:15]
                ],
                "top_posts": posts[:10] if posts else []
            }
            
        except Exception as e:
            logger.error(f"社群報告生成失敗: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def close(self):
        """登出並清理"""
        if self.client and self.logged_in:
            try:
                self.client.logout()
                logger.info("Instagram 已登出")
            except:
                pass
        self.logged_in = False


# ==================== 便捷函數 ====================

# 全域實例 (延遲初始化)
_threads_crawler = None

def get_threads_crawler() -> ThreadsCrawler:
    """獲取 Threads 爬蟲實例"""
    global _threads_crawler
    if _threads_crawler is None:
        _threads_crawler = ThreadsCrawler()
    return _threads_crawler

async def get_threads_trending_stocks() -> List[Dict]:
    """獲取 Threads/Instagram 熱門股票"""
    crawler = get_threads_crawler()
    return crawler.get_trending_stocks()


# ==================== 測試 ====================

if __name__ == "__main__":
    import asyncio
    
    print("=" * 50)
    print("Threads/Instagram 爬蟲測試")
    print("=" * 50)
    
    # 檢查 instagrapi
    try:
        from instagrapi import Client
        print("✅ instagrapi 已安裝")
    except ImportError:
        print("❌ instagrapi 未安裝")
        print("請執行: pip install instagrapi")
        exit(1)
    
    # 檢查環境變數
    username = os.getenv('IG_USERNAME')
    password = os.getenv('IG_PASSWORD')
    
    if not username or not password:
        print("\n⚠️ 未設定 Instagram 帳號")
        print("請設定環境變數:")
        print("  export IG_USERNAME='your_username'")
        print("  export IG_PASSWORD='your_password'")
        exit(1)
    
    print(f"\n使用帳號: {username}")
    
    # 測試
    crawler = ThreadsCrawler()
    if crawler.login(username, password):
        print("\n正在爬取社群貼文...")
        report = crawler.generate_social_report()
        
        print(f"\n📊 社群分析結果:")
        print(f"  總貼文數: {report.get('total_posts', 0)}")
        print(f"  市場情緒: {report.get('sentiment', {}).get('mood', '-')}")
        print(f"\n🔥 熱門股票:")
        for stock in report.get('trending_stocks', [])[:10]:
            print(f"    {stock['code']}: {stock['mentions']} 次提及")
        
        crawler.close()
    else:
        print("❌ 登入失敗")
