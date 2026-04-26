#!/usr/bin/env python3
"""測試新聞報告生成"""
from app.services.news_report_generator import generate_daily_news_report

print("開始生成新聞報告...")
report = generate_daily_news_report()

print("=== 新聞報告生成結果 ===")
print(f"成功: {report.get('success')}")
print(f"PDF路徑: {report.get('pdf_path')}")
print()

summary = report.get('summary', {})
print(f"漲停股: {len(summary.get('limit_up_stocks', []))} 檔")
print(f"漲停相關新聞: {len(summary.get('limit_up_news', []))} 則")
print()

print("=== 漲停板相關新聞 ===")
for news in summary.get('limit_up_news', [])[:5]:
    title = news.get('title', '')[:40]
    source = news.get('source', '')
    print(f"  - {title}... ({source})")
