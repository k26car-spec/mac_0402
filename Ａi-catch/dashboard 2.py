#!/usr/bin/env python3
# dashboard.py - AI主力監控平台

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import sqlite3
import json
from datetime import datetime, timedelta
import threading
import os
import subprocess
import logging

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # 啟用 CORS，允許跨域請求

# 導入富邦搜尋 API
try:
    from fubon_search_api import search_stocks
    FUBON_SEARCH_AVAILABLE = True
except ImportError:
    FUBON_SEARCH_AVAILABLE = False
    logger.warning("富邦搜尋 API 未可用")

class StockMonitorDashboard:
    def __init__(self, db_path='data/stock_monitor.db'):
        self.db_path = db_path
        self.monitor_process = None
        self.monitor_status = 'stopped'
        self.last_check = None
        
    def get_db_connection(self):
        """獲取資料庫連接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_system_status(self):
        """獲取系統狀態"""
        # 檢查進程是否在運行
        is_running = self.check_monitor_running()
        
        status = {
            'monitor_status': 'running' if is_running else 'stopped',
            'last_check': self.get_last_log_time(),
            'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_trading_time': self._is_trading_time(),
            'total_alerts': self.get_total_alerts(),
            'today_alerts': len(self.get_today_alerts())
        }
        return status
    
    def check_monitor_running(self):
        """檢查監控進程是否在運行"""
        try:
            result = subprocess.run(
                ['ps', 'aux'], 
                capture_output=True, 
                text=True
            )
            return 'stock_monitor.py' in result.stdout
        except:
            return False
    
    def get_last_log_time(self):
        """從日誌獲取最後檢查時間"""
        try:
            with open('logs/stock_monitor.log', 'r') as f:
                lines = f.readlines()
                if lines:
                    last_line = lines[-1]
                    # 提取時間戳 (格式: 2024-12-12 00:03:09,...)
                    time_str = last_line.split(' - ')[0] if ' - ' in last_line else ''
                    return time_str[:19] if len(time_str) >= 19 else '--:--'
        except:
            pass
        return '--:--'
    
    def _is_trading_time(self):
        """判斷是否為交易時間"""
        now = datetime.now()
        weekday = now.weekday()
        hour = now.hour
        minute = now.minute
        
        if 0 <= weekday <= 4:  # 週一至週五
            if (9 <= hour < 13) or (hour == 13 and minute <= 30):
                return True
        return False
    
    def get_total_alerts(self):
        """獲取總警示數"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM stock_alerts')
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0
    
    def get_today_alerts(self):
        """獲取今日警示"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT * FROM stock_alerts 
                WHERE DATE(timestamp) = ?
                ORDER BY timestamp DESC
            ''', (today,))
            alerts = cursor.fetchall()
            conn.close()
            
            result = []
            for alert in alerts:
                result.append({
                    'id': alert[0],
                    'stock_code': alert[1],
                    'alert_type': alert[2],
                    'confidence': float(alert[3]),
                    'timestamp': alert[5],
                    'notified': bool(alert[6])
                })
            return result
        except Exception as e:
            logger.error(f"獲取今日警示錯誤: {e}")
            return []
    
    def get_recent_alerts(self, limit=20):
        """獲取最近警示"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM stock_alerts 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            alerts = cursor.fetchall()
            conn.close()
            
            result = []
            for alert in alerts:
                try:
                    features = json.loads(alert[4]) if alert[4] else {}
                except:
                    features = {}
                    
                result.append({
                    'id': alert[0],
                    'stock_code': alert[1],
                    'alert_type': alert[2],
                    'confidence': float(alert[3]),
                    'timestamp': alert[5],
                    'features': features
                })
            return result
        except Exception as e:
            logger.error(f"獲取最近警示錯誤: {e}")
            return []
    
    def get_stock_list(self):
        """獲取監控清單"""
        try:
            import yaml
            with open('config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config['watchlist']['stocks']
        except:
            return ["2330.TW", "2317.TW", "2454.TW"]
    
    def start_monitoring(self):
        """啟動監控"""
        try:
            # 檢查是否已在運行
            if self.check_monitor_running():
                return {'success': False, 'message': '監控已在運行中'}
            
            # 在背景啟動監控
            subprocess.Popen(
                ['python3', 'stock_monitor.py'],
                stdout=open('logs/monitor_output.log', 'w'),
                stderr=subprocess.STDOUT
            )
            
            self.monitor_status = 'running'
            self.last_check = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return {'success': True, 'message': '監控已啟動'}
        except Exception as e:
            logger.error(f"啟動監控錯誤: {e}")
            return {'success': False, 'message': str(e)}
    
    def stop_monitoring(self):
        """停止監控"""
        try:
            # 使用 pkill 停止進程
            subprocess.run(['pkill', '-f', 'stock_monitor.py'])
            
            self.monitor_status = 'stopped'
            
            return {'success': True, 'message': '監控已停止'}
        except Exception as e:
            logger.error(f"停止監控錯誤: {e}")
            return {'success': False, 'message': str(e)}
    
    def add_stock(self, stock_code):
        """添加股票到監控清單"""
        try:
            import yaml
            
            with open('config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if stock_code not in config['watchlist']['stocks']:
                config['watchlist']['stocks'].append(stock_code)
                
                with open('config.yaml', 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
                
                return True
            return False
        except Exception as e:
            logger.error(f"添加股票錯誤: {e}")
            return False
    
    def remove_stock(self, stock_code):
        """從監控清單移除股票"""
        try:
            import yaml
            
            with open('config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if stock_code in config['watchlist']['stocks']:
                config['watchlist']['stocks'].remove(stock_code)
                
                with open('config.yaml', 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
                
                return True
            return False
        except Exception as e:
            logger.error(f"移除股票錯誤: {e}")
            return False

# 初始化監控器
monitor = StockMonitorDashboard()

# Flask 路由
@app.route('/')
def index():
    """主頁面"""
    return render_template('dashboard.html')

@app.route('/premarket')
def premarket():
    """開盤前5分鐘精準選股系統"""
    return render_template('premarket.html')

@app.route('/api/status')
def get_status():
    """獲取系統狀態 API"""
    return jsonify(monitor.get_system_status())

@app.route('/api/alerts/today')
def get_today_alerts():
    """獲取今日警示 API"""
    return jsonify(monitor.get_today_alerts())

@app.route('/api/alerts/recent')
def get_recent_alerts():
    """獲取最近警示 API"""
    return jsonify(monitor.get_recent_alerts())

@app.route('/api/stocks')
def get_stocks():
    """獲取監控清單 API"""
    stocks = monitor.get_stock_list()
    
    # 為每支股票添加中文名稱
    stock_data = []
    try:
        from stock_names import get_stock_name, get_full_name
        for stock_code in stocks:
            stock_data.append({
                'code': stock_code,
                'name': get_stock_name(stock_code),
                'full_name': get_full_name(stock_code)
            })
    except:
        # 如果獲取名稱失敗，只返回代碼
        stock_data = [{'code': s, 'name': s, 'full_name': s} for s in stocks]
    
    return jsonify({'stocks': stock_data})

@app.route('/api/monitor/start', methods=['POST'])
def start_monitor():
    """啟動監控 API"""
    result = monitor.start_monitoring()
    return jsonify(result)

@app.route('/api/monitor/stop', methods=['POST'])
def stop_monitor():
    """停止監控 API"""
    result = monitor.stop_monitoring()
    return jsonify(result)

@app.route('/api/stocks/add', methods=['POST'])
def add_stock():
    """添加股票 API"""
    data = request.json
    stock_code = data.get('stock_code', '').strip()
    
    if not stock_code:
        return jsonify({'success': False, 'message': '股票代號不能為空'})
    
    success = monitor.add_stock(stock_code)
    return jsonify({
        'success': success, 
        'message': '添加成功' if success else '股票已存在或添加失敗'
    })

@app.route('/api/stocks/remove', methods=['POST'])
def remove_stock():
    """移除股票 API"""
    try:
        data = request.json
        logger.info(f"收到刪除請求，原始數據: {data}, 類型: {type(data)}")
        
        if not data:
            return jsonify({'success': False, 'message': '無效的請求數據'}), 400
        
        # 處理 stock_code 可能是字典或字串的情況
        stock_code_raw = data.get('stock_code', '')
        logger.info(f"stock_code_raw: {stock_code_raw}, 類型: {type(stock_code_raw)}")
        
        # 如果是字典，嘗試提取 code 或 fullCode
        if isinstance(stock_code_raw, dict):
            stock_code = stock_code_raw.get('code') or stock_code_raw.get('fullCode') or ''
        else:
            stock_code = str(stock_code_raw)
        
        stock_code = stock_code.strip()
        logger.info(f"處理後的股票代碼: {stock_code}")
        
        if not stock_code:
            return jsonify({'success': False, 'message': '股票代號不能為空'}), 400
        
        success = monitor.remove_stock(stock_code)
        logger.info(f"刪除結果: {success}")
        
        return jsonify({
            'success': success, 
            'message': '移除成功' if success else '股票不存在或移除失敗'
        })
    except Exception as e:
        logger.error(f"刪除股票錯誤: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'服務器錯誤: {str(e)}'}), 500

@app.route('/api/logs/recent')
def get_recent_logs():
    """獲取最近日誌"""
    try:
        with open('logs/stock_monitor.log', 'r') as f:
            lines = f.readlines()
            return jsonify({'logs': lines[-50:]})  # 最後50行
    except:
        return jsonify({'logs': []})

if __name__ == '__main__':
    # 確保必要的目錄存在
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    
    print("=" * 60)
    print("🚀 AI主力監控平台啟動中...")
    print("=" * 60)
    print("🌐 平台網址: http://127.0.0.1:8082")
    print("📱 行動裝置: http://[您的IP]:8082")
    print("💡 提示: 如果端口被占用，可修改 dashboard.py 最後一行的端口號")
    print("🛑 停止平台: 按 Ctrl+C")
    print("=" * 60)
    print()
    
    app.run(host='0.0.0.0', port=8082, debug=True)
