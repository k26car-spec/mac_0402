# 🚀 1周LSTM集成计划 - 详细执行指南

## 📅 目标日期
**启动日期**: 2026-02-10（周一）  
**启用日期**: 2026-02-14（周五）  
**总时长**: 5个工作日 + 周末监控

---

## 🎯 总体目标

**2026年2月14日启用Smart Entry v2.1（含LSTM）**

**成功标准**:
- ✅ 43支股票模型全部改进
- ✅ LSTM回测准确率≥55%
- ✅ Smart Entry集成完成
- ✅ 测试全部通过
- ✅ 系统稳定运行

---

## 📊 每日详细计划

### Day 1 - 2月10日（周一）🔴

#### 上午（3小时）- 完成模型改进

**任务1: 处理欠拟合股票**（预计11支）
```bash
python3 batch_fix_underfitting.py

# 目标：11支欠拟合股票
# 方法：Larger模型 + 延长训练
# 预期：60-70%改善
# 时间：2小时
```

**任务2: 处理其他股票**（预计6支）
```bash
# 手动或脚本处理剩余股票
# 时间：1小时
```

**里程碑**: ✅ **43/43支完成（100%）**

---

#### 下午（3小时）- LSTM回测准备

**任务3: 创建回测脚本**
```bash
# 创建 lstm_backtest.py
# 功能：
#   - 加载所有LSTM模型
#   - 准备测试数据（最近3个月）
#   - 计算准确率、精确率、召回率
#   - 生成详细报告
```

**任务4: 开始回测**
```bash
python3 lstm_backtest.py --stocks all --period 3m

# 测试26-43支已改进股票
# 时间：1-2小时（运行中）
```

**里程碑**: 🚧 **回测进行中**

---

#### 晚上（1小时）- 分析回测结果

**任务5: 回测结果分析**
```bash
# 查看 lstm_backtest_report.json
# 分析准确率分布
# 识别问题股票
```

**决策点1**: 
- ✅ 准确率≥55% → 继续Day 2
- ⚠️ 准确率<55% → 优化模型（延后1-2天）

**预期**: 准确率60-65%，通过 ✅

---

### Day 2 - 2月11日（周二）🟠

#### 上午（3小时）- Smart Entry代码修改（Part 1）

**任务6: 创建LSTM管理器**
```python
# 文件：backend-v3/app/services/lstm_manager.py
class LSTMModelManager:
    def __init__(self):
        self.models = {}
        self._load_models()
    
    def _load_models(self):
        # 加载所有.h5模型文件
        
    def predict(self, stock_code, data):
        # 返回预测概率
```

**任务7: 修改Smart Entry系统**
```python
# 文件：backend-v3/app/services/smart_entry_system.py
# 添加LSTM集成
from .lstm_manager import LSTMModelManager

class SmartEntrySystem:
    def __init__(self):
        # ... 现有代码 ...
        self.lstm_manager = LSTMModelManager()
        self.use_lstm = config.get('use_lstm', False)
```

---

#### 下午（3小时）- Smart Entry代码修改（Part 2）

**任务8: 集成LSTM到评分系统**
```python
def calculate_confidence(self, stock_code, market_data):
    # 现有技术指标评分
    technical_score = self._calculate_technical_score(...)
    
    # LSTM预测
    if self.use_lstm and stock_code in self.lstm_manager.models:
        lstm_prob = self.lstm_manager.predict(stock_code, prepared_data)
        lstm_score = lstm_prob * 100
    else:
        lstm_score = 50  # 中性
    
    # 加权综合
    final_score = (
        technical_score * (1 - self.lstm_weight) +
        lstm_score * self.lstm_weight
    )
    
    return final_score
```

**任务9: 更新配置文件**
```json
// data/smart_entry_config.json
{
  "lstm_integration": {
    "enabled": true,
    "weight": 0.20,
    "min_confidence": 0.55,
    "fallback_on_missing": true
  }
}
```

**里程碑**: 🚧 **代码修改完成**

---

#### 晚上（2小时）- 单元测试

**任务10: 创建测试**
```bash
# tests/test_lstm_integration.py
# 测试：
#   - LSTM模型加载
#   - 预测功能
#   - 评分集成
#   - 配置读取
```

**任务11: 运行测试**
```bash
python3 -m pytest tests/test_lstm_integration.py -v
```

**预期**: 所有测试通过 ✅

---

### Day 3 - 2月12日（周三）🟡

#### 上午（2小时）- 集成测试

**任务12: API测试**
```bash
# 启动后端
cd backend-v3
python3 -m uvicorn app.main:app --reload

# 测试API
curl http://localhost:8000/api/smart-entry/score/2330
```

