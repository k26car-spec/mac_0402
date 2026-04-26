import feedparser
import ssl
import re
from datetime import datetime
from typing import Dict, List
import logging
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)

class MacroEconomyService:
    def __init__(self):
        # Ignore SSL errors for feedparser
        if hasattr(ssl, '_create_unverified_context'):
            ssl._create_default_https_context = ssl._create_unverified_context
            
        self.rss_urls = [
            {"name": "Google 國際 (台)", "url": "https://news.google.com/rss/headlines/section/topic/WORLD?hl=zh-TW&gl=TW&ceid=TW:zh-Hant", "foreign": False},
            {"name": "Google 財經 (台)", "url": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=zh-TW&gl=TW&ceid=TW:zh-Hant", "foreign": False},
            {"name": "Google World (US)", "url": "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-US&gl=US&ceid=US:en", "foreign": True},
            {"name": "Reuters World", "url": "https://www.reuters.com/rssFeed/worldNews", "foreign": True},
            {"name": "CNBC Finance", "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=40&keywords=finance", "foreign": True}
        ]
        self.translator = GoogleTranslator(source='en', target='zh-TW')
        self.cached_macro = None
        self.last_fetch_time = None

    async def get_global_macro_status(self) -> Dict:
        """獲取最新的全球政經總匯"""
        # 簡單快取 30 分鐘
        now = datetime.now()
        if self.cached_macro and self.last_fetch_time and (now - self.last_fetch_time).total_seconds() < 1800:
            return self.cached_macro

        try:
            headlines = []
            for rss in self.rss_urls:
                try:
                    feed = feedparser.parse(rss["url"])
                    for entry in feed.entries[:10]:
                        title = entry.title
                        link = entry.link
                        
                        # 如果是外媒且標題是英文，進行翻譯
                        translated_title = title
                        if rss["foreign"] and any(ord(c) < 128 for c in title):
                            try:
                                translated_title = self.translator.translate(title)
                                logger.info(f"Translated: {title} -> {translated_title}")
                            except Exception as te:
                                logger.error(f"Translation failed: {te}")
                        
                        headlines.append({
                            "title": translated_title,
                            "original_title": title if rss["foreign"] else None,
                            "link": link,
                            "source": rss["name"],
                            "is_foreign": rss["foreign"]
                        })
                except Exception as fe:
                    logger.error(f"Failed to parse {rss['url']}: {fe}")
            
            # 判斷趨勢與情緒
            analysis = self._analyze_items(headlines)
            
            self.cached_macro = analysis
            self.last_fetch_time = now
            return analysis
            
        except Exception as e:
            logger.error(f"獲取總經資料失敗: {e}")
            return self._fallback_macro()

    def _analyze_items(self, items: List[Dict]) -> Dict:
        """萃取重點新聞並判斷多空情緒"""
        
        events = []
        macro_score = 0
        headlines_for_sentiment = [item["title"] for item in items]
        geopolitical_keywords_positive = [r"(停火|停戰|撤軍|和解|談判|協議|結束.*戰爭)", r"(伊.*朗|以.*色列|中東|美.*方)"]
        geopolitical_keywords_negative = [r"(空襲|開戰|宣戰|報復|飛彈|制裁|打擊|軍事|抨擊|通牒)", r"(伊.*朗|以.*色列|中東|俄.*羅.*斯|烏.*克.*蘭|川.*普)"]
        macro_positive = [r"(降息|寬鬆|通膨.*降溫|非農.*優於預期)", r"(美.*聯.*儲|Fed|央行)"]
        macro_negative = [r"(升息|緊縮|通膨.*反彈|衰退|失業率.*攀升)", r"(美.*聯.*儲|Fed|美國經濟)"]
        
        found_geo_positive = False
        found_geo_negative = False
        
        for item in items:
            title = item["title"]
            # 1. 檢查正面地緣政治
            if re.search(geopolitical_keywords_positive[0], title) and re.search(geopolitical_keywords_positive[1], title):
                events.append({"category": "地緣政治", "impact": "positive", "title": title, "link": item["link"], "source": item["source"]})
                macro_score += 2
                found_geo_positive = True
            
            # 2. 檢查負面地緣政治 (優先權較高)
            if re.search(geopolitical_keywords_negative[0], title) and re.search(geopolitical_keywords_negative[1], title):
                events.append({"category": "地緣政治", "impact": "negative", "title": title, "link": item["link"], "source": item["source"]})
                macro_score -= 3.0
                found_geo_negative = True
                
            # 3. 檢查總經正面
            if re.search(macro_positive[0], title) and re.search(macro_positive[1], title):
                events.append({"category": "全球總經", "impact": "positive", "title": title, "link": item["link"], "source": item["source"]})
                macro_score += 1.5
                
            # 4. 檢查總經負面
            if re.search(macro_negative[0], title) and re.search(macro_negative[1], title):
                events.append({"category": "全球總經", "impact": "negative", "title": title, "link": item["link"], "source": item["source"]})
                macro_score -= 1.5

        # 為確保如果沒抓取到精準新聞也能給出模擬的市場氣氛
        summary = ""
        action_advice = ""
        
        # 🆕 偵測川普言論並提高警戒層級 (更積極的偵測：只要出現川普與打擊/抨擊/計畫)
        is_trump_warning = any("川普" in t or "Trump" in t or "Epic Fury" in t for t in headlines_for_sentiment) and (found_geo_negative or any("打擊" in t or "抨擊" in t or "通牒" in t for t in headlines_for_sentiment))
        
        if is_trump_warning:
            # 動態從頭條擷取川普相關摘要，不使用硬編碼的過期日期
            trump_headlines = [t for t in headlines_for_sentiment if "川普" in t or "Trump" in t]
            top_trump = trump_headlines[:3]
            bullets = "\n".join(f"• {h}" for h in top_trump) if top_trump else "• 川普相關重大政策消息持續發酵"
            today_str = datetime.now().strftime("%m/%d")
            summary = (
                f"🚨 【{today_str} 川普政策警戒】\n"
                f"{bullets}\n"
                "• 相關聲明對國際供應鏈與金融市場構成系統性風險"
            )
            action_advice = "川普相關政策言論引發市場高度警戒，地緣政治不確定性攀升。操作建議：增加現金水位，嚴控持股風險，等待情勢明朗後再積極進場。"
            sentiment = "高度警戒 🔴"
        elif macro_score >= 2 or found_geo_positive:
            summary = "近期地緣政治緊張情緒顯著降溫（如美伊釋出停戰信號），避險資產壓力解除，全球股市資金回流風險資產。"
            action_advice = "國際環境友善，系統性風險降低，大盤有利多頭延續，可積極尋找有技術面突破或法人佈局的標的進場。"
            sentiment = "樂觀 🟢"
        elif macro_score <= -2 or found_geo_negative:
            summary = "地緣政治衝突升溫（例如中東地緣或戰爭變數），導致避險情緒蔓延，可能對全球供應鏈及股市造成波動。"
            action_advice = "請注意系統性風險的回調，操作宜保守並嚴設停損，減少持股水位或尋求黃金、原油等避險標的。"
            sentiment = "恐慌 🔴"
        else:
            summary = "當前國際政經局勢處於觀望期，無重大地緣衝突與突發經濟震撼彈。"
            action_advice = "大盤回歸基本面與籌碼面運作，建議「選股不選市」，專注於有強力外資/投信加持的強勢個股。"
            sentiment = "中性 🟡"
            
        # 整理最近頭條
        foreign_items = [item for item in items if item["is_foreign"]]
        domestic_items = [item for item in items if not item["is_foreign"]]
        
        top_items = foreign_items[:5] + domestic_items[:5]

        return {
            "sentiment": sentiment,
            "macro_score": macro_score,
            "summary": summary,
            "action_advice": action_advice,
            "top_events": events[:8],
            "recent_headlines": top_items
        }
        
    def _fallback_macro(self) -> Dict:
        return {
            "sentiment": "中性 🟡",
            "macro_score": 0,
            "summary": "當下無法獲取最新國際政經新聞。",
            "action_advice": "請暫時依賴個股本身的籌碼與技術面獨立判斷。",
            "top_events": [],
            "recent_headlines": []
        }

macro_service = MacroEconomyService()
