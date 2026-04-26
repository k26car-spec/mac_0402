"""
推薦準確率追蹤系統
追蹤 AI 選股推薦的歷史表現，計算準確率

功能:
1. 記錄每日推薦股票
2. 追蹤後續價格變化
3. 計算週/月準確率
4. 生成績效報告
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import yfinance as yf

logger = logging.getLogger(__name__)

# 資料儲存路徑
DATA_DIR = "/Users/Mac/Documents/ETF/AI/Ａi-catch/data/accuracy_tracking"


class AccuracyTracker:
    """準確率追蹤器"""
    
    def __init__(self):
        self.data_dir = DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)
        self.recommendations_file = os.path.join(self.data_dir, "recommendations.json")
        self.results_file = os.path.join(self.data_dir, "results.json")
        self._load_data()
    
    def _load_data(self):
        """載入歷史數據"""
        # 載入推薦記錄
        if os.path.exists(self.recommendations_file):
            with open(self.recommendations_file, 'r', encoding='utf-8') as f:
                self.recommendations = json.load(f)
        else:
            self.recommendations = []
        
        # 載入結果記錄
        if os.path.exists(self.results_file):
            with open(self.results_file, 'r', encoding='utf-8') as f:
                self.results = json.load(f)
        else:
            self.results = []
    
    def _save_data(self):
        """儲存數據"""
        with open(self.recommendations_file, 'w', encoding='utf-8') as f:
            json.dump(self.recommendations, f, ensure_ascii=False, indent=2)
        
        with open(self.results_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
    
    def record_recommendation(self, picks: List[Dict], timeframe: str):
        """
        記錄推薦
        
        Args:
            picks: 推薦股票列表 [{"stock_code": "2603", "stock_name": "長榮", "price": 98.5, ...}]
            timeframe: 週期類型 (short/mid/long)
        """
        today = datetime.now().strftime("%Y-%m-%d")
        
        for pick in picks:
            record = {
                "id": f"{today}_{pick['stock_code']}_{timeframe}",
                "date": today,
                "stock_code": pick["stock_code"],
                "stock_name": pick.get("stock_name", ""),
                "timeframe": timeframe,
                "recommended_price": pick["price"],
                "target_price": pick.get("target_price", pick["price"] * 1.08),
                "stop_loss": pick.get("stop_loss", pick["price"] * 0.95),
                "expert_score": pick.get("expert_score", 0),
                "status": "active",  # active / success / failed / expired
                "result_checked": False,
            }
            
            # 檢查是否已存在
            exists = any(r["id"] == record["id"] for r in self.recommendations)
            if not exists:
                self.recommendations.append(record)
                logger.info(f"記錄推薦: {pick['stock_code']} ({timeframe})")
        
        self._save_data()
    
    def check_results(self):
        """
        檢查推薦結果
        根據時間判斷是否達標
        """
        today = datetime.now()
        
        for rec in self.recommendations:
            if rec["status"] != "active":
                continue
            
            rec_date = datetime.strptime(rec["date"], "%Y-%m-%d")
            days_passed = (today - rec_date).days
            
            # 根據週期判斷檢查時間
            timeframe = rec["timeframe"]
            check_days = {
                "short": 5,   # 短期: 5天
                "mid": 20,    # 中期: 4週
                "long": 60,   # 長期: 2個月
            }
            
            if days_passed < check_days.get(timeframe, 5):
                continue  # 還未到檢查時間
            
            # 獲取當前價格
            current_price = self._get_current_price(rec["stock_code"])
            if current_price is None:
                continue
            
            # 判斷結果
            rec_price = rec["recommended_price"]
            target = rec["target_price"]
            stop = rec["stop_loss"]
            
            change_pct = (current_price - rec_price) / rec_price * 100
            
            if current_price >= target:
                rec["status"] = "success"
                rec["result"] = "達標"
            elif current_price <= stop:
                rec["status"] = "failed"
                rec["result"] = "停損"
            elif days_passed > check_days.get(timeframe, 5) * 2:
                # 超時判斷
                if change_pct > 0:
                    rec["status"] = "success"
                    rec["result"] = "獲利"
                else:
                    rec["status"] = "failed"
                    rec["result"] = "虧損"
            
            rec["result_checked"] = True
            rec["result_price"] = current_price
            rec["result_change_pct"] = round(change_pct, 2)
            rec["result_date"] = today.strftime("%Y-%m-%d")
            
            # 記錄到結果
            if rec["status"] in ["success", "failed"]:
                self.results.append({
                    "id": rec["id"],
                    "stock_code": rec["stock_code"],
                    "stock_name": rec["stock_name"],
                    "timeframe": rec["timeframe"],
                    "date": rec["date"],
                    "result_date": rec["result_date"],
                    "status": rec["status"],
                    "recommended_price": rec_price,
                    "result_price": current_price,
                    "change_pct": change_pct,
                })
        
        self._save_data()
    
    def _get_current_price(self, stock_code: str) -> Optional[float]:
        """獲取股票當前價格"""
        try:
            ticker = yf.Ticker(f"{stock_code}.TW")
            hist = ticker.history(period="1d")
            if not hist.empty:
                return hist['Close'].iloc[-1]
        except Exception as e:
            logger.error(f"獲取 {stock_code} 價格失敗: {e}")
        return None
    
    def get_accuracy_stats(self, days: int = 30) -> Dict:
        """
        計算準確率統計
        
        Args:
            days: 統計天數
        """
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        # 過濾時間範圍內的結果
        recent_results = [r for r in self.results if r["date"] >= cutoff]
        
        total = len(recent_results)
        success = len([r for r in recent_results if r["status"] == "success"])
        failed = len([r for r in recent_results if r["status"] == "failed"])
        
        # 按週期分類
        by_timeframe = {}
        for tf in ["short", "mid", "long"]:
            tf_results = [r for r in recent_results if r["timeframe"] == tf]
            tf_success = len([r for r in tf_results if r["status"] == "success"])
            by_timeframe[tf] = {
                "total": len(tf_results),
                "success": tf_success,
                "accuracy": round(tf_success / len(tf_results) * 100, 1) if tf_results else 0
            }
        
        # 平均報酬率
        avg_return = 0
        if recent_results:
            avg_return = sum(r["change_pct"] for r in recent_results) / len(recent_results)
        
        return {
            "period_days": days,
            "total_recommendations": total,
            "success_count": success,
            "failed_count": failed,
            "overall_accuracy": round(success / total * 100, 1) if total else 0,
            "average_return": round(avg_return, 2),
            "by_timeframe": by_timeframe,
            "updated_at": datetime.now().isoformat()
        }
    
    def get_recent_results(self, limit: int = 20) -> List[Dict]:
        """獲取最近的結果"""
        sorted_results = sorted(self.results, key=lambda x: x["result_date"], reverse=True)
        return sorted_results[:limit]
    
    def get_active_recommendations(self) -> List[Dict]:
        """獲取活躍的推薦 (尚未結算)"""
        return [r for r in self.recommendations if r["status"] == "active"]


# 全域實例
accuracy_tracker = AccuracyTracker()


# ==================== API 函數 ====================

def record_picks(short_term: List, mid_term: List, long_term: List):
    """記錄今日所有推薦"""
    if short_term:
        accuracy_tracker.record_recommendation(short_term, "short")
    if mid_term:
        accuracy_tracker.record_recommendation(mid_term, "mid")
    if long_term:
        accuracy_tracker.record_recommendation(long_term, "long")

def get_accuracy_report(days: int = 30) -> Dict:
    """獲取準確率報告"""
    accuracy_tracker.check_results()
    return accuracy_tracker.get_accuracy_stats(days)
