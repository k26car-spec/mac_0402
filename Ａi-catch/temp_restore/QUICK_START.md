# 🚀 AI Stock Intelligence v3.0 快速启动指南

**最后更新**: 2025-12-16 01:00

---

## ⚡ 快速开始（30秒）

```bash
# 1. 启动所有服务
./start_all.sh

# 2. 打开浏览器
open http://127.0.0.1:8000/api/docs
open http://127.0.0.1:8082/

# 3. 测试AI专家
curl http://127.0.0.1:8000/api/analysis/experts
```

---

## 📱 可用界面

| 界面 | 网址 | 说明 |
|------|------|------|
| **API文档** | http://127.0.0.1:8000/api/docs | Swagger UI，可测试所有API |
| **ReDoc** | http://127.0.0.1:8000/redoc | 美观的API文档 |
| **Dashboard** | http://127.0.0.1:8082/ | v2.0主力监控平台 |
| **健康检查** | http://127.0.0.1:8000/health | 系统状态 |

---

## 🤖 6个AI专家

### 查看所有专家

```bash
curl http://127.0.0.1:8000/api/analysis/experts
```

**返回**:
```json
{
    "total_experts": 6,
    "experts": [
        {"name": "主力侦测"},
        {"name": "量价分析"},
        {"name": "技术指标"},
        {"name": "动量分析"},
        {"name": "趋势识别"},
        {"name": "支撑阻力"}
    ]
}
```

### 运行AI分析

```bash
# 分析台积电(2330)
curl -X POST "http://127.0.0.1:8000/api/analysis/mainforce?symbol=2330"
```

**返回**: 6个专家的综合分析结果！

---

## 📊 主要API端点

### 股票查询

```bash
# 获取所有股票
curl http://127.0.0.1:8000/api/stocks/

# 获取单一股票
curl http://127.0.0.1:8000/api/stocks/2330

# 搜索股票
curl "http://127.0.0.1:8000/api/stocks/search/台積"
```

### AI分析

```bash
# 查看专家列表
curl http://127.0.0.1:8000/api/analysis/experts

# 获取分析摘要
curl http://127.0.0.1:8000/api/analysis/summary/2330

# 主力分析
curl -X POST "http://127.0.0.1:8000/api/analysis/mainforce?symbol=2330"

# 风险评估
curl http://127.0.0.1:8000/api/analysis/risk/2330
```

### 警报管理

```bash
# 获取活跃警报
curl http://127.0.0.1:8000/api/alerts/active

# 警报统计
curl http://127.0.0.1:8000/api/alerts/stats
```

### 缓存操作

```bash
# 测试Redis
curl http://127.0.0.1:8000/api/cache/test

# 设置缓存
curl -X POST "http://127.0.0.1:8000/api/cache/set?key=test&value=hello"

# 获取缓存
curl http://127.0.0.1:8000/api/cache/get/test
```

---

## 🛠️ 服务管理

### 启动服务

```bash
# 启动所有服务
./start_all.sh

# 或分别启动
cd backend-v3
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 停止服务

```bash
# 停止所有服务
./stop_all.sh

# 或手动停止
pkill -f "uvicorn app.main"
pkill -f "dashboard.py"
```

### 查看日志

```bash
# FastAPI日志
tail -f logs/fastapi.log

# Dashboard日志
tail -f logs/dashboard.log
```

---

## 📦 系统组件

### 后端服务

| 组件 | 端口 | 状态检查 |
|------|------|----------|
| **FastAPI** | 8000 | `curl http://127.0.0.1:8000/health` |
| **Dashboard** | 8082 | `curl http://127.0.0.1:8082/` |
| **PostgreSQL** | 5432 | `psql ai_stock_db` |
| **Redis** | - | FakeRedis (dev) |

### AI专家系统

1. **主力侦测** - 检测主力进出场
2. **量价分析** - 分析量价配合
3. **技术指标** - MA/RSI/MACD分析
4. **动量分析** - 价格和成交量动量
5. **趋势识别** - 判断趋势方向和强度
6. **支撑阻力** - 识别关键价位

---

## 💡 快速示例

### Python 调用

```python
import requests

# 1. 查看专家列表
resp = requests.get("http://127.0.0.1:8000/api/analysis/experts")
print(resp.json())

# 2. 运行AI分析
resp = requests.post(
    "http://127.0.0.1:8000/api/analysis/mainforce",
    params={"symbol": "2330", "timeframe": "1d"}
)
result = resp.json()
print(f"综合信号: {result['analysis']['overall_signal']}")
print(f"参与专家: {result['analysis']['expert_count']}")

# 3. 获取股票列表
resp = requests.get("http://127.0.0.1:8000/api/stocks/")
stocks = resp.json()
print(f"共有 {stocks['count']} 只股票")
```

### JavaScript 调用

```javascript
// 获取专家列表
fetch('http://127.0.0.1:8000/api/analysis/experts')
  .then(res => res.json())
  .then(data => console.log(`${data.total_experts}个专家`));

// 运行AI分析
fetch('http://127.0.0.1:8000/api/analysis/mainforce?symbol=2330', {
  method: 'POST'
})
  .then(res => res.json())
  .then(data => {
    console.log('综合信号:', data.analysis.overall_signal);
    console.log('专家共识:', data.analysis.consensus);
  });
```

---

## 🔧 故障排除

### 端口被占用

```bash
# 查看占用端口的进程
lsof -i :8000
lsof -i :8082

# kill进程
kill -9 <PID>

# 或使用停止脚本
./stop_all.sh
```

### 服务无法启动

```bash
# 检查PostgreSQL
pgrep postgres

# 检查虚拟环境
cd backend-v3
source venv/bin/activate
which python

# 重新安装依赖
pip install -r requirements-v3.txt
```

### 数据库连接问题

```bash
# 测试数据库连接
psql ai_stock_db

# 检查数据库是否存在
psql -l | grep ai_stock_db
```

---

## 📚 完整文档

- **Week 1 Roadmap**: FULL_SYSTEM_ROADMAP.md
- **6专家报告**: 6_EXPERTS_FINAL_REPORT.md
- **API设计**: backend-v3/README-v3.md
- **完成报告**: DAY1-6 各天报告

---

## 🎯 下一步

### Week 2 计划

1. **连接真实数据源**
   - Fubon API集成
   - Yahoo Finance数据
   - 实时行情推送

2. **前端开发**
   - React/Next.js界面
   - 实时图表展示
   - AI分析可视化

3. **性能优化**
   - 数据库查询优化
   - Redis缓存策略
   - API响应时间优化

4. **更多AI专家**
   - 形态识别专家
   - 情绪分析专家
   - 资金流向专家

---

## 💬 获取帮助

- **API文档**: http://127.0.0.1:8000/api/docs
- **项目文档**: 查看 `*.md` 文件
- **日志**: `logs/` 目录

---

**祝您使用愉快！** 🚀

**更新日期**: 2025-12-16  
**版本**: v3.0  
**AI专家**: 6个
