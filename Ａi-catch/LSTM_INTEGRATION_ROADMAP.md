# 🚀 LSTM集成完整路线图

## 📅 创建日期
2026-02-09 21:20

---

## 🎯 总体目标

将LSTM深度学习模型集成到Smart Entry v2模拟交易系统，提升进场决策准确度。

**预期效果**:
- 进场信号准确率提升10-20%
- 假信号减少15-25%
- 整体胜率提升至40-50%

---

## 📊 当前状态

### 已完成 ✅

| 项目 | 状态 | 数量 | 进度 |
|------|------|------|------|
| LSTM模型改进 | ✅ 完成 | 19支 | 44% |
| 模型验证 | ✅ 完成 | 19支 | 100% |
| 平均改善 | ✅ 优秀 | 90.8% | - |
| 性能稳定性 | ✅ 验证 | 100% | - |

### 待完成 ⏳

| 项目 | 状态 | 数量 | 预计时间 |
|------|------|------|---------|
| 剩余模型改进 | ⏳ 待处理 | 24支 | 3-4小时 |
| LSTM回测 | ⏳ 待开始 | 43支 | 2-3小时 |
| Smart Entry集成 | ⏳ 待开始 | 1个系统 | 2-3小时 |
| 纸上交易测试 | ⏳ 待开始 | 1-2周 | - |

---

## 🗓️ 4阶段执行计划

### 阶段1: 完成LSTM模型改进（本周）🔴

**目标**: 43/43支股票全部改进完成

**任务列表**:

#### 1.1 处理中度问题股票（8支）

**股票列表**:
- 8046, 2344, 3189, 1605
- 2449, 1301, 3037, 1326

**方法**: Regularized或Optimized  
**预期改善**: 65-80%  
**预计时间**: 1.5-2小时

**执行**:
```bash
python3 batch_fix_moderate.py
```

---

#### 1.2 处理欠拟合股票（11支）

**股票列表**:
- 2301, 3034, 6153, 2609, 3706
- 2317, 2314, 2412, 2881, 2408, 2618

**方法**: Larger + 延长训练  
**预期改善**: 15-30%  
**预计时间**: 1.5-2小时

**执行**:
```bash
python3 batch_fix_underfitting.py
```

---

#### 1.3 处理其他股票（5支）

**包括**:
- 8422（配置更新）
- 其他中度问题股票

**预计时间**: 30分钟

---

**阶段1总结**:
- 总时间: 3-4小时
- 完成后: 43/43支（100%）
- 平均改善预期: 70-80%

---

### 阶段2: LSTM回测验证（本周末）🟠

**目标**: 验证LSTM预测准确度≥60%

#### 2.1 创建回测框架

**功能**:
- 加载已改进的LSTM模型
- 使用历史数据测试预测
- 计算准确率、精确率、召回率
- 生成回测报告

**脚本**: `lstm_backtest.py`

---

#### 2.2 回测指标

**关键指标**:
- **准确率**: 预测正确的比例
- **精确率**: 预测看涨且实际上涨的比例
- **召回率**: 实际上涨且被预测到的比例
- **F1分数**: 精确率和召回率的调和平均

**目标**:
- 准确率 ≥ 60%
- 精确率 ≥ 55%
- 召回率 ≥ 50%
- F1分数 ≥ 52%

---

#### 2.3 回测期间

**测试数据**:
- 使用最近3个月数据
- 滚动窗口测试
- 避免数据泄漏

**执行**:
```bash
python3 lstm_backtest.py --period 3m --stocks all
```

**输出**: `lstm_backtest_report.json`

---

**阶段2总结**:
- 时间: 2-3小时（主要是等待）
- 决策点: 如果准确度<60%，返回优化模型
- 如果≥60%，继续阶段3

---

### 阶段3: Smart Entry集成（下周）🟡

**目标**: 将LSTM集成为辅助过滤器

#### 3.1 修改Smart Entry系统

**文件**: `backend-v3/app/services/smart_entry_system.py`

**改动**:

1. **添加LSTM加载器**
```python
class SmartEntrySystem:
    def __init__(self):
        # 现有代码...
        
        # 新增: LSTM模型管理器
        self.lstm_manager = LSTMModelManager()
        self.use_lstm = self.config.get('use_lstm', False)
        self.lstm_weight = self.config.get('lstm_weight', 0.25)
```

