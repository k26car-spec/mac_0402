"""
週報生成器
生成訊號追蹤分析週報
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List
import os
import json

from app.services.signal_tracking_db import signal_tracking_db

logger = logging.getLogger(__name__)


class WeeklyReportGenerator:
    """週報生成器"""
    
    def __init__(self):
        self.db = signal_tracking_db
        self.report_dir = "/Users/Mac/Documents/ETF/AI/Ａi-catch/logs/reports"
        os.makedirs(self.report_dir, exist_ok=True)
    
    def generate_weekly_report(self) -> Dict:
        """生成週報"""
        
        # 計算本週期間
        today = datetime.now()
        end_date = today.replace(hour=23, minute=59, second=59)
        start_date = end_date - timedelta(days=7)
        
        # 獲取統計數據
        stats = self.db.get_statistics(days=7)
        
        if stats.get('total', 0) == 0:
            logger.warning("沒有足夠的數據生成週報")
            return {'success': False, 'message': '沒有足夠的數據'}
        
        # 生成建議
        recommendations = self._generate_recommendations(stats)
        
        # 組裝報告數據
        report_data = {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'total_signals': stats['total'],
            'total_rejected': stats['total'],
            'rejection_rate': 1.0,
            'correct_rejections': stats['correct_rejections'],
            'incorrect_rejections': stats['incorrect_rejections'],
            'ambiguous_decisions': stats['ambiguous'],
            'decision_accuracy': stats['accuracy'],
            'avg_missed_profit': 0,  # 需要從詳細數據計算
            'avg_avoided_loss': 0,
            'expected_value_if_entered': stats['avg_pnl_if_entered'],
            'net_benefit': -stats['avg_pnl_if_entered'],  # 負的期望值 = 正的淨效益
            'reason_stats': stats['reason_stats'],
            'recommendations': recommendations
        }
        
        # 保存到資料庫
        report_id = self.db.save_weekly_report(report_data)
        
        # 生成 HTML 報告
        html_file = self._generate_html_report(report_data)
        
        report_data['report_id'] = report_id
        report_data['html_file'] = html_file
        report_data['success'] = True
        
        logger.info(f"✅ 週報生成完成: {report_id}")
        
        return report_data
    
    def _generate_recommendations(self, stats: Dict) -> List[str]:
        """生成優化建議"""
        recommendations = []
        
        avg_pnl = stats.get('avg_pnl_if_entered', 0)
        accuracy = stats.get('accuracy', 0)
        
        # 整體評估
        if avg_pnl > 2.0:
            recommendations.append(
                f"⚠️ 系統可能過度保守：如果都進場，期望值為 +{avg_pnl:.2f}%，建議放寬限制"
            )
        elif avg_pnl < -2.0:
            recommendations.append(
                f"✅ 系統防守得當：避免了平均 {abs(avg_pnl):.2f}% 的虧損"
            )
        else:
            recommendations.append(
                f"🤷 系統處於平衡狀態：期望值接近 0 ({avg_pnl:+.2f}%)"
            )
        
        # 分原因分析
        for reason, reason_stats in stats.get('reason_stats', {}).items():
            ev = reason_stats.get('avg_pnl', 0)
            count = reason_stats.get('count', 0)
            acc = reason_stats.get('accuracy', 0)
            
            if ev > 3.0 and count >= 3:
                recommendations.append(
                    f"🔧 '{reason[:20]}...' 可能過嚴：{count} 筆中期望值 +{ev:.2f}%，建議調整閾值"
                )
            elif ev < -3.0 and acc > 0.7:
                recommendations.append(
                    f"✅ '{reason[:20]}...' 效果良好：避免 {abs(ev):.2f}% 虧損，準確率 {acc*100:.0f}%"
                )
        
        return recommendations
    
    def _generate_html_report(self, report_data: Dict) -> str:
        """生成 HTML 報告"""
        
        accuracy_color = '#2ecc71' if report_data['decision_accuracy'] > 0.7 else '#e74c3c'
        ev_color = '#2ecc71' if report_data['expected_value_if_entered'] < 0 else '#e74c3c'
        net_color = '#2ecc71' if report_data['net_benefit'] > 0 else '#e74c3c'
        
        # 拒絕原因統計表格
        reason_rows = ""
        for reason, stats in report_data.get('reason_stats', {}).items():
            pnl_class = 'positive' if stats['avg_pnl'] < 0 else 'negative'
            reason_rows += f"""
            <tr>
                <td>{reason[:30]}...</td>
                <td>{stats['count']}</td>
                <td class="{pnl_class}">{stats['avg_pnl']:+.2f}%</td>
                <td>{stats['accuracy']*100:.0f}%</td>
            </tr>
            """
        
        # 建議列表
        rec_html = ""
        for rec in report_data.get('recommendations', []):
            priority_class = 'high' if '⚠️' in rec else ('low' if '✅' in rec else 'medium')
            rec_html += f'<div class="recommendation {priority_class}">{rec}</div>\n'
        
        html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>交易系統追蹤週報 {report_data['start_date']} ~ {report_data['end_date']}</title>
    <style>
        body {{
            font-family: 'Microsoft JhengHei', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 2.5em;
            font-weight: bold;
        }}
        .metric-label {{
            font-size: 0.9em;
            opacity: 0.9;
            margin-top: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #3498db;
            color: white;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .positive {{ color: #27ae60; font-weight: bold; }}
        .negative {{ color: #e74c3c; font-weight: bold; }}
        .recommendation {{
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
        }}
        .recommendation.high {{
            background: #ffe6e6;
            border-left: 4px solid #e74c3c;
        }}
        .recommendation.medium {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
        }}
        .recommendation.low {{
            background: #d4edda;
            border-left: 4px solid #28a745;
        }}
        .summary-box {{
            background: #ecf0f1;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 交易系統追蹤週報</h1>
        <p>報告期間：{report_data['start_date']} ~ {report_data['end_date']}</p>
        <p>生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>📈 關鍵指標</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-value">{report_data['total_rejected']}</div>
                <div class="metric-label">拒絕訊號數</div>
            </div>
            <div class="metric-card" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);">
                <div class="metric-value">{report_data['decision_accuracy']*100:.1f}%</div>
                <div class="metric-label">決策準確率</div>
            </div>
            <div class="metric-card" style="background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);">
                <div class="metric-value">{report_data['expected_value_if_entered']:+.2f}%</div>
                <div class="metric-label">期望值（如都進場）</div>
            </div>
            <div class="metric-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
                <div class="metric-value">{report_data['net_benefit']:+.2f}%</div>
                <div class="metric-label">淨效益</div>
            </div>
        </div>
        
        <h2>📋 決策品質分析</h2>
        <div class="summary-box">
            <table>
                <tr>
                    <th>決策類型</th>
                    <th>數量</th>
                    <th>佔比</th>
                </tr>
                <tr>
                    <td>✅ 正確拒絕（避免虧損）</td>
                    <td>{report_data['correct_rejections']}</td>
                    <td>{report_data['correct_rejections']/max(report_data['total_rejected'],1)*100:.1f}%</td>
                </tr>
                <tr>
                    <td>❌ 錯誤拒絕（錯過獲利）</td>
                    <td>{report_data['incorrect_rejections']}</td>
                    <td>{report_data['incorrect_rejections']/max(report_data['total_rejected'],1)*100:.1f}%</td>
                </tr>
                <tr>
                    <td>🤷 模糊地帶</td>
                    <td>{report_data['ambiguous_decisions']}</td>
                    <td>{report_data['ambiguous_decisions']/max(report_data['total_rejected'],1)*100:.1f}%</td>
                </tr>
            </table>
        </div>
        
        <h2>🔍 拒絕原因分析</h2>
        <table>
            <tr>
                <th>拒絕原因</th>
                <th>次數</th>
                <th>平均損益</th>
                <th>準確率</th>
            </tr>
            {reason_rows}
        </table>
        
        <h2>💡 系統優化建議</h2>
        {rec_html}
        
        <hr style="margin: 40px 0;">
        <p style="color: #7f8c8d; text-align: center;">
            此報告由 AI Stock Intelligence 系統自動生成
        </p>
    </div>
</body>
</html>
        """
        
        # 保存 HTML 文件
        filename = f"weekly_report_{report_data['start_date'].replace('-', '')}_{report_data['end_date'].replace('-', '')}.html"
        filepath = os.path.join(self.report_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"HTML 報告已保存: {filepath}")
        
        return filepath


# 全局實例
weekly_reporter = WeeklyReportGenerator()
