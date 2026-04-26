"""
配置文件 - 循環驅動多因子投資系統
請填入您的 API 金鑰
"""

# FRED API 金鑰
# 從 https://fred.stlouisfed.org/docs/api/api_key.html 免費取得
FRED_API_KEY = ""

# Alpha Vantage API 金鑰（可選）
# 從 https://www.alphavantage.co/ 取得
ALPHA_VANTAGE_API = ""

# 數據更新設定
UPDATE_FREQUENCY = "monthly"  # monthly, weekly, daily
SAVE_REPORTS = True
SAVE_CHARTS = True

# 圖表樣式
CHART_STYLE = "seaborn-v0_8-darkgrid"

# 報告輸出目錄
REPORTS_DIR = "reports"
CHARTS_DIR = "charts"

# 權重參數（可根據需求調整）
WEIGHTS = {
    'pmi': 0.30,
    'yield_curve': 0.25,
    'unemployment': 0.15,
    'inflation': 0.15,
    'gdp_growth': 0.15
}

# 風險警告閾值
THRESHOLDS = {
    'pmi_warning': 48,
    'pmi_critical': 45,
    'yield_curve_warning': 0,
    'yield_curve_critical': -0.5,
    'inflation_warning': 4.0,
    'inflation_critical': 5.0,
    'unemployment_warning': 5.0,
    'unemployment_critical': 6.0
}
