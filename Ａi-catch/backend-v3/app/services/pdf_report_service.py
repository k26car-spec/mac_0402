"""
PDF 報告生成服務
生成 A4 格式的股票分析報告
"""

import io
import os
import uuid
import json
from datetime import datetime
from typing import Dict, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# 嘗試註冊中文字體
CHINESE_FONT_NAME = 'Helvetica'  # 預設字體

try:
    # 嘗試使用 CID 字體 (更可靠)
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    CHINESE_FONT_NAME = 'STSong-Light'
except Exception:
    try:
        # macOS 系統字體路徑
        font_paths = [
            '/System/Library/Fonts/Hiragino Sans GB.ttc',
            '/System/Library/Fonts/PingFang.ttc',
            '/System/Library/Fonts/STHeiti Light.ttc',
            '/Library/Fonts/Arial Unicode.ttf',
        ]
        for path in font_paths:
            if os.path.exists(path):
                try:
                    pdfmetrics.registerFont(TTFont('ChineseFont', path, subfontIndex=0))
                    CHINESE_FONT_NAME = 'ChineseFont'
                    break
                except:
                    continue
    except Exception:
        pass

# 報告儲存路徑
REPORTS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

# 儲存報告資料 (用於分享連結)
REPORTS_CACHE: Dict[str, Dict] = {}


def get_chinese_font():
    """取得中文字體名稱"""
    return CHINESE_FONT_NAME


def create_styles():
    """建立樣式"""
    styles = getSampleStyleSheet()
    font_name = get_chinese_font()
    
    styles.add(ParagraphStyle(
        name='ChineseTitle',
        fontName=font_name,
        fontSize=24,
        leading=30,
        alignment=1,  # 置中
        spaceAfter=20,
        textColor=colors.HexColor('#1a365d'),
    ))
    
    styles.add(ParagraphStyle(
        name='ChineseHeading',
        fontName=font_name,
        fontSize=14,
        leading=18,
        spaceBefore=15,
        spaceAfter=8,
        textColor=colors.HexColor('#2d3748'),
    ))
    
    styles.add(ParagraphStyle(
        name='ChineseBody',
        fontName=font_name,
        fontSize=10,
        leading=14,
        spaceAfter=6,
        textColor=colors.HexColor('#4a5568'),
    ))
    
    styles.add(ParagraphStyle(
        name='ChineseSmall',
        fontName=font_name,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#718096'),
    ))
    
    return styles


def create_table_style(header_color, has_split_header=False):
    """建立表格樣式，包含中文字體設定"""
    font_name = get_chinese_font()
    base_style = [
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f7fafc')),
    ]
    
    if not has_split_header:
        base_style.insert(0, ('BACKGROUND', (0, 0), (-1, 0), header_color))
    
    return TableStyle(base_style)


