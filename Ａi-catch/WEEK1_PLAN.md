# 📅 Week 1 實作計劃: 數據庫 + 完整 API

> **目標**: 建立完整的後端基礎設施（PostgreSQL + Redis + FastAPI）

**時間**: Day 1-7  
**狀態**: ⏳ 準備就緒  
**前置條件**: ✅ FastAPI v3.0 已啟動並測試通過

---

## 📊 概覽

### 本週目標

- ✅ **Day 1-2**: PostgreSQL + Redis 環境設置
- ✅ **Day 3-4**: FastAPI 完整 API 開發
- ✅ **Day 5-7**: v3.0 核心專家實作（5位）

### 預期成果

1. 生產級數據庫環境
2. 完整的 RESTful API 
3. WebSocket 即時推送
4. 5 位核心專家系統
5. 完整的測試覆蓋

---

## 🗓️ Day 1-2: 數據庫環境設置

### Day 1 上半天: PostgreSQL 安裝與配置

#### 1.1 安裝 PostgreSQL 14
```bash
# 使用 Homebrew 安裝
brew install postgresql@14

# 啟動服務
brew services start postgresql@14

# 驗證安裝
psql --version
```

#### 1.2 創建數據庫和用戶
```sql
-- 創建數據庫
CREATE DATABASE ai_stock_db;

-- 創建用戶
CREATE USER ai_stock_user WITH PASSWORD 'your_secure_password';

-- 授權
GRANT ALL PRIVILEGES ON DATABASE ai_stock_db TO ai_stock_user;
```

#### 1.3 測試連接
```bash
# 使用 psql 連接
psql -U ai_stock_user -d ai_stock_db -h localhost

# 或使用 Python
python3 -c "import psycopg2; conn = psycopg2.connect('dbname=ai_stock_db user=ai_stock_user'); print('✅ 連接成功')"
```

---

### Day 1 下半天: Database Schema 設計

#### 1.4 創建 Schema 文件

**文件位置**: `backend-v3/database/schema.sql`

**主要表結構**:
1. **stocks** - 股票基本信息
2. **stock_quotes** - 即時報價
3. **analysis_results** - 分析結果
4. **expert_signals** - 專家信號
5. **alerts** - 警報記錄
6. **users** - 用戶（可選）

#### 1.5 使用 Alembic 進行遷移
```bash
cd backend-v3

# 安裝 alembic
pip install alembic psycopg2-binary

# 初始化
alembic init alembic

# 創建第一個遷移
alembic revision -m "Initial schema"

# 執行遷移
alembic upgrade head
```

---

### Day 2 上半天: Redis 安裝與配置

#### 2.1 安裝 Redis
```bash
# 使用 Homebrew 安裝
brew install redis

# 啟動服務
brew services start redis

# 驗證
redis-cli ping
# 應返回 PONG
```

#### 2.2 Redis 配置
```bash
# 編輯配置文件（如需要）
vim /opt/homebrew/etc/redis.conf

# 基本配置
# - maxmemory: 設定最大內存
# - maxmemory-policy: allkeys-lru (推薦)
```

#### 2.3 測試 Redis
```python
import redis

# 連接測試
r = redis.Redis(host='localhost', port=6379, db=0)
r.set('test_key', 'test_value')
print(r.get('test_key'))  # 應返回 b'test_value'
```

---

### Day 2 下半天: Database 集成到 FastAPI

#### 2.4 安裝 Python 套件
```bash
cd backend-v3
source venv/bin/activate

pip install \
  sqlalchemy \
  alembic \
  psycopg2-binary \
  redis \
  asyncpg \
  aioredis
```

#### 2.5 創建數據庫連接模組

**文件**: `backend-v3/app/database/connection.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import redis.asyncio as aioredis

# PostgreSQL
DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/ai_stock_db"
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession)

# Redis
redis_client = aioredis.from_url("redis://localhost:6379")
```

#### 2.6 測試集成
```bash
# 創建測試腳本
python3 backend-v3/tests/test_database.py

# 驗證
# - PostgreSQL 連接 ✅
# - Redis 連接 ✅
# - 基本 CRUD 操作 ✅
```

---

## 🗓️ Day 3-4: FastAPI 完整 API 開發

### Day 3: RESTful API 端點

#### 3.1 股票相關 API

**文件**: `backend-v3/app/api/stocks.py`

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/stocks")
async def get_stocks():
    """獲取股票列表"""
    pass

@router.get("/stocks/{symbol}")
async def get_stock_detail(symbol: str):
    """獲取單一股票詳情"""
    pass

@router.get("/stocks/{symbol}/quote")
async def get_stock_quote(symbol: str):
    """獲取即時報價"""
    pass
