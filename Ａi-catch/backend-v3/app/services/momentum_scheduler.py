"""
漲停股自動排程與郵件通知服務

功能：
1. 每日自動抓取漲停股數據
2. 追蹤連續多日漲停的股票
3. 發送 Email 通知（產業連動趨勢）
4. 歷史數據分析
"""

import asyncio
import aiohttp
import ssl
import smtplib
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

logger = logging.getLogger(__name__)


class MomentumScheduler:
    """漲停股排程與通知服務"""
    
    def __init__(self):
        # 歷史數據存儲路徑
        self.data_dir = Path("/Users/Mac/Documents/ETF/AI/Ａi-catch/data/momentum_history")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 排程設定
        self.schedule = {
            "morning_update": "09:30",   # 開盤後更新
            "noon_update": "12:05",      # 午盤更新
            "closing_update": "13:35",   # 收盤後更新
            "report_time": "14:00"       # 發送日報
        }
        
        # Email 設定（從環境變數或配置讀取）
        self.email_config = {
            "enabled": True,
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "username": os.environ.get("EMAIL_USERNAME", ""),
            "password": os.environ.get("EMAIL_PASSWORD", ""),
            "recipients": ["k26car@gmail.com", "neimou1225@gmail.com"]
        }
        
        # 快取
        self.today_data = None
        self.history_cache = {}
        
    def _load_history(self, days: int = 30) -> Dict[str, Dict]:
        """載入歷史數據"""
        history = {}
        today = datetime.now()
        
        for i in range(days):
            date = (today - timedelta(days=i)).strftime('%Y%m%d')
            filepath = self.data_dir / f"{date}.json"
            
            if filepath.exists():
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        history[date] = json.load(f)
                except Exception as e:
                    logger.warning(f"載入 {date} 數據失敗: {e}")
                    
        return history
    
    def _save_daily_data(self, date: str, data: Dict):
        """儲存當日數據"""
        filepath = self.data_dir / f"{date}.json"
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"已儲存 {date} 漲停數據")
        except Exception as e:
            logger.error(f"儲存數據失敗: {e}")
    
    async def update_daily_data(self) -> Dict:
        """
        更新當日漲停數據
        這個函數會被排程器調用
        """
        from app.services.limit_stock_monitor import limit_stock_monitor
        
        try:
            # 抓取最新數據
            data = await limit_stock_monitor.fetch_limit_stocks(force_refresh=True)
            
            if data and (data.get('limitUp') or data.get('limitDown')):
                today = datetime.now().strftime('%Y%m%d')
                
                # 添加時間戳
                data['updateTime'] = datetime.now().isoformat()
                data['date'] = today
                
                # 儲存到檔案
                self._save_daily_data(today, data)
                self.today_data = data
                
                logger.info(f"更新成功: {len(data.get('limitUp', []))} 檔漲停, {len(data.get('limitDown', []))} 檔跌停")
                return {"success": True, "data": data}
            else:
                return {"success": False, "error": "無法取得數據"}
                
        except Exception as e:
            logger.error(f"更新失敗: {e}")
            return {"success": False, "error": str(e)}
    
    def analyze_consecutive_limit_up(self, days: int = 5) -> List[Dict]:
        """
        分析連續多日漲停的股票
        
        Returns:
            連續漲停1日以上的股票列表，按連續天數排序
        """
        history = self._load_history(days)
        
        if not history:
            return []
        
        # 統計每檔股票在過去N天內漲停的次數和日期
        stock_limit_up_days = {}
        
        sorted_dates = sorted(history.keys(), reverse=True)  # 最近的日期在前
        
        for date in sorted_dates:
            day_data = history[date]
            limit_up_stocks = day_data.get('limitUp', [])
            
            for stock in limit_up_stocks:
                code = stock.get('code')
                if not code:
                    continue
                
                # 獲取股票名稱，自動查詢如果為空
                stock_name = stock.get('name', '')
                if not stock_name or stock_name == code:
                    # 嘗試自動查詢名稱
                    stock_name = self._get_stock_name(code)
                    
                if code not in stock_limit_up_days:
                    stock_limit_up_days[code] = {
                        'code': code,
                        'name': stock_name,
                        'market': stock.get('market', 'TWSE'),
                        'dates': [],
                        'consecutiveDays': 0,
                        'latestPrice': stock.get('close', 0),
                        'latestChangePct': stock.get('changePct', 0)
                    }
                    
                stock_limit_up_days[code]['dates'].append(date)
        
        # 計算連續漲停天數
        results = []
        for code, info in stock_limit_up_days.items():
            dates = sorted(info['dates'], reverse=True)  # 最新日期在前
            
            # 計算從今天開始的連續天數
            consecutive = 0
            prev_date = None
            
            for date in dates:
                if prev_date is None:
                    consecutive = 1
                    prev_date = datetime.strptime(date, '%Y%m%d')
                else:
                    current_date = datetime.strptime(date, '%Y%m%d')
                    diff = (prev_date - current_date).days
                    
                    # 考慮週末（最多3天差距算連續）
                    if diff <= 3:
                        consecutive += 1
                        prev_date = current_date
                    else:
                        break
            
            info['consecutiveDays'] = consecutive
            info['totalDays'] = len(dates)
            
            # 只保留至少連續1天的
            if consecutive >= 1:
                results.append(info)
        
        # 按連續天數排序
        results.sort(key=lambda x: (x['consecutiveDays'], x['totalDays']), reverse=True)
        
        return results
    
    def _get_stock_name(self, code: str) -> str:
        """自動查詢股票名稱"""
        # 快取機制
        if not hasattr(self, '_name_cache'):
            self._name_cache = {}
        
        if code in self._name_cache:
            return self._name_cache[code]
        
        try:
            from app.config.big_order_config import get_stock_name
            name = get_stock_name(code)
            if name and name != code:
                self._name_cache[code] = name
                return name
        except Exception as e:
            logger.debug(f"查詢股票名稱失敗 {code}: {e}")
        
        # 如果查詢失敗，嘗試 yfinance
        try:
            import yfinance as yf
            ticker = yf.Ticker(f"{code}.TW")
            info = ticker.info
            name = info.get('shortName') or info.get('longName')
            if name:
                # 清理名稱
                name = name.split(' Ordinary')[0].split(' ADR')[0].strip()
                self._name_cache[code] = name
                return name
        except Exception:
            pass
        
        return code  # 查詢失敗返回代碼
    
    def get_industry_trend_analysis(self) -> Dict:
        """
        分析產業趨勢
        
        Returns:
            包含產業連動分析的字典
        """
        from app.services.stock_momentum_service import stock_momentum_service
        
        # 使用最近5天的數據
        history = self._load_history(5)
        
        if not history:
            return {"industries": {}, "trends": []}
        
        # 統計各產業在過去5天的漲停股數量
        industry_stats = {}
        
        for date, day_data in history.items():
            limit_up_stocks = day_data.get('limitUp', [])
            
            for stock in limit_up_stocks:
                code = stock.get('code', '')
                # 使用現有的產業映射
                industry = stock_momentum_service._get_stock_industry(code)
                
                if industry not in industry_stats:
                    industry_stats[industry] = {
                        'industry': industry,
                        'totalLimitUp': 0,
                        'daysActive': set(),
                        'stocks': set()
                    }
                
                industry_stats[industry]['totalLimitUp'] += 1
                industry_stats[industry]['daysActive'].add(date)
                industry_stats[industry]['stocks'].add(code)
        
        # 轉換為列表並計算趨勢強度
        trends = []
        for industry, stats in industry_stats.items():
            trend = {
                'industry': industry,
                'totalLimitUp': stats['totalLimitUp'],
                'daysActive': len(stats['daysActive']),
                'stockCount': len(stats['stocks']),
                'stocks': list(stats['stocks']),
                # 計算趨勢強度分數（0-100）
                'trendScore': min(100, (stats['totalLimitUp'] * 10) + (len(stats['daysActive']) * 15))
            }
            trends.append(trend)
        
        # 按趨勢強度排序
        trends.sort(key=lambda x: x['trendScore'], reverse=True)
        
        # 識別爆發趨勢（多天連續有漲停）
        emerging_trends = [t for t in trends if t['daysActive'] >= 3 and t['totalLimitUp'] >= 3]
        
        return {
            "industries": industry_stats,
            "trends": trends[:10],  # Top 10 產業
            "emergingTrends": emerging_trends
        }
    
    async def send_momentum_email_report(self) -> Dict:
        """
        發送漲停股郵件報告
        
        包含：
        - 今日漲停股列表（上市 + 上櫃）
        - 連續漲停股追蹤
        - 產業連動趨勢
        - 潛在機會股
        """
        from app.services.limit_stock_monitor import limit_stock_monitor
        
        if not self.email_config.get('enabled'):
            return {"success": False, "error": "Email 未啟用"}
            
        if not self.email_config.get('username') or not self.email_config.get('password'):
            return {"success": False, "error": "Email 設定不完整"}
        
        try:
            # 獲取今日數據
            report = await limit_stock_monitor.get_daily_momentum_report()
            consecutive_stocks = self.analyze_consecutive_limit_up(5)
            industry_trends = self.get_industry_trend_analysis()
            
            # 生成 HTML 郵件內容
            html_content = self._generate_email_html(report, consecutive_stocks, industry_trends)
            
            # 發送郵件
            result = await self._send_email(
                subject=f"📈 今日漲停股分析報告 - {datetime.now().strftime('%Y-%m-%d')}",
                html_body=html_content
            )
            
            return result
            
        except Exception as e:
            logger.error(f"發送郵件失敗: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_email_html(self, report: Dict, consecutive: List, trends: Dict) -> str:
        """生成 HTML 郵件內容"""
        
        limit_up = report.get('limitUp', [])
        limit_down = report.get('limitDown', [])
        opportunities = report.get('opportunities', [])
        chain_reaction = report.get('chainReaction', [])
        
        # 分離上市和上櫃
        twse_stocks = [s for s in limit_up if s.get('market') == 'TWSE']
        otc_stocks = [s for s in limit_up if s.get('market') == 'OTC']
        
        html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>今日漲停股分析報告</title>
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang TC', 'Microsoft JhengHei', 'Noto Sans TC', 'Heiti TC', sans-serif; 
            background: #f5f5f5; 
            padding: 20px; 
            margin: 0;
            -webkit-font-smoothing: antialiased;
        }}
        .container {{ max-width: 700px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 12px 12px 0 0; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 24px; font-weight: 600; }}
        .header .date {{ opacity: 0.9; margin-top: 8px; font-size: 14px; }}
        .section {{ padding: 20px; border-bottom: 1px solid #e5e7eb; }}
        .section-title {{ font-size: 18px; font-weight: bold; color: #1f2937; margin-bottom: 15px; }}
        .stats {{ margin-bottom: 15px; }}
        .stats table {{ width: 100%; border-collapse: collapse; }}
        .stats td {{ background: #f3f4f6; padding: 12px 18px; border-radius: 8px; text-align: center; }}
        .stat-number {{ font-size: 24px; font-weight: bold; color: #dc2626; display: block; }}
        .stat-label {{ font-size: 12px; color: #6b7280; }}
        .stock-list {{ line-height: 2; }}
        .stock-tag {{ background: #fee2e2; color: #dc2626; padding: 4px 8px; border-radius: 4px; font-size: 13px; display: inline-block; margin: 2px; white-space: nowrap; }}
        .consecutive {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px; margin: 10px 0; border-radius: 0 8px 8px 0; }}
        .trend-item {{ background: #eff6ff; padding: 12px; border-radius: 8px; margin: 8px 0; }}
        .opportunity {{ background: #f0fdf4; border-left: 4px solid #22c55e; padding: 12px; margin: 10px 0; border-radius: 0 8px 8px 0; }}
        .footer {{ padding: 15px; text-align: center; color: #9ca3af; font-size: 12px; }}
        .market-label {{ font-weight: bold; margin: 15px 0 8px; color: #4b5563; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>&#128640; 今日漲停股分析報告</h1>
            <div class="date">{datetime.now().strftime('%Y年%m月%d日 %H:%M')}</div>
        </div>
        
        <div class="section">
            <div class="section-title">&#128202; 今日統計</div>
            <table class="stats" cellspacing="8">
                <tr>
                    <td>
                        <span class="stat-number">{len(limit_up)}</span>
                        <span class="stat-label">漲停股</span>
                    </td>
                    <td>
                        <span class="stat-number" style="color: #16a34a;">{len(limit_down)}</span>
                        <span class="stat-label">跌停股</span>
                    </td>
                    <td>
                        <span class="stat-number" style="color: #7c3aed;">{len(twse_stocks)}</span>
                        <span class="stat-label">上市</span>
                    </td>
                    <td>
                        <span class="stat-number" style="color: #0891b2;">{len(otc_stocks)}</span>
                        <span class="stat-label">上櫃</span>
                    </td>
                </tr>
            </table>
        </div>
        
        <div class="section">
            <div class="section-title">&#128308; 漲停股列表</div>
            <div class="market-label">&#128204; 上市 ({len(twse_stocks)} 檔)</div>
            <div class="stock-list">
                {"".join([f'<span class="stock-tag">{s["code"]} {s["name"]} +{s["changePct"]:.1f}%</span> ' for s in twse_stocks[:15]])}
                {"<span style='color:#6b7280;'>...更多</span>" if len(twse_stocks) > 15 else ""}
            </div>
            <div class="market-label">&#128204; 上櫃 ({len(otc_stocks)} 檔)</div>
            <div class="stock-list">
                {"".join([f'<span class="stock-tag">{s["code"]} {s["name"]} +{s["changePct"]:.1f}%</span> ' for s in otc_stocks[:15]])}
                {"<span style='color:#6b7280;'>...更多</span>" if len(otc_stocks) > 15 else ""}
            </div>
        </div>
"""
        
        # 連續漲停股
        consecutive_top = [c for c in consecutive if c['consecutiveDays'] >= 2][:5]
        if consecutive_top:
            html += """
        <div class="section">
            <div class="section-title">🔥 連續漲停追蹤</div>
"""
            for stock in consecutive_top:
                html += f"""
            <div class="consecutive">
                <strong>{stock['code']} {stock['name']}</strong> - 連續 {stock['consecutiveDays']} 天漲停
                <br><small>最新: ${stock['latestPrice']:.2f} (+{stock['latestChangePct']:.1f}%)</small>
            </div>
"""
            html += "        </div>"
        
        # 產業連動趨勢
        if chain_reaction:
            html += """
        <div class="section">
            <div class="section-title">📈 產業連動趨勢</div>
"""
            for trend in chain_reaction[:3]:
                html += f"""
            <div class="trend-item">
                <strong>{trend['industry']}</strong>: {trend['description']}
            </div>
"""
            html += "        </div>"
        
        # 潛在機會股
        if opportunities:
            html += """
        <div class="section">
            <div class="section-title">💡 潛在機會股</div>
"""
            for opp in opportunities[:5]:
                html += f"""
            <div class="opportunity">
                <strong>{opp['code']} {opp['name']}</strong> ({opp['industry']})
                <br><small>{opp['reason']}</small>
            </div>
"""
            html += "        </div>"
        
        # 頁尾
        html += """
        <div class="footer">
            此郵件由 AI 股票分析系統自動發送<br>
            如需停止接收，請聯繫系統管理員
        </div>
    </div>
</body>
</html>
"""
        return html
    
    async def _send_email(self, subject: str, html_body: str) -> Dict:
        """發送 Email"""
        settings = self.email_config
        
        if not settings['recipients']:
            return {"success": False, "error": "沒有設定收件人"}
        
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = settings['username']
            msg['To'] = ", ".join(settings['recipients'])
            msg['Subject'] = subject
            
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))
            
            server = smtplib.SMTP(settings['smtp_server'], settings['smtp_port'])
            server.starttls()
            server.login(settings['username'], settings['password'])
            server.sendmail(settings['username'], settings['recipients'], msg.as_string())
            server.quit()
            
            logger.info(f"郵件已發送給 {len(settings['recipients'])} 位收件人")
            return {"success": True, "recipients": len(settings['recipients'])}
            
        except Exception as e:
            logger.error(f"發送郵件失敗: {e}")
            return {"success": False, "error": str(e)}
    
    def get_detailed_stock_analysis(self, code: str) -> Dict:
        """
        取得單支股票的詳細分析
        包含：歷史漲停記錄、成交量分析、週轉率等
        """
        history = self._load_history(30)
        
        stock_history = {
            'code': code,
            'limitUpDays': [],
            'limitDownDays': [],
            'stats': {}
        }
        
        for date, day_data in history.items():
            # 檢查是否在漲停列表
            for stock in day_data.get('limitUp', []):
                if stock.get('code') == code:
                    stock_history['limitUpDays'].append({
                        'date': date,
                        'close': stock.get('close'),
                        'changePct': stock.get('changePct'),
                        'volume': stock.get('volume', 0)
                    })
                    if not stock_history.get('name'):
                        stock_history['name'] = stock.get('name', '')
                        stock_history['market'] = stock.get('market', 'TWSE')
                    break
            
            # 檢查是否在跌停列表
            for stock in day_data.get('limitDown', []):
                if stock.get('code') == code:
                    stock_history['limitDownDays'].append({
                        'date': date,
                        'close': stock.get('close'),
                        'changePct': stock.get('changePct')
                    })
                    break
        
        # 計算統計
        stock_history['stats'] = {
            'limitUpCount': len(stock_history['limitUpDays']),
            'limitDownCount': len(stock_history['limitDownDays']),
            'lastLimitUpDate': stock_history['limitUpDays'][0]['date'] if stock_history['limitUpDays'] else None
        }
        
        return stock_history


# 創建服務實例
momentum_scheduler = MomentumScheduler()
