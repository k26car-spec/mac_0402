"""
撐壓趨勢轉折 API
Support & Resistance Trend Reversal API

提供：
- 單股撐壓趨勢分析
- 批量分析
- 趨勢轉折偵測
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/support-resistance", tags=["Support Resistance Analysis"])


@router.get("/analyze/{stock_code}")
async def analyze_support_resistance(stock_code: str):
    """
    撐壓趨勢轉折分析
    
    分析股票的：
    - 多層級撐壓位
    - 趨勢狀態（短/中/長期）
    - 趨勢轉折訊號
    - 風險回報評估
    - 交易建議
    
    Args:
        stock_code: 股票代碼 (如: 2330, 2454)
    
    Returns:
        完整的撐壓趨勢分析結果
    """
    try:
        from app.services.support_resistance_analyzer import support_resistance_analyzer
        
        result = await support_resistance_analyzer.analyze(stock_code)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"無法取得 {stock_code} 的撐壓趨勢資料"
            )
        
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"撐壓趨勢分析失敗 {stock_code}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"分析失敗: {str(e)}"
        )


@router.get("/batch")
async def batch_analyze(
    stock_codes: str = Query(..., description="股票代碼，逗號分隔，如: 2330,2454,2317")
):
    """
    批量撐壓趨勢分析
    
    一次分析多檔股票的撐壓趨勢
    
    Args:
        stock_codes: 逗號分隔的股票代碼列表
    
    Returns:
        多檔股票的撐壓趨勢分析結果
    """
    try:
        from app.services.support_resistance_analyzer import support_resistance_analyzer
        import asyncio
        
        codes = [c.strip() for c in stock_codes.split(',') if c.strip()]
        
        if not codes:
            raise HTTPException(status_code=400, detail="請提供至少一個股票代碼")
        
        if len(codes) > 10:
            raise HTTPException(status_code=400, detail="最多一次分析 10 檔股票")
        
        # 並行分析
        tasks = [support_resistance_analyzer.analyze(code) for code in codes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        analyses = []
        errors = []
        
        for code, result in zip(codes, results):
            if isinstance(result, Exception):
                errors.append({"stock_code": code, "error": str(result)})
            elif result:
                analyses.append(result)
            else:
                errors.append({"stock_code": code, "error": "資料取得失敗"})
        
        return {
            "success": True,
            "count": len(analyses),
            "data": analyses,
            "errors": errors if errors else None,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量分析失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"批量分析失敗: {str(e)}"
        )


@router.get("/reversal-signals")
async def get_reversal_signals(
    stock_codes: str = Query(..., description="股票代碼，逗號分隔"),
    signal_type: Optional[str] = Query(None, description="訊號類型：bullish_reversal, bearish_reversal")
):
    """
    取得趨勢轉折訊號
    
    篩選出有明確轉折訊號的股票
    
    Args:
        stock_codes: 股票代碼列表
        signal_type: 可選的訊號類型篩選
    
    Returns:
        有轉折訊號的股票列表
    """
    try:
        from app.services.support_resistance_analyzer import support_resistance_analyzer
        import asyncio
        
        codes = [c.strip() for c in stock_codes.split(',') if c.strip()]
        
        if not codes:
            raise HTTPException(status_code=400, detail="請提供至少一個股票代碼")
        
        # 並行分析
        tasks = [support_resistance_analyzer.analyze(code) for code in codes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        signals = []
        
        for code, result in zip(codes, results):
            if isinstance(result, Exception) or not result:
                continue
            
            reversal = result.get('reversal_signal', {})
            reversal_type = reversal.get('type', 'neutral')
            
            # 篩選有意義的轉折訊號
            if reversal_type in ['bullish_reversal', 'bearish_reversal']:
                if signal_type and reversal_type != signal_type:
                    continue
                
                signals.append({
                    'stock_code': result['stock_code'],
                    'stock_name': result['stock_name'],
                    'current_price': result['current_price'],
                    'signal_type': reversal_type,
                    'strength': reversal.get('strength', 0),
                    'confidence': reversal.get('confidence', 0),
                    'signals': reversal.get('signals', []),
                    'action': reversal.get('action', 'hold'),
                    'recommendation': result.get('recommendation', ''),
                    'overall_score': result.get('overall_score', 50)
                })
        
        # 按強度排序
        signals.sort(key=lambda x: x['strength'], reverse=True)
        
        return {
            "success": True,
            "count": len(signals),
            "bullish_count": len([s for s in signals if s['signal_type'] == 'bullish_reversal']),
            "bearish_count": len([s for s in signals if s['signal_type'] == 'bearish_reversal']),
            "signals": signals,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取得轉折訊號失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"取得轉折訊號失敗: {str(e)}"
        )


@router.get("/key-levels/{stock_code}")
async def get_key_levels(stock_code: str):
    """
    取得關鍵價位
    
    快速取得股票的關鍵撐壓價位和建議停損停利點
    
    Returns:
        - 最近壓力/支撐位
        - 建議進場價
        - 建議停損價
        - 建議目標價
    """
    try:
        from app.services.support_resistance_analyzer import support_resistance_analyzer
        
        result = await support_resistance_analyzer.analyze(stock_code)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"無法取得 {stock_code} 的價位資料"
            )
        
        return {
            "success": True,
            "stock_code": result['stock_code'],
            "stock_name": result['stock_name'],
            "current_price": result['current_price'],
            "key_levels": {
                "nearest_resistance": result['nearest_resistance'],
                "nearest_support": result['nearest_support'],
                "resistance_distance_pct": result['resistance_distance_pct'],
                "support_distance_pct": result['support_distance_pct']
            },
            "risk_reward": result['risk_reward_analysis'],
            "recommendation": result['recommendation'],
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取得關鍵價位失敗 {stock_code}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"取得關鍵價位失敗: {str(e)}"
        )


@router.get("/intraday-data/{stock_code}")
async def get_intraday_data(stock_code: str):
    """
    取得當沖數據 (富邦即時版)
    """
    try:
        from app.services.fubon_service import get_intraday_data as fetch_fubon_intraday, calculate_vwap
        from datetime import datetime
        
        # 1. 取得富邦 1m K 線
        candles = await fetch_fubon_intraday(stock_code, timeframe="1")
        
        if not candles:
            # 備援：若富邦無數據，嘗試目前的報價
            from app.services.fubon_service import get_realtime_quote
            quote = await get_realtime_quote(stock_code)
            return {
                "success": True,
                "stock_code": stock_code,
                "data_type": "quote_only",
                "current": quote.get("price", 0),
                "open_price": quote.get("open", 0),
                "day_high": quote.get("high", 0),
                "day_low": quote.get("low", 0),
                "vwap": 0,
                "timestamp": datetime.now().isoformat()
            }
        
        # 2. 計算指標
        import pandas as pd
        df = pd.DataFrame(candles)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(int)
        
        # 前15分鐘
        first_15 = df.head(15)
        range_high = float(first_15['high'].max())
        range_low = float(first_15['low'].min())
        open_price = float(df['open'].iloc[0])
        
        current = float(df['close'].iloc[-1])
        day_high = float(df['high'].max())
        day_low = float(df['low'].min())
        vwap = calculate_vwap(candles)
        
        range_size = range_high - range_low
        signal = "neutral"
        if current > range_high: signal = "bullish_breakout"
        elif current < range_low: signal = "bearish_breakout"
        
        return {
            "success": True,
            "stock_code": stock_code,
            "data_type": "fubon_intraday",
            "range_high": range_high,
            "range_low": range_low,
            "current": current,
            "open_price": open_price,
            "day_high": day_high,
            "day_low": day_low,
            "vwap": vwap,
            "volume": int(df['volume'].sum()),
            "signal": signal,
            "range_position_pct": round((current - range_low) / range_size * 100, 1) if range_size > 0 else 50,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"取得當沖數據失敗 {stock_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取得當沖數據失敗 {stock_code}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"取得當沖數據失敗: {str(e)}"
        )


@router.post("/send-report/{stock_code}")
async def send_trade_analyzer_report(
    stock_code: str,
    send_email: bool = Query(default=True, description="是否發送郵件"),
    recipient: Optional[str] = Query(default=None, description="指定收件人 (可選)")
):
    """
    生成並發送交易分析報告
    
    整合：撐壓趨勢、分析戰報、倉位風控、斐波那契、當沖判讀
    
    Args:
        stock_code: 股票代碼
        send_email: 是否發送郵件
        recipient: 指定收件人 (可選，未指定則使用預設)
    
    Returns:
        報告生成結果和發送狀態
    """
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from app.services.support_resistance_analyzer import support_resistance_analyzer
        from app.services.trade_analyzer_report import generate_trade_analyzer_html
        import yfinance as yf
        
        # 1. 取得撐壓趨勢資料
        sr_result = await support_resistance_analyzer.analyze(stock_code)
        if not sr_result:
            raise HTTPException(status_code=404, detail=f"無法取得 {stock_code} 資料")
        
        # 2. 取得當沖數據
        ticker = yf.Ticker(f"{stock_code}.TW")
        hist = ticker.history(period="1d", interval="1m")
        
        if hist.empty:
            ticker = yf.Ticker(f"{stock_code}.TWO")
            hist = ticker.history(period="1d", interval="1m")
        
        intraday_data = {}
        if not hist.empty and len(hist) >= 15:
            first_15 = hist.head(15)
            range_high = float(first_15['High'].max())
            range_low = float(first_15['Low'].min())
            current = float(hist['Close'].iloc[-1])
            range_size = range_high - range_low
            
            # 判斷訊號
            if current > range_high:
                signal = "bullish_breakout"
                signal_text = "🔴 突破高點 - 強勢多頭"
            elif current < range_low:
                signal = "bearish_breakout"  
                signal_text = "🟢 跌破低點 - 弱勢空頭"
            else:
                signal = "neutral"
                signal_text = "⚖️ 中性盤整"
            
            # 計算目標價
            if current > range_high + range_size:
                long_stop = current - range_size * 0.5
            else:
                long_stop = range_high - range_size * 0.2
                
            if current < range_low - range_size:
                short_stop = current + range_size * 0.5
            else:
                short_stop = range_low + range_size * 0.2
            
            intraday_data = {
                'range_high': range_high,
                'range_low': range_low,
                'current': current,
                'signal': signal,
                'signal_text': signal_text,
                'long_target1': current + range_size * 0.5 if current > range_high else range_high + range_size * 0.5,
                'long_stop': long_stop,
                'short_target1': current - range_size * 0.5 if current < range_low else range_low - range_size * 0.5,
                'short_stop': short_stop
            }
        
        # 3. 取得籌碼數據
        volume_profile_data = {}
        try:
            from app.services.volume_profile_analyzer import VolumeProfileAnalyzer
            vp_analyzer = VolumeProfileAnalyzer()
            vp_result = await vp_analyzer.get_summary(stock_code)
            if vp_result:
                volume_profile_data = vp_result
        except Exception as e:
            logger.warning(f"籌碼分析失敗: {e}")
        
        # 4. 組裝報告數據
        report_data = {
            'stock_code': sr_result['stock_code'],
            'stock_name': sr_result['stock_name'],
            'current_price': sr_result['current_price'],
            'support_resistance': {
                'trend_status': sr_result.get('trend_status', {}),
                'reversal_signal': sr_result.get('reversal_signal', {}),
                'risk_reward_analysis': sr_result.get('risk_reward_analysis', {}),
                'resistance_levels': sr_result.get('resistance_levels', []),
                'support_levels': sr_result.get('support_levels', [])
            },
            'checklist': [
                {'id': 1, 'text': '股價站上20日均線且月線翻揚?', 'checked': True, 'reason': ''},
                {'id': 2, 'text': '均線呈現多頭排列?', 'checked': True, 'reason': ''},
                {'id': 3, 'text': '布林通道收窄後突破?', 'checked': False, 'reason': ''},
                {'id': 4, 'text': '成交量大於5日均量?', 'checked': True, 'reason': ''},
                {'id': 5, 'text': '出現突破缺口?', 'checked': False, 'reason': ''},
                {'id': 6, 'text': '法人連續買超?', 'checked': True, 'reason': ''},
                {'id': 7, 'text': '技術型態突破?', 'checked': False, 'reason': ''},
                {'id': 8, 'text': 'MACD/KD黃金交叉?', 'checked': True, 'reason': ''},
                {'id': 9, 'text': '斐波那契支撐有守?', 'checked': True, 'reason': ''},
                {'id': 10, 'text': '籌碼集中度良好?', 'checked': False, 'reason': ''}
            ],
            'score': sr_result.get('overall_score', 60),
            'recommendation': sr_result.get('recommendation', '持有觀望'),
            'risk_calculator': {
                'entry_price': sr_result['current_price'],
                'stop_loss': sr_result.get('risk_reward_analysis', {}).get('stop_loss_price', 0),
                'target_price': sr_result.get('risk_reward_analysis', {}).get('target_price', 0),
                'position_size': 1000,
                'risk_reward_ratio': sr_result.get('risk_reward_analysis', {}).get('risk_reward_ratio', 0)
            },
            'fibonacci': {
                'high': max([l['price'] for l in sr_result.get('resistance_levels', [{'price': sr_result['current_price'] * 1.1}])]),
                'low': min([l['price'] for l in sr_result.get('support_levels', [{'price': sr_result['current_price'] * 0.9}])]),
                'trend': 'uptrend',
                'fib_382': 0,
                'fib_500': 0,
                'fib_618': 0
            },
            'intraday': intraday_data,
            'volume_profile': volume_profile_data
        }
        
        # 計算斐波那契
        fib_range = report_data['fibonacci']['high'] - report_data['fibonacci']['low']
        report_data['fibonacci']['fib_382'] = report_data['fibonacci']['high'] - fib_range * 0.382
        report_data['fibonacci']['fib_500'] = report_data['fibonacci']['high'] - fib_range * 0.5
        report_data['fibonacci']['fib_618'] = report_data['fibonacci']['high'] - fib_range * 0.618
        
        # 5. 生成 HTML 報告
        html_content = generate_trade_analyzer_html(report_data)
        
        # 6. 發送郵件
        email_result = {"success": False, "message": "未發送"}
        
        if send_email:
            try:
                from app.main import NOTIFICATION_SETTINGS
                settings = NOTIFICATION_SETTINGS["email"]
                
                if settings["username"] and settings["password"]:
                    msg = MIMEMultipart()
                    msg["From"] = settings["username"]
                    recipients = [recipient] if recipient else settings["recipients"]
                    msg["To"] = ", ".join(recipients)
                    msg["Subject"] = f"[交易分析報告] {stock_code} {sr_result['stock_name']} - {datetime.now().strftime('%Y/%m/%d %H:%M')}"
                    
                    msg.attach(MIMEText(html_content, "html"))
                    
                    server = smtplib.SMTP(settings["smtp_server"], settings["smtp_port"])
                    server.starttls()
                    server.login(settings["username"], settings["password"])
                    server.sendmail(settings["username"], recipients, msg.as_string())
                    server.quit()
                    
                    email_result = {"success": True, "recipients": len(recipients)}
                else:
                    email_result = {"success": False, "message": "Email 設定不完整"}
            except Exception as e:
                email_result = {"success": False, "message": str(e)}
        
        return {
            "success": True,
            "stock_code": stock_code,
            "stock_name": sr_result['stock_name'],
            "report_generated": True,
            "email_sent": email_result,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"報告生成失敗 {stock_code}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"報告生成失敗: {str(e)}"
        )


# 開盤5分鐘自動發送報告的排程任務

@router.post("/schedule-report")
async def schedule_morning_report(
    stock_codes: str = Query(..., description="股票代碼，逗號分隔"),
    send_time: str = Query(default="09:05", description="發送時間，格式 HH:MM")
):
    """
    排程開盤5分鐘後自動發送報告
    
    預設 09:05 發送（開盤後5分鐘）
    
    Args:
        stock_codes: 股票代碼列表
        send_time: 發送時間
    
    Returns:
        排程設定結果
    """
    codes = [c.strip() for c in stock_codes.split(',') if c.strip()]
    
    if not codes:
        raise HTTPException(status_code=400, detail="請提供至少一個股票代碼")
    
    # 使用真正的排程器
    try:
        from app.services.trade_report_scheduler import trade_report_scheduler
        result = trade_report_scheduler.set_schedule(codes, send_time)
        return {
            "success": True,
            "scheduled_stocks": codes,
            "send_time": send_time,
            "message": f"已排程 {len(codes)} 檔股票於 {send_time} 發送報告"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"排程設定失敗: {str(e)}")


@router.get("/scheduled-reports")
async def get_scheduled_reports():
    """取得目前排程設定"""
    try:
        from app.services.trade_report_scheduler import trade_report_scheduler
        return {
            "success": True,
            "scheduled": trade_report_scheduler.get_status()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.delete("/scheduled-reports")
async def cancel_scheduled_reports():
    """取消排程"""
    try:
        from app.services.trade_report_scheduler import trade_report_scheduler
        trade_report_scheduler.cancel_schedule()
        return {
            "success": True,
            "message": "已取消所有排程"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消排程失敗: {str(e)}")


@router.post("/send-reports-now")
async def send_reports_now():
    """立即發送所有排程的報告（測試用）"""
    try:
        from app.services.trade_report_scheduler import trade_report_scheduler
        
        if not trade_report_scheduler.scheduled_stocks:
            raise HTTPException(status_code=400, detail="沒有排程的股票")
        
        result = await trade_report_scheduler.send_all_reports()
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"發送失敗: {str(e)}")