```

**實作端點**:
- `GET /api/stocks` - 股票列表
- `GET /api/stocks/{symbol}` - 股票詳情
- `GET /api/stocks/{symbol}/quote` - 即時報價
- `GET /api/stocks/{symbol}/history` - 歷史數據
- `GET /api/stocks/{symbol}/orderbook` - 五檔掛單

#### 3.2 分析相關 API

**文件**: `backend-v3/app/api/analysis.py`

**實作端點**:
- `POST /api/analysis/mainforce` - 主力分析
- `POST /api/analysis/multiframe` - 多時間框架
- `GET /api/analysis/results/{symbol}` - 分析結果
- `GET /api/analysis/history` - 分析歷史

---

### Day 4: WebSocket + Alert API

#### 4.1 WebSocket 即時推送

**文件**: `backend-v3/app/api/realtime.py`

```python
@app.websocket("/ws/stocks/{symbol}")
async def stock_websocket(websocket: WebSocket, symbol: str):
    """股票即時數據推送"""
    await websocket.accept()
    
    try:
        while True:
            # 從 Redis 獲取最新數據
            data = await get_latest_quote(symbol)
            await websocket.send_json(data)
            await asyncio.sleep(1)
    except:
        await websocket.close()
```

**實作功能**:
- `/ws/stocks/{symbol}` - 單股即時報價
- `/ws/analysis/{symbol}` - 分析結果推送
- `/ws/alerts` - 警報推送

#### 4.2 警報 API

**文件**: `backend-v3/app/api/alerts.py`

**實作端點**:
- `GET /api/alerts` - 警報列表
- `POST /api/alerts` - 創建警報
- `DELETE /api/alerts/{id}` - 刪除警報
- `GET /api/alerts/history` - 歷史警報

---

## 🗓️ Day 5-7: v3.0 核心專家實作

### 核心專家優先順序

#### 🥇 Tier 1: 立即實作（Day 5）

1. **大單交易專家** (`BigOrderExpert`)
   - 偵測大額交易
   - 分析買賣方向
   - 計算主力意圖

2. **價量協同專家** (`PriceVolumeExpert`)
   - 價量背離
   - 價量齊升
   - 異常放量

3. **趨勢偵測專家** (`TrendExpert`)
   - 上升/下降趨勢
   - 趨勢強度
   - 趨勢轉折點

#### 🥈 Tier 2: 次要實作（Day 6）

4. **資金流向專家** (`MoneyFlowExpert`)
   - 主力進出
   - 散戶行為
   - 資金流向強度

5. **支撐壓力專家** (`SupportResistanceExpert`)
   - 關鍵價位
   - 突破/跌破
   - 價位強度

---

### Day 5: 第一組專家實作

#### 5.1 專家基類

**文件**: `backend-v3/app/detector/base_expert.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseExpert(ABC):
    """專家基類"""
    
    def __init__(self, name: str, weight: float = 1.0):
        self.name = name
        self.weight = weight
    
    @abstractmethod
    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """分析方法"""
        pass
    
    @abstractmethod
    def get_signal_strength(self) -> float:
        """獲取信號強度 (0-1)"""
        pass
```

#### 5.2 大單交易專家

**文件**: `backend-v3/app/detector/experts/big_order_expert.py`

**實作功能**:
- 偵測大額交易（買/賣）
- 計算大單占比
- 判斷主力意圖（吸籌/出貨）
- 信號強度評分

#### 5.3 價量協同專家

**文件**: `backend-v3/app/detector/experts/price_volume_expert.py`

**實作功能**:
- 價量背離偵測
- 價量齊升確認
- 異常放量警報
- 趨勢確認

#### 5.4 趨勢偵測專家

**文件**: `backend-v3/app/detector/experts/trend_expert.py`

**實作功能**:
- 趨勢判斷（多/空）
- 趨勢強度計算
- 轉折點偵測
- 趨勢持續時間

---

### Day 6: 第二組專家實作

#### 6.1 資金流向專家
**文件**: `backend-v3/app/detector/experts/money_flow_expert.py`

#### 6.2 支撐壓力專家
**文件**: `backend-v3/app/detector/experts/support_resistance_expert.py`

---

### Day 7: 整合與測試

#### 7.1 專家管理器

**文件**: `backend-v3/app/detector/expert_manager.py`

```python
class ExpertManager:
    """專家系統管理器"""
    
    def __init__(self):
        self.experts = []
    
    def register_expert(self, expert: BaseExpert):
        """註冊專家"""
        self.experts.append(expert)
    
    async def analyze(self, symbol: str) -> Dict:
        """執行所有專家分析"""
        results = []
        for expert in self.experts:
            result = await expert.analyze(symbol)
            results.append(result)
        
        return self.aggregate_results(results)