**任务13: 验证LSTM调用**
```bash
# 检查日志
tail -f backend-v3/backend.log | grep -i "lstm"

# 应该看到：
# "LSTM模型加载: 43个"
# "LSTM预测: 2330 -> 0.65"
```

---

#### 下午（2小时）- Bug修复

**任务14: 修复发现的问题**
- 模型加载错误
- 数据格式不匹配
- 预测异常
- 配置读取问题

**任务15: 回归测试**
```bash
# 重新运行所有测试
python3 -m pytest tests/ -v
```

---

#### 晚上（2小时）- 性能优化

**任务16: 优化模型加载**
```python
# 懒加载：用时才加载
# 缓存：避免重复加载
# 异步：不阻塞主流程
```

**任务17: 监控准备**
```bash
# 添加日志
# 添加性能指标
# 准备监控脚本
```

**里程碑**: ✅ **集成完成，准备部署**

---

### Day 4 - 2月13日（周四）🟢

#### 上午（2小时）- 最终测试

**任务18: 端到端测试**
```bash
# 测试完整流程：
# 1. 获取股票数据
# 2. 技术指标分析
# 3. LSTM预测
# 4. 综合评分
# 5. 进场决策
```

**任务19: 边界情况测试**
```bash
# 测试：
# - 无LSTM模型的股票
# - LSTM预测失败
# - 数据不足
# - 配置错误
```

---

#### 下午（2小时）- 配置优化

**任务20: 调整参数**
```json
{
  "lstm_weight": 0.20,  // 可能调至0.15或0.25
  "min_confidence": 0.55,  // 可能调整
  "threshold_adjustment": 5  // LSTM支持时降低阈值
}
```

**任务21: 对比测试**
```bash
# 模拟对比v2.0 vs v2.1
# 相同条件下的决策差异
```

---

#### 晚上（1小时）- 部署准备

**任务22: 备份**
```bash
# 备份现有配置
cp data/smart_entry_config.json data/smart_entry_config_v2.0_backup.json

# 备份代码
git commit -am "Backup before LSTM integration"
git tag v2.0-stable
```

**任务23: 部署文档**
```markdown
# DEPLOYMENT.md
- 部署步骤
- 回退步骤
- 监控指标
- 应急预案
```

**里程碑**: ✅ **准备就绪**

---

### Day 5 - 2月14日（周五）🔵

#### 上午（1小时）- 最终检查

**任务24: 预部署检查清单**
```
□ 所有测试通过
□ 配置文件正确
□ 日志系统就绪
□ 监控脚本准备
□ 备份完成
□ 回退方案明确
```

**任务25: 灰度启用**
```json
// 先部署但不启用
{
  "lstm_integration": {
    "enabled": false  // 先关闭
  }
}
```

---

#### 下午（1小时）- 正式启用！🚀

**13:00 - 启用LSTM**
```json
{
  "lstm_integration": {
    "enabled": true  // 开启！
  }
}
```

**任务26: 重启服务**
```bash
# 重启后端
cd backend-v3
./restart_backend.sh

# 检查日志
tail -f backend.log
```

**任务27: 验证运行**
```bash
# 测试API
curl http://localhost:8000/api/smart-entry/score/2330

# 检查LSTM是否参与
# 应该在响应中看到lstm_score
```

**📢 宣布**: ✅ **Smart Entry v2.1正式启用！**

---

#### 晚上（按需）- 密切监控

**任务28: 实时监控**
```bash
# 监控日志
tail -f backend.log | grep -E "entry|lstm|signal"

# 监控性能
htop

# 监控决策
python3 monitor_decisions.py
```

**任务29: 记录数据**
```bash
# 记录每个进场信号
# 记录LSTM贡献
# 记录技术指标vs LSTM的差异
```

---

### 周末 - 2月15-16日（监控评估）📊

#### 周六（按需）

**任务30: 数据收集**
- 收集周五的所有决策记录
- 统计信号数量
- 分析LSTM影响

**任务31: 初步评估**
```python
# analyze_first_day.py
- 进场信号数量对比
- LSTM贡献分析
- 是否有异常
```

---

#### 周日（1小时）

**任务32: 周总结**
```markdown
# WEEK1_SUMMARY.md
- 启用情况
- 信号统计
- 初步效果
- 发现的问题
- 下周计划
```

**决策点2**:
- ✅ 运行正常 → 继续监控，准备调优
- ⚠️ 有问题 → 周一调整/回退
- ❌ 严重问题 → 立即回退到v2.0

---

## 📋 任务依赖图

