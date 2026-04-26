"""
OpenAI GPT 服務
用於 AI 智慧選股的真實 AI 分析

功能:
1. 新聞情緒分析
2. 股票投資建議生成
3. 風險評估
4. 市場趨勢解讀
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# OpenAI API 設定
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")  # 較便宜且快速

# 嘗試導入 OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("⚠️ openai 套件未安裝，請執行: pip install openai")


class GPTAnalyzer:
    """GPT 股票分析器"""
    
    def __init__(self):
        self.client = None
        self.initialized = False
        
        if OPENAI_AVAILABLE and OPENAI_API_KEY:
            try:
                self.client = OpenAI(api_key=OPENAI_API_KEY)
                self.initialized = True
                logger.info("✅ OpenAI GPT 服務已初始化")
            except Exception as e:
                logger.error(f"❌ OpenAI 初始化失敗: {e}")
        else:
            if not OPENAI_AVAILABLE:
                logger.warning("⚠️ OpenAI 套件未安裝")
            if not OPENAI_API_KEY:
                logger.warning("⚠️ OPENAI_API_KEY 環境變數未設定")
    
    async def analyze_news_sentiment(self, news_list: List[Dict]) -> Dict:
        """
        分析新聞情緒
        
        Args:
            news_list: 新聞列表，每則包含 title, source
        
        Returns:
            情緒分析結果
        """
        if not self.initialized:
            return self._fallback_sentiment_analysis(news_list)
        
        try:
            # 準備新聞摘要
            news_text = "\n".join([
                f"- {n.get('title', '')}" for n in news_list[:15]
            ])
            
            prompt = f"""你是專業的台股市場分析師。請分析以下今日股市新聞，給出：

1. **整體市場情緒** (極度樂觀/樂觀/中性/悲觀/極度悲觀)
2. **信心指數** (0-100，100 表示極度樂觀)
3. **主要題材** (列出 3-5 個熱門投資主題)
4. **風險提示** (1-2 個需要注意的風險)
5. **建議操作策略** (50字以內)

今日新聞:
{news_text}

請用 JSON 格式回覆:
{{
    "sentiment": "樂觀/中性/悲觀",
    "confidence": 65,
    "themes": ["AI 科技", "半導體"],
    "risks": ["美股回檔風險"],
    "strategy": "建議策略..."
}}"""

            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "你是專業的台股分析師，擅長解讀市場新聞和趨勢。請用繁體中文回覆。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content
            
            # 嘗試解析 JSON
            try:
                # 移除可能的 markdown 標記
                result_text = result_text.replace("```json", "").replace("```", "").strip()
                result = json.loads(result_text)
                result["source"] = "GPT-4"
                result["analyzed_at"] = datetime.now().isoformat()
                return result
            except json.JSONDecodeError:
                return {
                    "sentiment": "中性",
                    "confidence": 50,
                    "themes": [],
                    "risks": [],
                    "strategy": result_text[:100],
                    "source": "GPT-4 (解析失敗)",
                    "raw_response": result_text
                }
                
        except Exception as e:
            logger.error(f"GPT 新聞分析失敗: {e}")
            return self._fallback_sentiment_analysis(news_list)
    
    async def analyze_stock(self, stock_data: Dict, news_context: str = "") -> Dict:
        """
        AI 分析單一股票
        
        Args:
            stock_data: 股票技術數據
            news_context: 相關新聞摘要
        
        Returns:
            AI 分析結果
        """
        if not self.initialized:
            return self._fallback_stock_analysis(stock_data)
        
        try:
            stock_code = stock_data.get("code", "")
            stock_name = stock_data.get("name", stock_code)
            price = stock_data.get("price", 0)
            volume = stock_data.get("volume", 0)
            trend = stock_data.get("trend", "盤整")
            ma5 = stock_data.get("ma5", 0)
            ma20 = stock_data.get("ma20", 0)
            atr_pct = stock_data.get("atr_pct", 0)
            patterns = stock_data.get("patterns", [])
            
            prompt = f"""你是專業的台股分析師。請分析以下股票並給出投資建議：

**股票資訊**
- 代碼/名稱: {stock_code} {stock_name}
- 現價: ${price}
- 成交量: {volume} 張/日
- 趨勢: {trend}
- MA5: ${ma5}, MA20: ${ma20}
- 波動率 (ATR%): {atr_pct}%
- K線形態: {', '.join(patterns) if patterns else '無明顯形態'}

{f'**相關新聞**: {news_context}' if news_context else ''}

請提供：
1. **AI 評分** (0-100)
2. **投資建議** (強力買進/買進/觀望/減碼/賣出)
3. **分析理由** (50字以內，重點說明)
4. **風險等級** (低/中/高)
5. **建議持有週期** (短期/中期/長期)