```

#### 7.2 完整測試

**測試腳本**: `backend-v3/tests/test_week1.py`

**測試項目**:
- ✅ PostgreSQL 連接
- ✅ Redis 連接
- ✅ 所有 API 端點
- ✅ WebSocket 連接
- ✅ 5 位專家分析
- ✅ 數據持久化
- ✅ 性能測試

---

## 📦 Week 1 完成清單

### 基礎設施
- [ ] PostgreSQL 14 安裝
- [ ] Redis 安裝
- [ ] Database Schema 創建
- [ ] Alembic 遷移設置

### FastAPI 開發
- [ ] 股票 API (5 個端點)
- [ ] 分析 API (4 個端點)
- [ ] 警報 API (4 個端點)
- [ ] WebSocket (3 個端點)

### 專家系統
- [ ] 大單交易專家
- [ ] 價量協同專家
- [ ] 趨勢偵測專家
- [ ] 資金流向專家
- [ ] 支撐壓力專家

### 測試與文檔
- [ ] 單元測試
- [ ] 集成測試
- [ ] API 文檔
- [ ] 使用指南

---

## 🎯 Week 1 成功標準

### 功能性
1. ✅ 可以通過 API 獲取股票數據
2. ✅ WebSocket 可以推送即時數據
3. ✅ 5 位專家可以產生分析結果
4. ✅ 警報系統可以觸發通知
5. ✅ 數據可以持久化到 PostgreSQL

### 性能
1. API 響應時間 < 200ms
2. WebSocket 延遲 < 100ms
3. 專家分析時間 < 500ms
4. 支援 100+ 並發連接

### 質量
1. 測試覆蓋率 > 70%
2. 無嚴重 bug
3. 代碼符合 PEP 8
4. 完整的 API 文檔

---

## 📚 需要的依賴套件

### requirements-v3.txt（更新）
```txt
# 基礎框架
fastapi==0.109.0
uvicorn[standard]==0.27.0
websockets==12.0

# 數據庫
sqlalchemy==2.0.25
alembic==1.13.1
psycopg2-binary==2.9.9
asyncpg==0.29.0

# Redis
redis==5.0.1
aioredis==2.0.1

# 數據處理
pandas==2.2.0
numpy==1.26.3

# HTTP 客戶端
httpx==0.26.0
aiohttp==3.9.1

# 工具
python-dotenv==1.0.0
pydantic==2.5.3
pydantic-settings==2.1.0
```

---

## 🔧 環境變數配置

### .env 文件（backend-v3/.env）
```bash
# Database
DATABASE_URL=postgresql+asyncpg://ai_stock_user:password@localhost/ai_stock_db
DATABASE_POOL_SIZE=20

# Redis
REDIS_URL=redis://localhost:6379
REDIS_DB=0

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# 安全
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256

# 日誌
LOG_LEVEL=INFO
LOG_FILE=/var/log/ai-stock-api.log
```

---

## 🚀 每日啟動流程

### 開始工作前
```bash
# 1. 啟動數據庫服務
brew services start postgresql@14
brew services start redis

# 2. 啟動 FastAPI
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./start_api_v3.sh

# 3. 驗證服務
curl http://127.0.0.1:8000/health
```

### 結束工作後
```bash
# 停止 FastAPI (Ctrl+C 在運行的終端)

# 可選：停止數據庫（如果不需要常駐）
brew services stop postgresql@14
brew services stop redis
```

---

## 📊 進度追蹤

### 使用 GitHub Issues 或簡單的 Markdown

**追蹤文件**: `backend-v3/WEEK1_PROGRESS.md`

```markdown
# Week 1 進度

## Day 1
- [x] PostgreSQL 安裝
- [x] 數據庫創建
- [ ] Schema 設計

## Day 2
- [ ] Redis 安裝
- [ ] Database 集成

...
```

---

## 💡 建議的工作方式

### 新對話開始方式

**對話標題**: "Week 1: PostgreSQL + Redis + FastAPI 開發"

**提供給 AI 的信息**:
```
我要開始 Week 1 的開發工作。

目標：
1. 設置 PostgreSQL + Redis
2. 開發完整 FastAPI
3. 實作 5 位核心專家

當前狀態：
- ✅ FastAPI v3.0 基礎已就緒
- ✅ 測試通過（見 V3_TEST_REPORT.md）
- ✅ 專案路徑：/Users/Mac/Documents/ETF/AI/Ａi-catch

請協助我完成 Day 1 的 PostgreSQL 設置。
```

**附上文檔**:
- `FULL_SYSTEM_ROADMAP.md`
- `V3_EXPANSION_PLAN.md`
- `WEEK1_PLAN.md`（本文件）

---

## 🎊 Week 1 完成後

### 預期成果

1. **完整的後端 API**
   - 15+ RESTful 端點
   - 3+ WebSocket 端點
   - 完整文檔

2. **5 位專家系統**
   - 大單交易專家
   - 價量協同專家
   - 趨勢偵測專家
   - 資金流向專家
   - 支撐壓力專家

3. **生產級基礎設施**
   - PostgreSQL 數據庫
   - Redis 緩存
   - 完整測試覆蓋

### 下一步: Week 2

- 完成剩餘 10 位專家
- 多時間框架分析
- 回測系統
- 性能優化

---

**準備好開始了嗎？** 🚀

**建議**: 今晚休息，明天早上精神飽滿地開始！

**最後更新**: 2025-12-15 21:00  
**狀態**: 📋 計劃完成  
**下一步**: Day 1 - PostgreSQL 安裝