```
Day 1: 模型改进 ──┐
                  ├─→ Day 1: 回测 ──→ 决策点1
                  │                      ↓
Day 2: 代码开发 ←─┘                  继续/延后
      ↓
Day 2: 测试
      ↓
Day 3: 集成+Bug修复
      ↓
Day 4: 优化+部署准备
      ↓
Day 5: 启用！
      ↓
周末: 监控评估 ──→ 决策点2
                      ↓
                  继续/调整/回退
```

---

## ⏰ 时间预算

| 天 | 工作时间 | 主要任务 | 关键输出 |
|----|---------|---------|---------|
| Day 1 | 7h | 模型+回测 | 43/43完成，回测报告 |
| Day 2 | 8h | 代码开发 | LSTM集成完成 |
| Day 3 | 6h | 测试修复 | 集成测试通过 |
| Day 4 | 5h | 优化部署 | 部署就绪 |
| Day 5 | 2h | 启用监控 | v2.1上线 |
| **总计** | **28h** | **5天** | **LSTM启用** |

---

## ✅ 每日检查清单

### Day 1 检查
- [ ] 43支股票改进完成
- [ ] 回测脚本创建
- [ ] 回测执行完成
- [ ] 准确率≥55%
- [ ] 决定继续

### Day 2 检查
- [ ] LSTM管理器完成
- [ ] Smart Entry修改完成
- [ ] 配置文件更新
- [ ] 单元测试通过

### Day 3 检查
- [ ] 集成测试通过
- [ ] Bug全部修复
- [ ] API正常工作
- [ ] 性能优化完成

### Day 4 检查
- [ ] 端到端测试通过
- [ ] 参数调优完成
- [ ] 备份完成
- [ ] 文档完整

### Day 5 检查
- [ ] 预部署检查通过
- [ ] LSTM成功启用
- [ ] 监控系统运行
- [ ] 无严重错误

---

## 🚨 应急预案

### 回退机制

**快速回退**（5分钟）:
```bash
# 方法1: 禁用LSTM
# 修改配置
{
  "lstm_integration": { "enabled": false }
}

# 重启
./restart_backend.sh
```

**完全回退**（15分钟）:
```bash
# 恢复备份配置
cp data/smart_entry_config_v2.0_backup.json data/smart_entry_config.json

# 切换到稳定版本
git checkout v2.0-stable

# 重启
./restart_backend.sh
```

### 常见问题处理

**问题1: LSTM加载失败**
```
解决: 检查模型文件路径
     检查文件权限
     查看错误日志
```

**问题2: 预测异常**
```
解决: 检查数据格式
     验证模型输入
     添加异常处理
```

**问题3: 性能下降**
```
解决: 启用缓存
     异步加载
     优化频率
```

---

## 📊 监控指标

### 关键指标

**系统指标**:
- LSTM加载成功率
- 预测响应时间
- 内存使用
- CPU使用

**业务指标**:
- 每日信号数量
- LSTM参与率
- 决策改变率（vs v2.0）
- 初步准确率

### 监控频率

**Day 5-7**: 每小时检查  
**Week 2**: 每天检查  
**Month 1**: 每周检查

---

## 🎯 成功标准

### 技术标准
- ✅ 所有测试通过
- ✅ 无严重bug
- ✅ 性能影响<10%
- ✅ LSTM正常工作

### 业务标准
- ✅ 系统稳定运行
- ✅ 信号质量不下降
- ✅ LSTM有效贡献
- ✅ 可以持续优化

---

## 💪 激励与期望

### 这一周您将完成

**工作量**: 28小时  
**成果**: Smart Entry v2.1上线  
**提升**: 预计准确率+10%  
**价值**: 巨大！

### 每天的成就感

**Day 1**: 100%模型改进 🏆  
**Day 2**: LSTM集成完成 🤖  
**Day 3**: 所有测试通过 ✅  
**Day 4**: 准备就绪 🚀  
**Day 5**: 正式启用！ 🎉

---

## 📁 需要创建的文件

### 脚本
1. `batch_fix_underfitting.py` - 欠拟合处理
2. `lstm_backtest.py` - LSTM回测
3. `backend-v3/app/services/lstm_manager.py` - LSTM管理器
4. `tests/test_lstm_integration.py` - 集成测试
5. `monitor_decisions.py` - 决策监控
6. `analyze_first_day.py` - 首日分析

### 文档
1. `DEPLOYMENT.md` - 部署文档
2. `WEEK1_SUMMARY.md` - 周总结
3. `ROLLBACK_GUIDE.md` - 回退指南

---

## 🚀 准备开始！

**当前时间**: 2026-02-09 22:45  
**启动时间**: 2026-02-10 上午  
**启用时间**: 2026-02-14 下午  

**距离启用**: **5天** ⏰

---

**明天就开始！准备好了吗？** 💪🚀🎯