def generate_stock_report_pdf(analysis_data: Dict) -> tuple[bytes, str]:
    """
    生成股票分析 PDF 報告 (單張 A4)
    
    Returns:
        tuple: (PDF bytes, report_id)
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.2*cm,
        leftMargin=1.2*cm,
        topMargin=1*cm,
        bottomMargin=0.8*cm
    )
    
    styles = create_styles()
    story = []
    font_name = get_chinese_font()
    
    stock_code = analysis_data.get('stock_code', 'N/A')
    stock_name = analysis_data.get('stock_name', 'N/A')
    overall_score = analysis_data.get('overall_score', 0)
    recommendation = analysis_data.get('recommendation', 'N/A')
    target_price = analysis_data.get('target_price', 0)
    stop_loss = analysis_data.get('stop_loss', 0)
    ti = analysis_data.get('technical_indicators', {})
    fh = analysis_data.get('financial_health', {})
    inst = analysis_data.get('institutional_trading', {})
    
    current_price = ti.get('current_price', 0) if ti else 0
    change_pct = ti.get('change_pct', 0) if ti else 0
    
    # 緊湊型表格樣式
    def compact_style(header_color):
        return TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('BACKGROUND', (0, 0), (-1, 0), header_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d0d0')),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fafafa')),
        ])
    
    # ===== 標題區 =====
    title_style = ParagraphStyle(
        'CompactTitle', fontName=font_name, fontSize=18, leading=22,
        alignment=1, textColor=colors.HexColor('#1a365d')
    )
    story.append(Paragraph(f"{stock_code} {stock_name} AI分析報告", title_style))
    
    time_style = ParagraphStyle(
        'TimeStyle', fontName=font_name, fontSize=7, alignment=1,
        textColor=colors.HexColor('#888888')
    )
    story.append(Paragraph(f"報告時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}", time_style))
    
    # ===== 異常股票警示 =====
    try:
        from app.services.twse_abnormal_api import check_stock_abnormal
        is_abnormal, reasons = check_stock_abnormal(stock_code)
        if is_abnormal:
            warning_style = ParagraphStyle(
                'WarningStyle', fontName=font_name, fontSize=9, alignment=1,
                textColor=colors.HexColor('#dc2626'), spaceBefore=4, spaceAfter=4
            )
            warning_text = f"[!] 警示: {', '.join(reasons)}"
            story.append(Paragraph(warning_text, warning_style))
    except Exception:
        pass
    
    story.append(Spacer(1, 8))
    
    # ===== 核心指標 (一行顯示) =====
    change_color = '#dc2626' if change_pct >= 0 else '#16a34a'
    rec_bg = '#dc2626' if recommendation in ['強力買進', '買進'] else '#16a34a' if recommendation in ['賣出', '減碼'] else '#f59e0b'
    
    core_data = [[
        f"股價: ${current_price:.2f}",
        f"漲跌: {change_pct:+.2f}%",
        f"評分: {overall_score}/100",
        f"建議: {recommendation}",
        f"目標: ${target_price:.2f}",
        f"停損: ${stop_loss:.2f}"
    ]]
    
    core_table = Table(core_data, colWidths=[2.8*cm, 2.3*cm, 2.5*cm, 2.5*cm, 2.8*cm, 2.8*cm])
    core_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f9ff')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#3b82f6')),
    ]))
    story.append(core_table)
    story.append(Spacer(1, 8))
    
    # ===== 技術分析區 (MA + 壓力支撐合併) =====
    if ti:
        section_style = ParagraphStyle(
            'Section', fontName=font_name, fontSize=10, leading=12,
            textColor=colors.HexColor('#1e40af'), spaceBefore=4, spaceAfter=3
        )
        story.append(Paragraph("[技術分析]", section_style))
        
        # MA 均線 + 壓力支撐合併為一個表格
        tech_data = [
            ['MA5', 'MA10', 'MA20', 'MA60', '壓力1', '壓力2', '支撐1', '支撐2'],
            [
                f"${ti.get('ma5', 0):.1f}",
                f"${ti.get('ma10', 0):.1f}",
                f"${ti.get('ma20', 0):.1f}",
                f"${ti.get('ma60', 0):.1f}",
                f"${ti.get('resistance_1', 0):.1f}",
                f"${ti.get('resistance_2', 0):.1f}",
                f"${ti.get('support_1', 0):.1f}",
                f"${ti.get('support_2', 0):.1f}",
            ]
        ]
        
        tech_table = Table(tech_data, colWidths=[2.1*cm] * 8)
        tech_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (3, 0), colors.HexColor('#22c55e')),
            ('BACKGROUND', (4, 0), (5, 0), colors.HexColor('#ef4444')),
            ('BACKGROUND', (6, 0), (7, 0), colors.HexColor('#22c55e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d0d0')),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fafafa')),
        ]))
        story.append(tech_table)
        
        # 趨勢文字 (多行顯示)
        trend_style = ParagraphStyle(
            'TrendStyle', fontName=font_name, fontSize=8, leading=10,
            textColor=colors.HexColor('#374151')
        )
        
        # 均線排列
        trend_text = f"排列: {ti.get('ma_arrangement', 'N/A')} | {ti.get('ma_signal', 'N/A')} | {ti.get('ma_trend', 'N/A')}"
        story.append(Paragraph(trend_text, trend_style))
        
        # RSI、MACD、趨勢
        rsi = ti.get('rsi_14', 50)
        macd = ti.get('macd', 0)
        trend = ti.get('trend', 'N/A')
        
        # RSI 判斷
        if rsi > 70:
            rsi_status = "超買"
        elif rsi < 30:
            rsi_status = "超賣"
        else:
            rsi_status = "中性"
        
        # MACD 判斷
        macd_status = "多方" if macd > 0 else "空方" if macd < 0 else "中性"
        
        indicator_text = f"RSI(14): {rsi:.1f} ({rsi_status}) | MACD: {macd:.2f} ({macd_status}) | 趨勢: {trend}"
        story.append(Paragraph(indicator_text, trend_style))
        story.append(Spacer(1, 6))
    
    # ===== 量價分析 (NEW) =====
    vpa = analysis_data.get('volume_price_analysis')
    if vpa:
        story.append(Paragraph("[量價分析]", section_style))
        
        trend_dir = vpa.get('trend_direction', '')
        trend_map = {'bullish': '看漲', 'bearish': '看跌', 'sideways': '盤整'}
        trend_text = trend_map.get(trend_dir, '盤整')
        
        confirm = vpa.get('volume_price_confirmation', '')
        confirm_signal = vpa.get('confirmation_signal', '')
        confirm_map = {'bullish_confirmation': '多方確認', 'bearish_confirmation': '空方確認', 'caution': '警示', 'neutral': '中性'}
        signal_text = confirm_map.get(confirm_signal, '中性')
        
        predicted = vpa.get('predicted_direction', '')
        predict_map = {'up': '↑上漲', 'down': '↓下跌', 'sideways': '→盤整'}
        predict_text = predict_map.get(predicted, '盤整')
        
        volume_ratio = vpa.get('volume_ratio', 1)
        confidence = vpa.get('trend_confidence', 0)
        
        vpa_data = [
            ['趨勢方向', '量價確認', '訊號強度', '量比', '預測方向', '置信度'],
            [
                trend_text,
                confirm,
                signal_text,
                f"{volume_ratio:.2f}",
                predict_text,
                f"{confidence:.0f}%",
            ]
        ]
        
        vpa_table = Table(vpa_data, colWidths=[2.8*cm] * 6)
        vpa_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0891b2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d0d0')),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0fdfa')),
        ]))
        story.append(vpa_table)
        
        # 背離訊號
        divergence = vpa.get('divergence_detected', False)
        if divergence:
            div_type = vpa.get('divergence_type', '')
            div_desc = vpa.get('divergence_description', '')
            div_style = ParagraphStyle(
                'DivStyle', fontName=font_name, fontSize=8, leading=10,
                textColor=colors.HexColor('#dc2626')
            )
            story.append(Paragraph(f"⚠ 背離訊號: {div_type} - {div_desc}", div_style))
        
        # 關鍵訊號
        key_signals = vpa.get('key_signals', [])
        if key_signals:
            signals_text = "關鍵訊號: " + " | ".join(key_signals[:3])
            story.append(Paragraph(signals_text, trend_style))
        
        story.append(Spacer(1, 6))
    
    # ===== 財務 + 法人合併 =====
    if fh or inst:
        story.append(Paragraph("[財務健康] & [法人籌碼]", section_style))
        
        combined_data = [
            ['ROE', 'EPS', '毛利率', '負債比', '外資', '投信', '自營商', '合計'],
            [
                f"{fh.get('roe', 0):.1f}%" if fh else '-',
                f"${fh.get('eps', 0):.2f}" if fh else '-',
                f"{fh.get('gross_margin', 0):.1f}%" if fh else '-',
                f"{fh.get('debt_ratio', 0):.1f}%" if fh else '-',
                f"{inst.get('foreign_net', 0):,}" if inst else '-',
                f"{inst.get('trust_net', 0):,}" if inst else '-',
                f"{inst.get('dealer_net', 0):,}" if inst else '-',
                f"{inst.get('total_net', 0):,}" if inst else '-',
            ]
        ]
        
        combined_table = Table(combined_data, colWidths=[2.1*cm] * 8)
        combined_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (3, 0), colors.HexColor('#8b5cf6')),
            ('BACKGROUND', (4, 0), (7, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d0d0')),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fafafa')),
        ]))
        story.append(combined_table)
        
        # 法人趨勢分析
        try:
            from app.services.stock_event_service import get_institutional_analysis
            inst_analysis = get_institutional_analysis(stock_code, inst or {})
            trend = inst_analysis.get('trend', '')
            strength = inst_analysis.get('strength', '')
            if trend:
                inst_trend_text = f"法人動向: {trend} (力道: {strength})"
                story.append(Paragraph(inst_trend_text, trend_style))
        except Exception:
            pass
        
        story.append(Spacer(1, 6))
    
    # ===== 重要日期事件 =====
    try:
        from app.services.stock_event_service import get_stock_events
        events = get_stock_events(stock_code)
        
        if events:
            story.append(Paragraph("[重要日期]", section_style))
            
            event_style = ParagraphStyle(
                'EventStyle', fontName=font_name, fontSize=7, leading=9,
                textColor=colors.HexColor('#374151')
            )
            
            # 月營收公告
            revenue_date = events.get('next_revenue_date', '')
            last_month = events.get('last_revenue_month', '')
            if revenue_date:
                story.append(Paragraph(f"月營收: {last_month}已公告，下次公告: {revenue_date}", event_style))
            
            # 季財報
            quarterly = events.get('next_quarterly_report', {})
            if quarterly:
                story.append(Paragraph(f"季財報: {quarterly.get('quarter', '')} 財報截止日: {quarterly.get('deadline', '')}", event_style))
            
            # 除權息
            dividend = events.get('dividend', {})
            if dividend and dividend.get('dividend_yield', 0) > 0:
                story.append(Paragraph(f"殖利率: {dividend.get('dividend_yield', 0):.2f}% | 年度股利: ${dividend.get('annual_dividend', 0):.2f}", event_style))
            
            story.append(Spacer(1, 6))
    except Exception:
        pass
    
    # ===== 法人籌碼分析 (NEW) =====
    chip_analysis = analysis_data.get('chip_analysis')
    if chip_analysis:
        story.append(Paragraph("[法人籌碼分析]", section_style))
        
        futures = chip_analysis.get('futures', {})
        margin = chip_analysis.get('margin', {})
        summary = chip_analysis.get('summary', {})
        continuous = chip_analysis.get('continuous', {})
        
        # 綜合態度
        overall_stance = summary.get('overall_stance', '中性')
        total_score = summary.get('total_score', 0)
        
        chip_summary_style = ParagraphStyle(
            'ChipSummary', fontName=font_name, fontSize=9, leading=11,
            textColor=colors.HexColor('#1e40af')
        )
        
        score_sign = '+' if total_score > 0 else ''
        story.append(Paragraph(f"籌碼態度: {overall_stance} (綜合分數: {score_sign}{total_score})", chip_summary_style))
        
        # 期貨選擇權 + 融資融券表格
        chip_data = [
            ['外資期貨淨部位', 'P/C Ratio', '外資態度', '散戶情緒', '融資變化', '融券變化'],
            [
                f"{futures.get('foreign_futures_net', 0):+,} 口",
                f"{futures.get('pc_ratio', 0):.2f}",
                futures.get('foreign_stance', 'N/A'),
                margin.get('retail_sentiment', 'N/A'),
                f"{margin.get('margin_change_ratio', 0):+.2f}%",
                f"{margin.get('short_change_ratio', 0):+.2f}%",
            ]
        ]
        
        chip_table = Table(chip_data, colWidths=[2.8*cm, 2.0*cm, 2.5*cm, 2.5*cm, 2.3*cm, 2.3*cm])
        chip_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d0d0')),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#faf5ff')),
        ]))
        story.append(chip_table)
        
        # 個股法人連續買賣超
        if continuous:
            foreign_cont = continuous.get('foreign', {})
            invest_cont = continuous.get('investment', {})
            dealer_cont = continuous.get('dealer', {})
            
            cont_style = ParagraphStyle(
                'ContStyle', fontName=font_name, fontSize=7, leading=9,
                textColor=colors.HexColor('#374151')
            )
            
            def format_cont(name, data):
                if not data or not data.get('direction'):
                    return f"{name}: 無連續"
                direction = "買超" if data['direction'] == 'buy' else "賣超"
                return f"{name}: 連續{direction}{data.get('days', 0)}天"
            
            cont_text = f"{format_cont('外資', foreign_cont)} | {format_cont('投信', invest_cont)} | {format_cont('自營商', dealer_cont)}"
            story.append(Paragraph(cont_text, cont_style))
        
        story.append(Spacer(1, 6))
    
    # ===== 買入/賣出訊號 & 風險警示 =====
    buy_signals = analysis_data.get('buy_signals', [])
    sell_signals = analysis_data.get('sell_signals', [])
    risk_warnings = analysis_data.get('risk_warnings', [])
    
    if buy_signals or sell_signals or risk_warnings:
        signal_style = ParagraphStyle(
            'SignalStyle', fontName=font_name, fontSize=7, leading=9,
            textColor=colors.HexColor('#374151')
        )
        
        # 買入訊號
        if buy_signals:
            story.append(Paragraph(f"[+] 買入訊號 ({len(buy_signals)})", section_style))
            for sig in buy_signals[:2]:
                name = sig.get('name', '')
                desc = sig.get('description', '')[:40]
                conf = sig.get('confidence', 0)
                story.append(Paragraph(f"  + {name}: {desc}... (信心:{conf}%)", signal_style))
            story.append(Spacer(1, 3))
        
        # 賣出訊號
        if sell_signals:
            story.append(Paragraph(f"[-] 賣出訊號 ({len(sell_signals)})", section_style))
            for sig in sell_signals[:2]:
                name = sig.get('name', '')
                desc = sig.get('description', '')[:40]
                conf = sig.get('confidence', 0)
                story.append(Paragraph(f"  - {name}: {desc}... (信心:{conf}%)", signal_style))
            story.append(Spacer(1, 3))
        
        # 風險警示
        if risk_warnings:
            story.append(Paragraph(f"[!] 風險警示 ({len(risk_warnings)})", section_style))
            for warn in risk_warnings[:2]:
                name = warn.get('name', '')
                desc = warn.get('description', '')[:50]
                story.append(Paragraph(f"  • {name}: {desc}", signal_style))
            story.append(Spacer(1, 3))
    
    # ===== 相關新聞 (附超連結) =====
    news = analysis_data.get('related_news', [])
    if news and len(news) > 0:
        story.append(Paragraph("[相關新聞] 點擊標題可開啟連結", section_style))
        
        # 一般新聞樣式
        news_style = ParagraphStyle(
            'NewsStyle', fontName=font_name, fontSize=8, leading=10,
            textColor=colors.HexColor('#374151')
        )
        
        # 帶連結的新聞樣式
        news_link_style = ParagraphStyle(
            'NewsLinkStyle', fontName=font_name, fontSize=8, leading=10,
            textColor=colors.HexColor('#2563eb')  # 藍色表示可點擊
        )
        
        # 顯示全部新聞
        for i, item in enumerate(news, 1):
            title = item.get('title', '') if isinstance(item, dict) else str(item)
            sentiment = item.get('sentiment', 'neutral') if isinstance(item, dict) else 'neutral'
            date = item.get('date', '') if isinstance(item, dict) else ''
            url = item.get('url', '') if isinstance(item, dict) else ''
            source = item.get('source', '') if isinstance(item, dict) else ''
            
            sentiment_icon = '[+]' if sentiment == 'positive' else '[-]' if sentiment == 'negative' else '[o]'
            
            # 標題限制長度
            short_title = title[:42] + '...' if len(title) > 42 else title
            
            # 來源和日期資訊
            info_parts = []
            if source:
                info_parts.append(source)
            if date:
                info_parts.append(date)
            info_str = f" ({', '.join(info_parts)})" if info_parts else ""
            
            # 如果有 URL，使用超連結格式
            if url and url.startswith('http'):
                # ReportLab 超連結語法: <link href="url">text</link>
                news_text = f'{i}. {sentiment_icon} <link href="{url}" color="blue"><u>{short_title}</u></link>{info_str}'
                story.append(Paragraph(news_text, news_link_style))
            else:
                news_text = f"{i}. {sentiment_icon} {short_title}{info_str}"
                story.append(Paragraph(news_text, news_style))
        
        story.append(Spacer(1, 6))
    
    # ===== AI 摘要 =====
    ai_summary = analysis_data.get('ai_summary', '')
    if ai_summary:
        story.append(Paragraph("[AI] 分析摘要", section_style))
        
        summary_style = ParagraphStyle(
            'SummaryStyle', fontName=font_name, fontSize=9, leading=12,
            textColor=colors.HexColor('#1f2937'), leftIndent=5, rightIndent=5
        )
        # 限制摘要長度
        short_summary = ai_summary[:250] + '...' if len(ai_summary) > 250 else ai_summary
        story.append(Paragraph(short_summary, summary_style))
        story.append(Spacer(1, 6))
    
    # ===== 頁尾 =====
    footer_style = ParagraphStyle(
        'Footer', fontName=font_name, fontSize=6, alignment=1,
        textColor=colors.HexColor('#9ca3af')
    )
    story.append(Paragraph(
        f"本報告由 AI 股票分析系統自動生成，僅供參考。© {datetime.now().year}",
        footer_style
    ))
    
    # 生成 PDF
    doc.build(story)
    
    # 生成報告 ID 並儲存
    report_id = str(uuid.uuid4())[:8]
    REPORTS_CACHE[report_id] = {
        'data': analysis_data,
        'created_at': datetime.now().isoformat(),
        'stock_code': stock_code,
        'stock_name': stock_name,
    }
    
    # 儲存 PDF 檔案
    pdf_bytes = buffer.getvalue()
    pdf_path = os.path.join(REPORTS_DIR, f'{report_id}.pdf')
    with open(pdf_path, 'wb') as f:
        f.write(pdf_bytes)
    
    # 儲存 JSON 資料
    json_path = os.path.join(REPORTS_DIR, f'{report_id}.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(analysis_data, f, ensure_ascii=False, indent=2, default=str)
    
    return pdf_bytes, report_id


def generate_genz_report_pdf(analysis_data: Dict) -> tuple[bytes, str]:
    """
    生成 GenZ 風格投資懶人包 PDF 報告
    
    特色：
    - 表情符號表達情緒
    - 口語化翻譯專業術語
    - 給新手的實用建議
    
    Returns:
        tuple: (PDF bytes, report_id)
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.2*cm,
        bottomMargin=1*cm
    )
    
    styles = create_styles()
    story = []
    font_name = get_chinese_font()
    
    # 取得資料
    stock_code = analysis_data.get('stock_code', 'N/A')
    stock_name = analysis_data.get('stock_name', 'N/A')
    overall_score = analysis_data.get('overall_score', 0)
    recommendation = analysis_data.get('recommendation', 'N/A')
    target_price = analysis_data.get('target_price', 0)
    stop_loss = analysis_data.get('stop_loss', 0)
    ti = analysis_data.get('technical_indicators', {})
    fh = analysis_data.get('financial_health', {})
    inst = analysis_data.get('institutional_trading', {})
    ai_summary = analysis_data.get('ai_summary', '')
    
    current_price = ti.get('current_price', 0) if ti else 0
    change_pct = ti.get('change_pct', 0) if ti else 0
    
    # ===== 1. 判斷主要表情符號 =====
    if overall_score >= 75:
        main_emoji = "🔥"
        mood = "這支超強的！"
        mood_color = '#dc2626'
    elif overall_score >= 60:
        main_emoji = "👍"
        mood = "表現還不錯"
        mood_color = '#16a34a'
    elif overall_score >= 45:
        main_emoji = "😐"
        mood = "普普通通..."
        mood_color = '#f59e0b'
    else:
        main_emoji = "💩"
        mood = "建議先觀望"
        mood_color = '#6b7280'
    
    # ===== 2. 口語化翻譯 =====
    roe = fh.get('roe', 0) if fh else 0
    if roe > 20:
        roe_comment = "🏎️ 賺錢速度像法拉利！"
    elif roe > 15:
        roe_comment = "🚗 賺錢速度不錯喔"
    elif roe > 10:
        roe_comment = "🚴 賺錢速度像騎腳踏車"
    elif roe > 0:
        roe_comment = "🐢 賺錢速度有點慢..."
    else:
        roe_comment = "🦥 在虧錢欸..."
    
    # 法人評價
    total_net = inst.get('total_net', 0) if inst else 0
    foreign_net = inst.get('foreign_net', 0) if inst else 0
    if total_net > 5000:
        inst_comment = "🐋 大戶狂買中！"
    elif total_net > 1000:
        inst_comment = "📈 大戶在買"
    elif total_net > 0:
        inst_comment = "🤔 大戶小買"
    elif total_net > -1000:
        inst_comment = "🤷 大戶小賣"
    elif total_net > -5000:
        inst_comment = "📉 大戶在跑"
    else:
        inst_comment = "🏃 大戶狂賣逃命中！"
    
    # PE 評價
    pe = fh.get('pe_ratio', 0) if fh else 0
    if pe <= 0:
        pe_comment = "虧損中，沒本益比"
    elif pe < 10:
        pe_comment = "便宜到翻！"
    elif pe < 15:
        pe_comment = "價格合理"
    elif pe < 25:
        pe_comment = "有點貴了"
    else:
        pe_comment = "貴鬆鬆！"
    
    # 趨勢評價
    trend = ti.get('trend', '盤整') if ti else '盤整'
    if trend == "多頭":
        trend_emoji = "📈"
        trend_comment = "走勢向上，趁現在！"
    elif trend == "空頭":
        trend_emoji = "📉"
        trend_comment = "走勢向下，小心接刀..."
    else:
        trend_emoji = "➡️"
        trend_comment = "盤整中，等待方向"
    
    # ===== 開始建構 PDF =====
    
    # 標題
    title_style = ParagraphStyle(
        'GenZTitle', fontName=font_name, fontSize=22, leading=28,
        alignment=1, textColor=colors.HexColor(mood_color)
    )
    story.append(Paragraph(f"{stock_name} ({stock_code}) 投資懶人包 {main_emoji}", title_style))
    
    # 副標題
    subtitle_style = ParagraphStyle(
        'GenZSubtitle', fontName=font_name, fontSize=12, alignment=1,
        textColor=colors.HexColor('#6b7280'), spaceBefore=4, spaceAfter=10
    )
    story.append(Paragraph(f"生成時間: {datetime.now().strftime('%Y/%m/%d %H:%M')} | 小白專用版", subtitle_style))
    
    story.append(Spacer(1, 10))
    
    # ===== 核心評分大框 =====
    score_box_color = colors.HexColor('#fef3c7') if overall_score >= 60 else colors.HexColor('#fee2e2') if overall_score < 45 else colors.HexColor('#f3f4f6')
    
    score_data = [[
        Paragraph(f"<b>綜合分數</b><br/><font size='24'>{overall_score:.0f}</font> 分", 
                  ParagraphStyle('ScoreNum', fontName=font_name, fontSize=12, alignment=1)),
        Paragraph(f"<b>AI 建議</b><br/><font size='14'>{recommendation}</font><br/><font size='10' color='gray'>{mood}</font>",
                  ParagraphStyle('ScoreRec', fontName=font_name, fontSize=12, alignment=1)),
        Paragraph(f"<b>目前股價</b><br/>${current_price:.2f}<br/><font color='{('#dc2626' if change_pct >= 0 else '#16a34a')}'>{change_pct:+.2f}%</font>",
                  ParagraphStyle('ScorePrice', fontName=font_name, fontSize=12, alignment=1)),
    ]]
    
    score_table = Table(score_data, colWidths=[5.5*cm, 5.5*cm, 5.5*cm])
    score_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, -1), score_box_color),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOX', (0, 0), (-1, -1), 2, colors.HexColor(mood_color)),
        ('INNERGRID', (0, 0), (-1, -1), 1, colors.HexColor('#d1d5db')),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 15))
    
    # ===== 為什麼這樣評？ =====
    section_style = ParagraphStyle(
        'GenZSection', fontName=font_name, fontSize=14, leading=18,
        textColor=colors.HexColor('#1f2937'), spaceBefore=10, spaceAfter=6
    )
    story.append(Paragraph("🧐 為什麼這樣評？", section_style))
    
    reason_style = ParagraphStyle(
        'GenZReason', fontName=font_name, fontSize=11, leading=16,
        textColor=colors.HexColor('#374151'), leftIndent=10
    )
    
    # 賺錢能力
    story.append(Paragraph(f"1️⃣ 賺錢能力 (ROE: {roe:.1f}%)", reason_style))
    story.append(Paragraph(f"   → {roe_comment}", reason_style))
    
    # 股價貴不貴
    story.append(Paragraph(f"2️⃣ 股價貴不貴 (本益比: {pe:.1f}倍)", reason_style))
    story.append(Paragraph(f"   → {pe_comment}", reason_style))
    
    # 大戶動向
    story.append(Paragraph(f"3️⃣ 大戶/法人動向 (淨買超: {total_net:+,}張)", reason_style))
    story.append(Paragraph(f"   → {inst_comment}", reason_style))
    
    # 技術趨勢
    story.append(Paragraph(f"4️⃣ 技術趨勢 {trend_emoji}", reason_style))
    story.append(Paragraph(f"   → {trend_comment}", reason_style))
    
    story.append(Spacer(1, 15))
    
    # ===== 如果你真的手癢想買... =====
    story.append(Paragraph("💰 如果你真的手癢想買...", section_style))
    
    support_1 = ti.get('support_1', stop_loss) if ti else stop_loss
    
    action_style = ParagraphStyle(
        'GenZAction', fontName=font_name, fontSize=12, leading=18,
        textColor=colors.HexColor('#1e40af'), leftIndent=10
    )
    
    warning_style = ParagraphStyle(
        'GenZWarning', fontName=font_name, fontSize=12, leading=18,
        textColor=colors.HexColor('#dc2626'), leftIndent=10
    )
    
    story.append(Paragraph(f"✅ 建議進場價：${support_1:.2f} 附近 (接近支撐位)", action_style))
    story.append(Paragraph(f"🎯 目標價位：${target_price:.2f} (可以考慮獲利了結)", action_style))
    story.append(Paragraph(f"🛑 嚴格停損：跌破 ${stop_loss:.2f} 就跑！別捨不得！", warning_style))
    
    story.append(Spacer(1, 15))
    
    # ===== 一分鐘看懂技術面 =====
    story.append(Paragraph("📊 一分鐘看懂技術面", section_style))
    
    # 簡化版技術指標
    rsi = ti.get('rsi_14', 50) if ti else 50
    macd = ti.get('macd', 0) if ti else 0
    
    if rsi > 70:
        rsi_text = f"RSI: {rsi:.0f} 🔥 超熱！可能要休息一下"
    elif rsi < 30:
        rsi_text = f"RSI: {rsi:.0f} 🥶 超冷！可能有反彈機會"
    else:
        rsi_text = f"RSI: {rsi:.0f} 😌 正常範圍"
    
    if macd > 0:
        macd_text = f"MACD: {macd:.2f} 📈 多方控場中"
    else:
        macd_text = f"MACD: {macd:.2f} 📉 空方暫時佔優"
    
    tech_simple_style = ParagraphStyle(
        'TechSimple', fontName=font_name, fontSize=11, leading=15,
        textColor=colors.HexColor('#374151'), leftIndent=10
    )
    story.append(Paragraph(rsi_text, tech_simple_style))
    story.append(Paragraph(macd_text, tech_simple_style))
    story.append(Paragraph(f"均線排列：{ti.get('ma_arrangement', 'N/A') if ti else 'N/A'}", tech_simple_style))
    
    story.append(Spacer(1, 15))
    
    # ===== AI 真心話 =====
    story.append(Paragraph("🤖 AI 真心話", section_style))
    
    ai_style = ParagraphStyle(
        'GenZAI', fontName=font_name, fontSize=11, leading=16,
        textColor=colors.HexColor('#4b5563'), leftIndent=10, rightIndent=10,
        borderColor=colors.HexColor('#e5e7eb'), borderWidth=1,
        borderPadding=10, backColor=colors.HexColor('#f9fafb')
    )
    
    # 如果有 AI 摘要就用，沒有就生成一個
    if ai_summary:
        ai_text = ai_summary[:300] + '...' if len(ai_summary) > 300 else ai_summary
    else:
        if overall_score >= 70:
            ai_text = f"這支 {stock_name} 各方面表現都不錯！基本面穩健、技術面偏多、法人也在買。如果你有閒錢想投資，可以考慮分批進場。但記得設好停損，投資一定有風險！"
        elif overall_score >= 50:
            ai_text = f"{stock_name} 目前表現還可以，不算特別好也不算太差。建議再觀察一下，等到有更明確的訊號再進場會比較安全。新手可以先放入觀察名單。"
        else:
            ai_text = f"{stock_name} 目前各項指標都不太理想，建議先不要碰。等基本面改善、技術面轉強再來考慮。記住：沒有買就沒有虧！"
    
    story.append(Paragraph(ai_text, ai_style))
    
    story.append(Spacer(1, 15))
    
    # ===== 新手必讀小提醒 =====
    story.append(Paragraph("📚 新手必讀小提醒", section_style))
    
    tip_style = ParagraphStyle(
        'GenZTip', fontName=font_name, fontSize=9, leading=13,
        textColor=colors.HexColor('#6b7280'), leftIndent=10
    )
    
    tips = [
        "• 永遠不要把所有錢都投進一支股票（雞蛋不要放同一個籃子）",
        "• 設好停損點，跌破就賣，不要凹單或攤平",
        "• 投資是長期的事，不要每天盯盤搞得自己很焦慮",
        "• 這份報告是 AI 分析，僅供參考，最終決定還是要自己做",
        "• 不懂的股票不要買，先學習再投資"
    ]
    
    for tip in tips:
        story.append(Paragraph(tip, tip_style))
    
    story.append(Spacer(1, 20))
    
    # ===== 頁尾 =====
    footer_style = ParagraphStyle(
        'GenZFooter', fontName=font_name, fontSize=7, alignment=1,
        textColor=colors.HexColor('#9ca3af')
    )
    story.append(Paragraph(
        f"本報告由 AI 股票分析系統自動生成 | 投資有風險，入市需謹慎 | © {datetime.now().year}",
        footer_style
    ))
    
    # 生成 PDF
    doc.build(story)
    
    # 生成報告 ID 並儲存
    report_id = f"genz_{str(uuid.uuid4())[:8]}"
    REPORTS_CACHE[report_id] = {
        'data': analysis_data,
        'created_at': datetime.now().isoformat(),
        'stock_code': stock_code,
        'stock_name': stock_name,
        'report_type': 'genz'
    }
    
    # 儲存 PDF 檔案
    pdf_bytes = buffer.getvalue()
    pdf_path = os.path.join(REPORTS_DIR, f'{report_id}.pdf')
    with open(pdf_path, 'wb') as f:
        f.write(pdf_bytes)
    
    return pdf_bytes, report_id


def get_report_by_id(report_id: str) -> Optional[Dict]:
    # 先從快取查詢
    if report_id in REPORTS_CACHE:
        return REPORTS_CACHE[report_id]['data']
    
    # 從檔案讀取
    json_path = os.path.join(REPORTS_DIR, f'{report_id}.json')
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return None


def get_pdf_by_id(report_id: str) -> Optional[bytes]:
    """根據 ID 取得 PDF 檔案"""
    pdf_path = os.path.join(REPORTS_DIR, f'{report_id}.pdf')
    if os.path.exists(pdf_path):
        with open(pdf_path, 'rb') as f:
            return f.read()
    return None
