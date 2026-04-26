"""
產業新聞 PDF 報告生成器
自動生成每日產業新聞摘要 PDF 並發送郵件
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# PDF 生成依賴
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    logger.warning("reportlab 未安裝，無法生成 PDF")


class NewsReportGenerator:
    """產業新聞 PDF 報告生成器"""
    
    def __init__(self):
        self.output_dir = Path("/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3/reports/news")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 嘗試註冊中文字體
        self._register_fonts()
    
    def _register_fonts(self):
        """註冊中文字體"""
        if not HAS_REPORTLAB:
            return
        
        # macOS 上優先使用的繁體中文字體列表
        font_paths = [
            # macOS 驗證存在的字體
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
            # 用戶安裝的字體
            "/Library/Fonts/Microsoft JhengHei.ttf",
            "/Library/Fonts/Noto Sans CJK TC Regular.otf",
            # Homebrew 安裝的字體
            "/opt/homebrew/share/fonts/microsoft/msjh.ttf",
        ]
        
        self.has_chinese_font = False
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    # 對於 .ttc 集合字體，嘗試使用 subfontIndex
                    if font_path.endswith('.ttc'):
                        pdfmetrics.registerFont(TTFont('ChineseFont', font_path, subfontIndex=0))
                    else:
                        pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                    
                    self.has_chinese_font = True
                    logger.info(f"成功註冊中文字體: {font_path}")
                    return
                except Exception as e:
                    logger.debug(f"字體註冊失敗 {font_path}: {e}")
                    continue
        
        logger.warning("無法註冊中文字體，PDF 中的中文可能顯示為方框")
    
    def generate_news_summary(self, news_data: Dict) -> Dict:
        """
        生成新聞重點摘要
        將新聞整理成易讀的重點格式
        """
        all_news = news_data.get('news', {}).get('all', [])
        recommendations = news_data.get('recommendations', [])
        
        # 按產業分類新聞
        industry_news = {}
        for news in all_news:
            industry = news.get('industry', '其他')
            if industry not in industry_news:
                industry_news[industry] = []
            industry_news[industry].append(news)
        
        # 生成產業重點
        industry_highlights = {}
        for industry, news_list in industry_news.items():
            highlights = []
            for news in news_list[:5]:  # 每個產業最多5則
                title = news.get('title', '')
                sentiment = news.get('sentiment', 'neutral')
                
                # 提取重點 (移除冗餘，保留核心資訊)
                highlight = self._extract_highlight(title)
                if highlight:
                    highlights.append({
                        'text': highlight,
                        'sentiment': sentiment,
                        'stocks': news.get('stocks', [])
                    })
            
            if highlights:
                industry_highlights[industry] = highlights
        
        # 生成投資重點
        investment_focus = []
        for rec in recommendations[:10]:
            if rec.get('action') in ['強力關注', '值得關注']:
                investment_focus.append({
                    'symbol': rec['symbol'],
                    'name': rec['name'],
                    'action': rec['action'],
                    'score': rec['score'],
                    'reason': rec.get('relatedNews', [''])[0] if rec.get('relatedNews') else ''
                })
        
        # 獲取漲停板資料和相關新聞 (新增)
        limit_up_stocks = []
        limit_down_stocks = []
        near_limit_up_stocks = []
        limit_up_news = []  # 漲停板相關新聞
        
        try:
            import asyncio
            from app.services.limit_stock_monitor import limit_stock_monitor
            
            # 使用新事件循環或現有循環
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 在已有事件循環中，使用 Thread
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        def run_async():
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            try:
                                # 獲取完整動能報告（包含新聞）
                                return new_loop.run_until_complete(limit_stock_monitor.get_daily_momentum_report())
                            finally:
                                new_loop.close()
                        future = executor.submit(run_async)
                        momentum_report = future.result(timeout=60)
                else:
                    momentum_report = loop.run_until_complete(limit_stock_monitor.get_daily_momentum_report())
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                momentum_report = loop.run_until_complete(limit_stock_monitor.get_daily_momentum_report())
            
            if momentum_report.get('success'):
                limit_up_stocks = momentum_report.get('limitUp', [])
                limit_down_stocks = momentum_report.get('limitDown', [])
                near_limit_up_stocks = momentum_report.get('nearLimitUp', [])
                limit_up_news = momentum_report.get('relatedNews', [])
                logger.info(f"漲停板資料: 漲停 {len(limit_up_stocks)} 檔, 相關新聞 {len(limit_up_news)} 則")
        except Exception as e:
            logger.warning(f"獲取漲停板資料失敗: {e}")
        
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'timestamp': datetime.now().isoformat(),
            'total_news': len(all_news),
            'industry_highlights': industry_highlights,
            'investment_focus': investment_focus,
            'market_mood': self._analyze_market_mood(all_news),
            'limit_up_stocks': limit_up_stocks,
            'limit_down_stocks': limit_down_stocks,
            'near_limit_up_stocks': near_limit_up_stocks,
            'limit_up_news': limit_up_news,  # 新增漲停板相關新聞
        }
    
    def _extract_highlight(self, title: str) -> str:
        """從標題提取重點"""
        # 移除常見的冗餘詞彙
        remove_words = ['報導', '指出', '表示', '認為', '分析']
        result = title
        for word in remove_words:
            result = result.replace(word, '')
        
        # 如果標題太長，截取前 40 個字
        if len(result) > 40:
            result = result[:40] + '...'
        
        return result.strip()
    
    def _analyze_market_mood(self, news_list: List[Dict]) -> Dict:
        """分析市場情緒"""
        positive = sum(1 for n in news_list if n.get('sentiment') == 'positive')
        negative = sum(1 for n in news_list if n.get('sentiment') == 'negative')
        neutral = sum(1 for n in news_list if n.get('sentiment') == 'neutral')
        
        total = len(news_list) if news_list else 1
        
        if positive > negative * 1.5:
            mood = "樂觀"
            emoji = "📈"
        elif negative > positive * 1.5:
            mood = "謹慎"
            emoji = "📉"
        else:
            mood = "中性"
            emoji = "➖"
        
        return {
            'mood': mood,
            'emoji': emoji,
            'positive_pct': round(positive / total * 100, 1),
            'negative_pct': round(negative / total * 100, 1),
            'neutral_pct': round(neutral / total * 100, 1)
        }
    
    def generate_pdf_report(self, news_data: Dict) -> Optional[str]:
        """生成 PDF 報告"""
        if not HAS_REPORTLAB:
            logger.error("reportlab 未安裝，無法生成 PDF")
            return None
        
        summary = self.generate_news_summary(news_data)
        
        # 生成檔案名稱
        date_str = datetime.now().strftime('%Y%m%d')
        filename = f"daily_news_report_{date_str}.pdf"
        filepath = self.output_dir / filename
        
        try:
            doc = SimpleDocTemplate(
                str(filepath),
                pagesize=A4,
                rightMargin=15*mm,
                leftMargin=15*mm,
                topMargin=15*mm,
                bottomMargin=15*mm
            )
            
            # 樣式
            styles = getSampleStyleSheet()
            
            # 使用中文字體（不繼承父樣式的字體）
            title_style = ParagraphStyle(
                'ChineseTitle',
                fontName='ChineseFont',
                fontSize=18,
                spaceAfter=12,
                alignment=1,  # 置中
                textColor=colors.darkblue
            )
            normal_style = ParagraphStyle(
                'ChineseNormal',
                fontName='ChineseFont',
                fontSize=10,
                leading=14
            )
            heading_style = ParagraphStyle(
                'ChineseHeading',
                fontName='ChineseFont',
                fontSize=14,
                spaceAfter=8,
                textColor=colors.darkblue,
                spaceBefore=10
            )
            
            # 內容
            content = []
            
            # 標題 (不使用 emoji)
            content.append(Paragraph(
                f"每日產業新聞重點 - {summary['date']}",
                title_style
            ))
            content.append(Spacer(1, 10))
            
            # 市場情緒
            mood = summary['market_mood']
            mood_text = "上升" if mood['mood'] == '樂觀' else "下降" if mood['mood'] == '謹慎' else "持平"
            content.append(Paragraph(
                f"今日市場情緒: {mood['mood']} ({mood_text}) - "
                f"正面 {mood['positive_pct']}% / 負面 {mood['negative_pct']}%",
                normal_style
            ))
            content.append(Spacer(1, 15))
            
            # 漲停板訊息 (新增)
            if summary.get('limit_up_stocks'):
                content.append(Paragraph("今日漲停板", heading_style))
                
                limit_table_data = [['代碼', '名稱', '收盤價', '漲幅%', '市場']]
                for stock in summary['limit_up_stocks'][:10]:
                    limit_table_data.append([
                        Paragraph(stock.get('code', ''), normal_style),
                        Paragraph(stock.get('name', ''), normal_style),
                        Paragraph(f"${stock.get('close', 0):.2f}", normal_style),
                        Paragraph(f"+{stock.get('changePct', 0):.1f}%", normal_style),
                        Paragraph(stock.get('market', 'TWSE'), normal_style),
                    ])
                
                limit_table = Table(limit_table_data, colWidths=[50, 70, 70, 55, 55])
                limit_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.pink),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.darkred),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTNAME', (0, 0), (-1, 0), 'ChineseFont'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                content.append(limit_table)
                content.append(Spacer(1, 5))
                
                content.append(Paragraph(
                    f"漲停: {len(summary.get('limit_up_stocks', []))} 檔 | "
                    f"跌停: {len(summary.get('limit_down_stocks', []))} 檔 | "
                    f"接近漲停: {len(summary.get('near_limit_up_stocks', []))} 檔",
                    normal_style
                ))
                content.append(Spacer(1, 10))
                
                # 漲停板相關新聞 (新增)
                if summary.get('limit_up_news'):
                    content.append(Paragraph("漲停板相關新聞", heading_style))
                    for news in summary['limit_up_news'][:8]:
                        title = news.get('title', '')
                        if len(title) > 50:
                            title = title[:50] + '...'
                        source = news.get('source', '')
                        # 顯示相關股票
                        related = news.get('relatedStocks', [])
                        related_str = ''
                        if related:
                            related_str = f" [{', '.join(s.get('name', s.get('code', '')) for s in related[:3])}]"
                        content.append(Paragraph(
                            f"  {title}{related_str} - {source}",
                            normal_style
                        ))
                    content.append(Spacer(1, 15))
            
            # 投資重點
            if summary['investment_focus']:
                content.append(Paragraph("今日關注股票", heading_style))
                
                table_data = [['代碼', '名稱', '關注度', '分數', '原因']]
                for stock in summary['investment_focus'][:8]:
                    reason_text = stock.get('reason', '')
                    if len(reason_text) > 20:
                        reason_text = reason_text[:20] + '...'
                    table_data.append([
                        Paragraph(stock['symbol'], normal_style),
                        Paragraph(stock['name'], normal_style),
                        Paragraph(stock['action'], normal_style),
                        Paragraph(str(stock['score']), normal_style),
                        Paragraph(reason_text, normal_style)
                    ])
                
                table = Table(table_data, colWidths=[45, 55, 65, 45, 155])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.darkblue),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTNAME', (0, 0), (-1, 0), 'ChineseFont'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                content.append(table)
                content.append(Spacer(1, 15))
            
            # 產業重點
            content.append(Paragraph("產業新聞重點", heading_style))
            
            for industry, highlights in summary['industry_highlights'].items():
                content.append(Paragraph(f"【{industry}】", normal_style))
                for h in highlights[:3]:
                    sentiment_mark = "[+]" if h['sentiment'] == 'positive' else "[-]" if h['sentiment'] == 'negative' else "[o]"
                    stock_str = f" ({', '.join(h['stocks'][:2])})" if h['stocks'] else ""
                    content.append(Paragraph(
                        f"  {sentiment_mark} {h['text']}{stock_str}",
                        normal_style
                    ))
                content.append(Spacer(1, 8))
            
            # 頁尾
            content.append(Spacer(1, 20))
            content.append(Paragraph(
                f"報告生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                normal_style
            ))
            content.append(Paragraph(
                "資料來源: IEK 產業情報網 (https://ieknet.iek.org.tw)",
                normal_style
            ))
            
            # 生成 PDF
            doc.build(content)
            logger.info(f"PDF 報告生成成功: {filepath}")
            
            return str(filepath)
            
        except Exception as e:
            logger.error(f"生成 PDF 失敗: {e}")
            return None
    
    def generate_text_report(self, news_data: Dict) -> str:
        """生成純文字報告 (用於郵件內文)"""
        summary = self.generate_news_summary(news_data)
        
        lines = []
        lines.append(f"📰 每日產業新聞重點 - {summary['date']}")
        lines.append("=" * 50)
        lines.append("")
        
        # 市場情緒
        mood = summary['market_mood']
        lines.append(f"{mood['emoji']} 今日市場情緒: {mood['mood']}")
        lines.append(f"   正面 {mood['positive_pct']}% | 負面 {mood['negative_pct']}% | 中性 {mood['neutral_pct']}%")
        lines.append("")
        
        # 漲停板訊息 (新增)
        if summary.get('limit_up_stocks'):
            lines.append("🔥 今日漲停板")
            lines.append("-" * 40)
            lines.append(f"   漲停: {len(summary.get('limit_up_stocks', []))} 檔 | 跌停: {len(summary.get('limit_down_stocks', []))} 檔")
            for stock in summary['limit_up_stocks'][:8]:
                lines.append(f"  • {stock.get('code')} {stock.get('name')} - ${stock.get('close'):.2f} (+{stock.get('changePct'):.1f}%)")
            
            # 漲停板相關新聞 (新增)
            if summary.get('limit_up_news'):
                lines.append("")
                lines.append("📰 漲停板相關新聞")
                for news in summary['limit_up_news'][:6]:
                    title = news.get('title', '')
                    if len(title) > 45:
                        title = title[:45] + '...'
                    source = news.get('source', '')
                    lines.append(f"  • {title} ({source})")
            lines.append("")
        
        # 投資重點
        lines.append("🎯 今日關注股票")
        lines.append("-" * 40)
        for stock in summary['investment_focus'][:8]:
            lines.append(f"  • {stock['symbol']} {stock['name']} - {stock['action']} (分數:{stock['score']})")
            if stock.get('reason'):
                lines.append(f"    └ {stock['reason'][:30]}...")
        lines.append("")
        
        # 產業重點
        lines.append("🏭 產業新聞重點")
        lines.append("-" * 40)
        for industry, highlights in summary['industry_highlights'].items():
            lines.append(f"\n【{industry}】")
            for h in highlights[:3]:
                emoji = "📈" if h['sentiment'] == 'positive' else "📉" if h['sentiment'] == 'negative' else "•"
                lines.append(f"  {emoji} {h['text']}")
        
        lines.append("")
        lines.append("=" * 50)
        lines.append(f"報告時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("資料來源: IEK 產業情報網")
        
        return "\n".join(lines)


# 全域實例
news_report_generator = NewsReportGenerator()


def generate_daily_news_report() -> Dict:
    """生成每日新聞報告 (PDF + 文字)"""
    from app.services.news_analysis_service import news_analysis_service
    
    # 取得新聞分析
    news_data = news_analysis_service.get_all_news_with_analysis()
    
    # 生成報告
    pdf_path = news_report_generator.generate_pdf_report(news_data)
    text_report = news_report_generator.generate_text_report(news_data)
    summary = news_report_generator.generate_news_summary(news_data)
    
    return {
        'success': True,
        'date': summary['date'],
        'pdf_path': pdf_path,
        'text_report': text_report,
        'summary': summary
    }


def send_daily_news_email() -> Dict:
    """發送每日新聞報告郵件"""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders
    
    # 生成報告
    report = generate_daily_news_report()
    
    if not report['success']:
        return {'success': False, 'error': '報告生成失敗'}
    
    # Email 設定 - 使用固定配置
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    username = 'k26car@gmail.com'
    password = 'zrgogmielnvpykrv'  # Gmail 應用程式密碼
    recipients = ['k26car@gmail.com', 'neimou1225@gmail.com']
    
    if not username or not password or not recipients:
        logger.warning("郵件設定不完整，跳過發送")
        return {'success': False, 'error': '郵件設定不完整'}
    
    try:
        # 建立郵件
        msg = MIMEMultipart()
        msg['From'] = username
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = f"📰 每日產業新聞重點 - {report['date']}"
        
        # 郵件內文
        msg.attach(MIMEText(report['text_report'], 'plain', 'utf-8'))
        
        # 附加 PDF
        if report['pdf_path'] and os.path.exists(report['pdf_path']):
            with open(report['pdf_path'], 'rb') as f:
                pdf_attachment = MIMEBase('application', 'pdf')
                pdf_attachment.set_payload(f.read())
                encoders.encode_base64(pdf_attachment)
                pdf_attachment.add_header(
                    'Content-Disposition',
                    f'attachment; filename="daily_news_{report["date"]}.pdf"'
                )
                msg.attach(pdf_attachment)
        
        # 發送
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
        
        logger.info(f"✅ 新聞報告郵件發送成功: {recipients}")
        return {'success': True, 'recipients': recipients, 'pdf_path': report['pdf_path']}
        
    except Exception as e:
        logger.error(f"郵件發送失敗: {e}")
        return {'success': False, 'error': str(e)}