請用 JSON 格式回覆:
{{
    "ai_score": 75,
    "recommendation": "買進",
    "analysis": "理由說明...",
    "risk_level": "中",
    "holding_period": "短期"
}}"""

            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "你是專業的台股技術分析師，擅長結合技術面和基本面給出投資建議。請用繁體中文回覆。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            result_text = response.choices[0].message.content
            
            try:
                result_text = result_text.replace("```json", "").replace("```", "").strip()
                result = json.loads(result_text)
                result["source"] = "GPT-4"
                return result
            except json.JSONDecodeError:
                return {
                    "ai_score": 50,
                    "recommendation": "觀望",
                    "analysis": result_text[:100],
                    "risk_level": "中",
                    "holding_period": "短期",
                    "source": "GPT-4 (解析失敗)"
                }
                
        except Exception as e:
            logger.error(f"GPT 股票分析失敗: {e}")
            return self._fallback_stock_analysis(stock_data)
    
    async def generate_market_summary(self, 
                                       news_sentiment: Dict,
                                       top_stocks: List[Dict],
                                       institutional_data: Dict = None) -> str:
        """
        生成 AI 市場摘要
        
        Args:
            news_sentiment: 新聞情緒分析結果
            top_stocks: 推薦股票列表
            institutional_data: 法人買賣超資料
        
        Returns:
            AI 生成的市場摘要
        """
        if not self.initialized:
            return self._fallback_market_summary(news_sentiment, top_stocks)
        
        try:
            themes = news_sentiment.get("themes", [])
            sentiment = news_sentiment.get("sentiment", "中性")
            
            stocks_text = ", ".join([
                f"{s.get('stock_code')} {s.get('stock_name')}" 
                for s in top_stocks[:5]
            ])
            
            inst_text = ""
            if institutional_data and institutional_data.get("data"):
                for item in institutional_data["data"][:3]:
                    inst_text += f"- {item.get('name', '')}: {item.get('diff', '')}\n"
            
            prompt = f"""根據以下資訊，用專業但易懂的語言寫一段今日市場摘要 (100字以內)：

市場情緒: {sentiment}
熱門題材: {', '.join(themes)}
推薦關注: {stocks_text}
{f'法人動向:\n{inst_text}' if inst_text else ''}

請直接輸出摘要文字，不要加任何標題或格式。"""

            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "你是財經媒體的專業編輯，擅長撰寫簡潔有力的市場摘要。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"GPT 市場摘要生成失敗: {e}")
            return self._fallback_market_summary(news_sentiment, top_stocks)
    
    # ==================== Fallback 方法 ====================
    
    def _fallback_sentiment_analysis(self, news_list: List[Dict]) -> Dict:
        """無 GPT 時的備用情緒分析"""
        # 簡單關鍵字分析
        positive_keywords = ["上漲", "突破", "創高", "買超", "看好", "成長", "利多"]
        negative_keywords = ["下跌", "跌破", "賣超", "利空", "風險", "衰退", "警告"]
        
        positive_count = 0
        negative_count = 0
        
        for news in news_list:
            title = news.get("title", "")
            for kw in positive_keywords:
                if kw in title:
                    positive_count += 1
            for kw in negative_keywords:
                if kw in title:
                    negative_count += 1
        
        if positive_count > negative_count * 1.5:
            sentiment = "樂觀"
            confidence = 65
        elif negative_count > positive_count * 1.5:
            sentiment = "悲觀"
            confidence = 35
        else:
            sentiment = "中性"
            confidence = 50
        
        return {
            "sentiment": sentiment,
            "confidence": confidence,
            "themes": ["市場觀察中"],
            "risks": ["市場波動"],
            "strategy": "建議謹慎操作，等待明確訊號",
            "source": "規則分析 (GPT 未啟用)"
        }
    
    def _fallback_stock_analysis(self, stock_data: Dict) -> Dict:
        """無 GPT 時的備用股票分析"""
        trend = stock_data.get("trend", "盤整")
        price = stock_data.get("price", 0)
        ma20 = stock_data.get("ma20", price)
        
        if trend == "多頭" and price > ma20:
            return {
                "ai_score": 70,
                "recommendation": "買進",
                "analysis": "技術面多頭排列，建議逢回布局",
                "risk_level": "中",
                "holding_period": "短期",
                "source": "規則分析 (GPT 未啟用)"
            }
        elif trend == "空頭":
            return {
                "ai_score": 35,
                "recommendation": "觀望",
                "analysis": "技術面偏空，建議等待止跌訊號",
                "risk_level": "高",
                "holding_period": "觀望",
                "source": "規則分析 (GPT 未啟用)"
            }
        else:
            return {
                "ai_score": 50,
                "recommendation": "觀望",
                "analysis": "盤整格局，等待方向明確",
                "risk_level": "中",
                "holding_period": "短期",
                "source": "規則分析 (GPT 未啟用)"
            }
    
    def _fallback_market_summary(self, news_sentiment: Dict, top_stocks: List[Dict]) -> str:
        """無 GPT 時的備用市場摘要"""
        sentiment = news_sentiment.get("sentiment", "中性")
        themes = news_sentiment.get("themes", [])
        
        if sentiment == "樂觀":
            return f"市場氣氛偏多，題材股活躍。建議關注{', '.join(themes[:2]) if themes else '熱門類股'}相關個股，但需注意追高風險。"
        elif sentiment == "悲觀":
            return f"市場氣氛保守，建議降低持倉比例，等待止跌訊號。可關注具防禦性的標的。"
        else:
            return f"市場呈現區間震盪格局，建議選股不選市，聚焦有實質題材支撐的個股。"


# 全域實例
gpt_analyzer = GPTAnalyzer()


# ==================== 便捷函數 ====================

async def analyze_news_with_gpt(news_list: List[Dict]) -> Dict:
    """使用 GPT 分析新聞情緒"""
    return await gpt_analyzer.analyze_news_sentiment(news_list)

async def analyze_stock_with_gpt(stock_data: Dict, news_context: str = "") -> Dict:
    """使用 GPT 分析單一股票"""
    return await gpt_analyzer.analyze_stock(stock_data, news_context)

async def generate_ai_summary(news_sentiment: Dict, top_stocks: List[Dict], institutional_data: Dict = None) -> str:
    """生成 AI 市場摘要"""
    return await gpt_analyzer.generate_market_summary(news_sentiment, top_stocks, institutional_data)

def is_gpt_available() -> bool:
    """檢查 GPT 是否可用"""
    return gpt_analyzer.initialized
