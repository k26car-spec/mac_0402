import asyncio
import re
import json
import httpx
from datetime import datetime

html_file = "index.html"

etf_base_data = {
    '00981A': {
        'name': '統一台股增長', 'price': 27.80, 'change': '+4.43%', 'scale': '1,925 億', 'topWeight': '8.55%', 'vwap': '多頭鎖碼',
        'holdings': [
            {'id': '2330', 'name': '台積電', 'weight': 8.55, 'chips': '龍頭守護', 'tech': '高於週VWAP'},
            {'id': '2454', 'name': '聯發科', 'weight': 5.20, 'chips': '法人買超', 'tech': '築底起飛'},
            {'id': '2383', 'name': '台光電', 'weight': 4.80, 'chips': '主動認養', 'tech': '強勢噴發'},
            {'id': '3653', 'name': '健策', 'weight': 4.50, 'chips': '籌碼集中', 'tech': '高檔震盪'},
            {'id': '3017', 'name': '奇鋐', 'weight': 4.30, 'chips': 'AI伺服器', 'tech': '量增突破'},
            {'id': '2345', 'name': '智邦', 'weight': 4.10, 'chips': '投信連買', 'tech': '仰角攻擊'},
            {'id': '3324', 'name': '雙鴻', 'weight': 3.90, 'chips': '散熱大廠', 'tech': '盤整向上'},
            {'id': '2308', 'name': '台達電', 'weight': 3.50, 'chips': '長線佈局', 'tech': '突破頸線'},
            {'id': '2317', 'name': '鴻海', 'weight': 3.20, 'chips': '外資吸納', 'tech': '上升通道'},
            # ... 其餘省略
        ]
    },
    '00992A': {
        'name': '群益科技創新', 'price': 16.93, 'change': '+1.62%', 'scale': '468 億', 'topWeight': '20.00%', 'vwap': '權值撐盤',
        'holdings': [
            {'id': '2330', 'name': '台積電', 'weight': 20.00, 'chips': '法人加碼', 'tech': '高於週VWAP'},
            {'id': '6669', 'name': '緯穎', 'weight': 4.80, 'chips': '大戶鎖碼', 'tech': '多頭排列'},
            # ... 其餘省略
        ]
    },
    '0050': {
        'name': '元大台灣50', 'price': 195.0, 'change': '+1.2%', 'scale': '4,500 億', 'topWeight': '63.17%', 'vwap': '權值護盤',
        'holdings': [
            {'id': '2330', 'name': '台積電', 'weight': 63.17, 'chips': '外資認養', 'tech': '權值霸主'},
            {'id': '2308', 'name': '台達電', 'weight': 3.93, 'chips': '長線佈局', 'tech': '站穩均線'},
            {'id': '2454', 'name': '聯發科', 'weight': 3.23, 'chips': '法人卡位', 'tech': '底部翻揚'},
            {'id': '2317', 'name': '鴻海', 'weight': 3.14, 'chips': 'AI題材', 'tech': '季線反彈'},
            {'id': '3711', 'name': '日月光投控', 'weight': 1.58, 'chips': '封測領頭', 'tech': '帶量突破'},
            {'id': '2383', 'name': '台光電', 'weight': 1.50, 'chips': 'CCL龍頭', 'tech': '強勢格局'},
            {'id': '2891', 'name': '中信金', 'weight': 1.09, 'chips': '金融首選', 'tech': '穩定向上'},
            {'id': '3017', 'name': '奇鋐', 'weight': 1.11, 'chips': '散熱大廠', 'tech': '高檔震盪'},
            {'id': '2345', 'name': '智邦', 'weight': 1.10, 'chips': '交換器熱', 'tech': '仰角拉升'},
            {'id': '2382', 'name': '廣達', 'weight': 0.99, 'chips': '代工權值', 'tech': '季線支撐'},
            {'id': '2303', 'name': '聯電', 'weight': 0.90, 'chips': '低檔買盤', 'tech': '黃金交叉'},
            {'id': '2881', 'name': '富邦金', 'weight': 0.85, 'chips': '金融龍頭', 'tech': '穩定向上'},
            {'id': '2882', 'name': '國泰金', 'weight': 0.80, 'chips': '投信青睞', 'tech': '站回月線'},
            {'id': '2412', 'name': '中華電', 'weight': 0.75, 'chips': '避險資金專區', 'tech': '防禦守勢'},
            {'id': '5871', 'name': '中租-KY', 'weight': 0.70, 'chips': '獲利穩健', 'tech': '箱型震盪'},
            {'id': '2886', 'name': '兆豐金', 'weight': 0.65, 'chips': '官股穩盤', 'tech': '緩步墊高'},
            {'id': '1303', 'name': '南亞', 'weight': 0.60, 'chips': '基本面復甦', 'tech': '底部築底'},
            {'id': '2002', 'name': '中鋼', 'weight': 0.55, 'chips': '春燕回來了', 'tech': '反彈格局'},
            {'id': '1301', 'name': '台塑', 'weight': 0.50, 'chips': '集團佈局', 'tech': '低檔震盪'},
            {'id': '1216', 'name': '統一', 'weight': 0.45, 'chips': '法人認養', 'tech': '盤堅向上'},
            {'id': '2884', 'name': '玉山金', 'weight': 0.40, 'chips': '散戶最愛', 'tech': '均線糾結'},
            {'id': '2357', 'name': '華碩', 'weight': 0.35, 'chips': 'AI PC題材', 'tech': '帶量噴發'},
            {'id': '2892', 'name': '第一金', 'weight': 0.30, 'chips': '穩定配息', 'tech': '緩漲格局'},
            {'id': '2885', 'name': '元大金', 'weight': 0.30, 'chips': '證券龍頭', 'tech': '創波段高'},
            {'id': '2880', 'name': '華南金', 'weight': 0.25, 'chips': '資產品質佳', 'tech': '盤整向上'},
            {'id': '3045', 'name': '台灣大', 'weight': 0.25, 'chips': '現金流強', 'tech': '防禦標的'},
            {'id': '2887', 'name': '台新金', 'weight': 0.25, 'chips': '獲利成長', 'tech': '底部起漲'},
            {'id': '2890', 'name': '永豐金', 'weight': 0.25, 'chips': '基本面強', 'tech': '多頭格局'},
            {'id': '3008', 'name': '大立光', 'weight': 0.25, 'chips': '潛望鏡紅利', 'tech': '打底完成'},
            {'id': '3037', 'name': '欣興', 'weight': 0.20, 'chips': '載板龍頭', 'tech': '低位反彈'},
            {'id': '3034', 'name': '聯詠', 'weight': 0.20, 'chips': '毛利回升', 'tech': '震盪上行'},
            {'id': '2395', 'name': '研華', 'weight': 0.15, 'chips': '工業控制', 'tech': '緩步墊高'},
            {'id': '2379', 'name': '瑞昱', 'weight': 0.15, 'chips': '網通強勢', 'tech': '挑戰新高'},
            {'id': '3231', 'name': '緯創', 'weight': 0.15, 'chips': 'AI代工', 'tech': '破底翻紅'},
            {'id': '2474', 'name': '可成', 'weight': 0.15, 'chips': '現金充沛', 'tech': '定存股首選'},
            {'id': '4904', 'name': '遠傳', 'weight': 0.10, 'chips': '電信三強', 'tech': '防守格局'},
            {'id': '5876', 'name': '上海商銀', 'weight': 0.10, 'chips': '利差優勢', 'tech': '低檔震盪'},
            {'id': '4938', 'name': '和碩', 'weight': 0.10, 'chips': '組裝大廠', 'tech': '緩步墊高'},
            {'id': '8046', 'name': '南電', 'weight': 0.10, 'chips': 'ABF回溫', 'tech': '底部成型'},
            {'id': '6488', 'name': '環球晶', 'weight': 0.10, 'chips': '矽晶圓熱', 'tech': '回測5日線'},
            {'id': '2408', 'name': '南亞科', 'weight': 0.10, 'chips': 'DRAM漲價', 'tech': '橫向整理'},
            {'id': '2301', 'name': '光寶科', 'weight': 0.10, 'chips': '雲端題材', 'tech': '回測季線'},
            {'id': '9910', 'name': '豐泰', 'weight': 0.10, 'chips': '消費復甦', 'tech': '打底區'},
            {'id': '9904', 'name': '寶成', 'weight': 0.10, 'chips': '低價龍頭', 'tech': '突破平台'},
            {'id': '2101', 'name': '南港', 'weight': 0.10, 'chips': '資產概念', 'tech': '強勢格局'},
            {'id': '2356', 'name': '英業達', 'weight': 0.05, 'chips': '伺服器熱', 'tech': '高檔震盪'},
            {'id': '2347', 'name': '聯強', 'weight': 0.05, 'chips': '通路王', 'tech': '高息保護'},
            {'id': '2324', 'name': '仁寶', 'weight': 0.05, 'chips': '投信低接', 'tech': '緩漲格局'},
            {'id': '2353', 'name': '宏碁', 'weight': 0.05, 'chips': 'PC復甦', 'tech': '震盪築底'},
            {'id': '9921', 'name': '巨大', 'weight': 0.05, 'chips': '自行車龍頭', 'tech': '庫存去化'},
            {'id': '6505', 'name': '台塑化', 'weight': 0.05, 'chips': '油價支撐', 'tech': '跌深反彈'},
            {'id': '1101', 'name': '台泥', 'weight': 0.03, 'chips': '綠能佈局', 'tech': '底部成型'},
            {'id': '2883', 'name': '凱基金', 'weight': 0.02, 'chips': '金控佈局', 'tech': '站穩月線'},
            {'id': '2207', 'name': '和泰車', 'weight': 0.02, 'chips': '車市龍頭', 'tech': '緩步墊高'}
        ]
    }
}
# ... 其餘抓取與寫入邏輯 ...