2. **创建LSTM管理器**
```python
class LSTMModelManager:
    """LSTM模型管理器"""
    
    def __init__(self):
        self.models = {}
        self._load_models()
    
    def _load_models(self):
        """加载所有LSTM模型"""
        model_dir = "models/lstm_smart_entry"
        # 加载.h5文件
        
    def predict(self, stock_code: str, data: np.ndarray) -> float:
        """获取LSTM预测概率"""
        # 返回0-1的概率值
```

3. **整合到评分系统**
```python
def calculate_confidence(self, stock_code, market_data):
    # 现有技术指标评分
    technical_score = self._calculate_technical_score(...)
    
    # 新增: LSTM预测
    if self.use_lstm and stock_code in self.lstm_manager.models:
        lstm_prob = self.lstm_manager.predict(stock_code, data)
        lstm_score = lstm_prob * 100  # 转为0-100分
    else:
        lstm_score = 50  # 无模型时中性
    
    # 加权综合
    final_score = (
        technical_score * (1 - self.lstm_weight) +
        lstm_score * self.lstm_weight
    )
    
    return final_score
```

---

#### 3.2 更新配置文件

**文件**: `data/smart_entry_config.json`

**新增配置**:
```json
{
  "lstm_integration": {
    "enabled": true,
    "weight": 0.25,
    "min_confidence": 0.6,
    "fallback_on_missing": true,
    "description": "LSTM辅助过滤器配置"
  },
  
  "entry_thresholds": {
    "min_confidence": 75,
    "with_lstm_boost": 5,
    "description": "有LSTM支持时，降低5分阈值"
  }
}
```

---

#### 3.3 测试集成

**单元测试**:
```bash
# 测试LSTM加载
python3 -m pytest tests/test_lstm_integration.py

# 测试预测
python3 test_lstm_prediction.py --stock 2330

# 测试评分
python3 test_smart_entry_with_lstm.py
```

---

**阶段3总结**:
- 时间: 2-3小时
- 输出: 集成完成的Smart Entry v2.1
- 测试: 单元测试 + API测试

---

### 阶段4: 纸上交易验证（2周）🟢

**目标**: 实际验证LSTM增强后的表现

#### 4.1 纸上交易设置

**配置**:
```json
{
  "paper_trading": {
    "enabled": true,
    "is_simulated": true,
    "use_lstm": true,
    "max_positions": 5,
    "position_size": 5000,
    "start_date": "2026-02-10"
  }
}
```

**记录数据**:
- 每个进场信号
- 技术分数 vs LSTM分数
- 最终决策
- 实际结果

---

#### 4.2 A/B对比测试

**对照组**: Smart Entry v2.0（无LSTM）  
**实验组**: Smart Entry v2.1（含LSTM）

**运行方式**:
- 同时运行两个系统
- 记录各自信号
- 对比效果

**对比指标**:
- 信号数量
- 准确率
- 假阳性率
- 收益率

---

#### 4.3 每周评估

**Week 1评估**:
```bash
python3 analyze_paper_trading.py --week 1

# 输出:
# - 信号统计
# - 准确率对比
# - 收益对比
# - 继续/调整决策
```

**Week 2评估**:
```bash
python3 analyze_paper_trading.py --week 2 --final

# 最终报告
```

---

#### 4.4 成功标准

**最低标准**:
- LSTM组准确率 ≥ 对照组 +5%
- 假阳性率 ≤ 对照组 -5%
- 收益率 ≥ 对照组

**理想标准**:
- LSTM组准确率 ≥ 对照组 +10%
- 假阳性率 ≤ 对照组 -10%
- 收益率 > 对照组 +20%

---

**阶段4总结**:
- 时间: 2周
- 决策点: 通过→正式启用，不通过→优化参数
- 输出: 纸上交易报告

---

## 📊 完整时间线

### Week 1（本周，2/10-2/14）

| 日期 | 任务 | 时间 | 状态 |
|------|------|------|------|
| 周一 | 处理中度问题（8支） | 2h | ⏳ |
| 周二 | 处理欠拟合（11支） | 2h | ⏳ |
| 周三 | 处理其他（5支） | 1h | ⏳ |
| 周四 | LSTM回测准备 | 2h | ⏳ |
| 周五 | LSTM回测执行 | 3h | ⏳ |

