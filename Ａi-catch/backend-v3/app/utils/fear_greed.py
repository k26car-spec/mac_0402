"""
Fear & Greed Index 整合
使用 Alternative.me 提供的免費API
"""

import requests
import logging

logger = logging.getLogger(__name__)


def get_fear_greed_index():
    """
    獲取CNN Fear & Greed Index
    使用 alternative.me 提供的免費API (加密貨幣市場)
    
    返回值: 0-100
    - 0-24: Extreme Fear
    - 25-49: Fear
    - 50-74: Greed
    - 75-100: Extreme Greed
    """
    try:
        # Alternative.me Crypto Fear & Greed Index (免費，無需API key)
        url = "https://api.alternative.me/fng/"
        
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if data.get('data') and len(data['data']) > 0:
            value = int(data['data'][0].get('value', 50))
            classification = data['data'][0].get('value_classification', 'Neutral')
            
            logger.info(f"✅ Fear & Greed Index: {value} ({classification})")
            return value
        else:
            logger.warning("⚠️ Fear & Greed API返回空數據")
            return 50
            
    except Exception as e:
        logger.error(f"獲取Fear & Greed Index錯誤: {e}")
        return 50  # 返回中性值


# 測試
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    index = get_fear_greed_index()
    print(f"Fear & Greed Index: {index}")
