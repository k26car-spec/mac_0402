"""
交易分析 PDF 報告生成器
Trade Analyzer PDF Report Generator

整合：撐壓趨勢、分析戰報、倉位風控、斐波那契、當沖判讀
"""

import os
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def generate_trade_analyzer_html(data: Dict[str, Any]) -> str:
    """
    生成交易分析 HTML 報告
    
    Args:
        data: 包含各項分析數據的字典
    
    Returns:
        HTML 格式的報告內容
    """
    stock_code = data.get('stock_code', 'N/A')
    stock_name = data.get('stock_name', 'N/A')
    current_price = data.get('current_price', 0)
    analysis_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 撐壓趨勢
    sr = data.get('support_resistance', {})
    trend_status = sr.get('trend_status', {})
    reversal_signal = sr.get('reversal_signal', {})
    risk_reward = sr.get('risk_reward_analysis', {})
    
    # 分析戰報
    checklist = data.get('checklist', [])
    score = data.get('score', 0)
    recommendation = data.get('recommendation', '')
    
    # 倉位風控
    risk_calc = data.get('risk_calculator', {})
    
    # 斐波那契
    fibonacci = data.get('fibonacci', {})
    
    # 當沖判讀
    intraday = data.get('intraday', {})
    
    # 籌碼分析
    volume_profile = data.get('volume_profile', {})
    
    # 生成 HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{stock_code} {stock_name} 交易分析報告</title>
        <style>
            body {{
                font-family: 'Arial', 'Microsoft JhengHei', sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }}
            .report-container {{
                background: white;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .header {{
                text-align: center;
                border-bottom: 3px solid #3b82f6;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }}
            .header h1 {{
                color: #1e3a5f;
                margin: 0;
                font-size: 28px;
            }}
            .stock-info {{
                display: flex;
                justify-content: center;
                gap: 20px;
                margin-top: 15px;
            }}
            .stock-badge {{
                background: #3b82f6;
                color: white;
                padding: 8px 20px;
                border-radius: 20px;
                font-weight: bold;
                font-size: 18px;
            }}
            .price-badge {{
                background: #ef4444;
                color: white;
                padding: 8px 20px;
                border-radius: 20px;
                font-weight: bold;
                font-size: 18px;
            }}
            .section {{
                margin-bottom: 25px;
                padding: 20px;
                border-radius: 10px;
            }}
            .section-title {{
                display: flex;
                align-items: center;
                gap: 10px;
                font-size: 18px;
                font-weight: bold;
                color: #1e3a5f;
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 2px solid #e5e7eb;
            }}
            .section-icon {{
                font-size: 24px;
            }}
            .sr-section {{ background: #f0f9ff; }}
            .checklist-section {{ background: #f0fdf4; }}
            .risk-section {{ background: #fef3c7; }}
            .fib-section {{ background: #fdf4ff; }}
            .intraday-section {{ background: #fff7ed; }}
            .vp-section {{ background: #f5f3ff; }}
            
            .grid-2 {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
            }}
            .grid-3 {{
                display: grid;
                grid-template-columns: 1fr 1fr 1fr;
                gap: 15px;
            }}
            .data-card {{
                background: white;
                padding: 12px;
                border-radius: 8px;
                text-align: center;
            }}
            .data-label {{
                font-size: 12px;
                color: #6b7280;
            }}
            .data-value {{
                font-size: 20px;
                font-weight: bold;
                color: #1f2937;
            }}
            .bullish {{ color: #ef4444; }}
            .bearish {{ color: #22c55e; }}
            
            .checklist-item {{
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 8px 12px;
                background: white;
                border-radius: 6px;
                margin-bottom: 8px;
            }}
            .check-icon {{
                width: 20px;
                height: 20px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 12px;
            }}
            .checked {{
                background: #22c55e;
                color: white;
            }}
            .unchecked {{
                background: #e5e7eb;
                color: #9ca3af;
            }}
            .checklist-text {{
                flex: 1;
                font-size: 14px;
            }}
            .checklist-reason {{
                font-size: 11px;
                color: #6b7280;
                background: #f3f4f6;
                padding: 2px 8px;
                border-radius: 4px;
            }}
            
            .score-box {{
                text-align: center;
                padding: 20px;
                background: white;
                border-radius: 10px;
                margin-bottom: 15px;
            }}
            .score-value {{
                font-size: 48px;
                font-weight: bold;
            }}
            .score-a {{ color: #22c55e; }}
            .score-b {{ color: #3b82f6; }}
            .score-c {{ color: #f59e0b; }}
            .score-d {{ color: #ef4444; }}
            
            .recommendation-box {{
                background: linear-gradient(135deg, #3b82f6, #1e40af);
                color: white;
                padding: 15px 20px;
                border-radius: 10px;
                text-align: center;
            }}
            
            .level-item {{
                display: flex;
                justify-content: space-between;
                padding: 8px 12px;
                background: white;
                border-radius: 6px;
                margin-bottom: 6px;
            }}
            .resistance {{ border-left: 4px solid #ef4444; }}
            .support {{ border-left: 4px solid #22c55e; }}
            
            .signal-box {{
                padding: 15px;
                border-radius: 8px;
                text-align: center;
            }}
            .signal-bullish {{ background: #fee2e2; color: #991b1b; }}
            .signal-bearish {{ background: #dcfce7; color: #166534; }}
            .signal-neutral {{ background: #f3f4f6; color: #374151; }}
            
            .footer {{
                text-align: center;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #e5e7eb;
                color: #6b7280;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="report-container">
            <div class="header">
                <h1>📊 交易分析報告</h1>
                <div class="stock-info">
                    <span class="stock-badge">{stock_code} {stock_name}</span>
                    <span class="price-badge">現價 ${current_price}</span>
                </div>
                <p style="color: #6b7280; margin-top: 10px;">{analysis_time}</p>
            </div>
    """
    
    # 1. 撐壓趨勢區塊
    short_term = trend_status.get('short_term', 'neutral')
    mid_term = trend_status.get('mid_term', 'neutral')
    long_term = trend_status.get('long_term', 'neutral')
    
    def trend_class(t):
        return 'bullish' if t == 'bullish' else 'bearish' if t == 'bearish' else ''
    
    def trend_text(t):
        return '偏多' if t == 'bullish' else '偏空' if t == 'bearish' else '盤整'
    
    resistance_levels = sr.get('resistance_levels', [])[:3]
    support_levels = sr.get('support_levels', [])[:3]
    
    html += f"""
            <div class="section sr-section">
                <div class="section-title">
                    <span class="section-icon">📈</span> 撐壓趨勢分析
                </div>
                <div class="grid-3">
                    <div class="data-card">
                        <div class="data-label">短期趨勢</div>
                        <div class="data-value {trend_class(short_term)}">{trend_text(short_term)}</div>
                    </div>
                    <div class="data-card">
                        <div class="data-label">中期趨勢</div>
                        <div class="data-value {trend_class(mid_term)}">{trend_text(mid_term)}</div>
                    </div>
                    <div class="data-card">
                        <div class="data-label">長期趨勢</div>
                        <div class="data-value {trend_class(long_term)}">{trend_text(long_term)}</div>
                    </div>
                </div>
                <div class="grid-2" style="margin-top: 15px;">
                    <div>
                        <h4 style="color: #ef4444; margin-bottom: 10px;">🔺 壓力位</h4>
    """
    
    for level in resistance_levels:
        html += f"""
                        <div class="level-item resistance">
                            <span>${level.get('price', 0):.2f}</span>
                            <span style="color: #ef4444;">+{level.get('distance_pct', 0):.1f}%</span>
                        </div>
        """
    
    html += """
                    </div>
                    <div>
                        <h4 style="color: #22c55e; margin-bottom: 10px;">🔻 支撐位</h4>
    """
    
    for level in support_levels:
        html += f"""
                        <div class="level-item support">
                            <span>${level.get('price', 0):.2f}</span>
                            <span style="color: #22c55e;">-{level.get('distance_pct', 0):.1f}%</span>
                        </div>
        """
    
    # 風險回報
    rr_ratio = risk_reward.get('risk_reward_ratio', 0)
    upside = risk_reward.get('potential_upside_pct', 0)
    downside = risk_reward.get('potential_downside_pct', 0)
    
    html += f"""
                    </div>
                </div>
                <div class="grid-3" style="margin-top: 15px;">
                    <div class="data-card">
                        <div class="data-label">風報比</div>
                        <div class="data-value">1:{rr_ratio}</div>
                    </div>
                    <div class="data-card">
                        <div class="data-label">潛在漲幅</div>
                        <div class="data-value bullish">+{upside}%</div>
                    </div>
                    <div class="data-card">
                        <div class="data-label">潛在跌幅</div>
                        <div class="data-value bearish">-{downside}%</div>
                    </div>
                </div>
            </div>
    """
    
    # 2. 分析戰報區塊
    score_class = 'score-a' if score >= 80 else 'score-b' if score >= 60 else 'score-c' if score >= 40 else 'score-d'
    
    html += f"""
            <div class="section checklist-section">
                <div class="section-title">
                    <span class="section-icon">📋</span> 綜合分析戰報
                </div>
                <div class="score-box">
                    <div class="data-label">綜合評分</div>
                    <div class="score-value {score_class}">{score}</div>
                </div>
    """
    
    for item in checklist:
        check_class = 'checked' if item.get('checked') else 'unchecked'
        check_icon = '✓' if item.get('checked') else '○'
        reason = item.get('reason', '')
        
        html += f"""
                <div class="checklist-item">
                    <span class="check-icon {check_class}">{check_icon}</span>
                    <span class="checklist-text">{item.get('text', '')}</span>
                    {f'<span class="checklist-reason">{reason}</span>' if reason else ''}
                </div>
        """
    
    html += f"""
                <div class="recommendation-box">
                    <strong>AI 交易建議：</strong> {recommendation}
                </div>
            </div>
    """
    
    # 3. 倉位風控區塊
    entry = risk_calc.get('entry_price', 0)
    stop = risk_calc.get('stop_loss', 0)
    target = risk_calc.get('target_price', 0)
    position = risk_calc.get('position_size', 0)
    rr = risk_calc.get('risk_reward_ratio', 0)
    
    html += f"""
            <div class="section risk-section">
                <div class="section-title">
                    <span class="section-icon">🎯</span> 倉位風控計算
                </div>
                <div class="grid-3">
                    <div class="data-card">
                        <div class="data-label">進場價</div>
                        <div class="data-value">${entry:.2f}</div>
                    </div>
                    <div class="data-card">
                        <div class="data-label">停損價</div>
                        <div class="data-value bearish">${stop:.2f}</div>
                    </div>
                    <div class="data-card">
                        <div class="data-label">目標價</div>
                        <div class="data-value bullish">${target:.2f}</div>
                    </div>
                </div>
                <div class="grid-2" style="margin-top: 15px;">
                    <div class="data-card">
                        <div class="data-label">建議張數</div>
                        <div class="data-value">{position} 股</div>
                    </div>
                    <div class="data-card">
                        <div class="data-label">損益比</div>
                        <div class="data-value">1 : {rr}</div>
                    </div>
                </div>
            </div>
    """
    
    # 4. 斐波那契區塊
    fib_high = fibonacci.get('high', 0)
    fib_low = fibonacci.get('low', 0)
    fib_382 = fibonacci.get('fib_382', 0)
    fib_500 = fibonacci.get('fib_500', 0)
    fib_618 = fibonacci.get('fib_618', 0)
    fib_trend = fibonacci.get('trend', 'uptrend')
    
    html += f"""
            <div class="section fib-section">
                <div class="section-title">
                    <span class="section-icon">📐</span> 斐波那契回撤 ({('上升趨勢' if fib_trend == 'uptrend' else '下降趨勢')})
                </div>
                <div class="grid-2">
                    <div class="data-card">
                        <div class="data-label">波段高點</div>
                        <div class="data-value">${fib_high:.2f}</div>
                    </div>
                    <div class="data-card">
                        <div class="data-label">波段低點</div>
                        <div class="data-value">${fib_low:.2f}</div>
                    </div>
                </div>
                <div class="grid-3" style="margin-top: 15px;">
                    <div class="data-card" style="border-left: 4px solid #22c55e;">
                        <div class="data-label">0.382 強勢</div>
                        <div class="data-value">${fib_382:.2f}</div>
                    </div>
                    <div class="data-card" style="border-left: 4px solid #f59e0b;">
                        <div class="data-label">0.500 中關</div>
                        <div class="data-value">${fib_500:.2f}</div>
                    </div>
                    <div class="data-card" style="border-left: 4px solid #ef4444;">
                        <div class="data-label">0.618 黃金</div>
                        <div class="data-value">${fib_618:.2f}</div>
                    </div>
                </div>
            </div>
    """
    
    # 5. 當沖判讀區塊
    range_high = intraday.get('range_high', 0)
    range_low = intraday.get('range_low', 0)
    intraday_current = intraday.get('current', 0)
    intraday_signal = intraday.get('signal', 'neutral')
    signal_text = intraday.get('signal_text', '中性盤整')
    long_target1 = intraday.get('long_target1', 0)
    long_stop = intraday.get('long_stop', 0)
    short_target1 = intraday.get('short_target1', 0)
    short_stop = intraday.get('short_stop', 0)
    
    signal_class = 'signal-bullish' if 'bullish' in intraday_signal else 'signal-bearish' if 'bearish' in intraday_signal else 'signal-neutral'
    
    html += f"""
            <div class="section intraday-section">
                <div class="section-title">
                    <span class="section-icon">⏱️</span> 當沖判讀
                </div>
                <div class="grid-3">
                    <div class="data-card">
                        <div class="data-label">15分鐘高點</div>
                        <div class="data-value bullish">${range_high:.2f}</div>
                    </div>
                    <div class="data-card">
                        <div class="data-label">15分鐘低點</div>
                        <div class="data-value bearish">${range_low:.2f}</div>
                    </div>
                    <div class="data-card">
                        <div class="data-label">現價</div>
                        <div class="data-value">${intraday_current:.2f}</div>
                    </div>
                </div>
                <div class="signal-box {signal_class}" style="margin-top: 15px;">
                    <strong style="font-size: 18px;">{signal_text}</strong>
                </div>
                <div class="grid-2" style="margin-top: 15px;">
                    <div class="data-card" style="border: 2px solid #ef4444;">
                        <div style="font-weight: bold; color: #ef4444; margin-bottom: 8px;">做多參考</div>
                        <div>目標: ${long_target1:.2f}</div>
                        <div style="color: #ef4444;">停損: ${long_stop:.2f}</div>
                    </div>
                    <div class="data-card" style="border: 2px solid #22c55e;">
                        <div style="font-weight: bold; color: #22c55e; margin-bottom: 8px;">做空參考</div>
                        <div>目標: ${short_target1:.2f}</div>
                        <div style="color: #22c55e;">停損: ${short_stop:.2f}</div>
                    </div>
                </div>
            </div>
    """
    
    # 6. 籌碼分析區塊 (如果有數據)
    if volume_profile:
        poc = volume_profile.get('poc', {}).get('price', 0)
        major_resistance = volume_profile.get('major_resistance', {}).get('price', 0)
        major_support = volume_profile.get('major_support', {}).get('price', 0)
        position_status = volume_profile.get('position_analysis', {}).get('status', '')
        
        html += f"""
            <div class="section vp-section">
                <div class="section-title">
                    <span class="section-icon">📊</span> 籌碼支撐壓力
                </div>
                <div class="grid-3">
                    <div class="data-card">
                        <div class="data-label">上方大量壓力</div>
                        <div class="data-value bullish">${major_resistance:.2f}</div>
                    </div>
                    <div class="data-card">
                        <div class="data-label">主控價位 (POC)</div>
                        <div class="data-value">${poc:.2f}</div>
                    </div>
                    <div class="data-card">
                        <div class="data-label">下方大量支撐</div>
                        <div class="data-value bearish">${major_support:.2f}</div>
                    </div>
                </div>
                <div class="signal-box signal-neutral" style="margin-top: 15px;">
                    {position_status}
                </div>
            </div>
        """
    
    # Footer
    html += """
            <div class="footer">
                <p>⚠️ 此報告僅供參考，投資一定有風險，請自行判斷</p>
                <p>AI 股票分析系統 | 自動生成報告</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html