**周末**: 分析回测结果，决定是否继续

---

### Week 2（下周，2/17-2/21）

| 日期 | 任务 | 时间 | 状态 |
|------|------|------|------|
| 周一 | Smart Entry代码修改 | 3h | ⏳ |
| 周二 | 配置更新+测试 | 2h | ⏳ |
| 周三 | 集成测试 | 2h | ⏳ |
| 周四 | 纸上交易启动 | 1h | ⏳ |
| 周五 | 监控+调整 | 1h | ⏳ |

---

### Week 3-4（纸上交易，2/24-3/7）

| 周 | 任务 | 活动 |
|----|------|------|
| Week 3 | 纸上交易W1 | 每日监控+记录 |
| Week 4 | 纸上交易W2 | 评估+决策 |

---

## 🎯 成功里程碑

### Milestone 1: 模型改进完成 ✅

**条件**:
- 43/43支股票改进完成
- 平均改善≥70%
- 验证稳定性100%

**预计**: 2月11日（周三）

---

### Milestone 2: 回测验证通过 ✅

**条件**:
- LSTM准确率≥60%
- 精确率≥55%
- 可以继续集成

**预计**: 2月14日（周五）

---

### Milestone 3: 集成完成 ✅

**条件**:
- 代码修改完成
- 测试全部通过
- 纸上交易可启动

**预计**: 2月19日（周三）

---

### Milestone 4: 验证成功 ✅

**条件**:
- 纸上交易2周完成
- 效果达标
- 可以正式启用

**预计**: 3月7日（周五）

---

## 📋 所需脚本清单

### 已有 ✅

1. ✅ `fix_top4_stocks.py`
2. ✅ `batch_fix_severe_overfitting.py`
3. ✅ `fix_remaining_3_severe.py`
4. ✅ `validate_improved_stocks.py`

### 需要创建 ⏳

1. ⏳ `batch_fix_moderate.py` - 中度问题
2. ⏳ `batch_fix_underfitting.py` - 欠拟合
3. ⏳ `lstm_backtest.py` - LSTM回测
4. ⏳ `test_lstm_integration.py` - 集成测试
5. ⏳ `analyze_paper_trading.py` - 纸上交易分析

---

## 💡 风险和应对

### 风险1: LSTM准确率不足

**如果准确率<60%**:

**原因分析**:
- 模型架构问题
- 特征工程不足
- 数据质量问题
- 训练参数不当

**应对方案**:
1. 返回优化模型架构
2. 增加特征工程
3. 调整训练参数
4. 延后集成计划

---

### 风险2: 集成导致性能下降

**如果纸上交易效果差**:

**原因分析**:
- LSTM权重过高
- 阈值设置不当
- 特殊情况处理不当

**应对方案**:
1. 降低LSTM权重（25%→15%）
2. 调整阈值
3. 增加fallback机制
4. A/B测试优化

---

### 风险3: 系统复杂度增加

**维护成本上升**:

**应对方案**:
1. 完善文档
2. 模块化设计
3. 自动化测试
4. 监控告警

---

## ✅ 检查清单

### 开始前

- [ ] 已完成19支验证 ✅
- [ ] 理解整体计划
- [ ] 准备好时间（~20小时）
- [ ] 环境就绪

### 阶段1完成

- [ ] 43支全部改进
- [ ] 平均改善≥70%
- [ ] 验证全部通过
- [ ] 文档更新

### 阶段2完成

- [ ] 回测脚本完成
- [ ] 准确率≥60%
- [ ] 回测报告生成
- [ ] 决定继续集成

### 阶段3完成

- [ ] 代码修改完成
- [ ] 配置更新
- [ ] 测试通过
- [ ] 文档完整

### 阶段4完成

- [ ] 纸上交易2周
- [ ] 效果达标
- [ ] 最终报告
- [ ] 启用决策

---

## 🎯 总结

**总时长**: 约4周  
**总工作时间**: 约20小时  
**关键决策点**: 2个（回测+纸上交易）

**预期ROI**:
- 准确率提升: +10-20%
- 假信号减少: -15-25%
- 胜率提升: +10-15%

---

**准备好开始了吗？** 🚀

**第一步**: 创建批量处理脚本 → 开始改进剩余24支！
