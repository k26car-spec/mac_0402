"""
阶段1: 批量Baseline测试脚本
为所有ORB监控股票运行Baseline模型测试

执行: python3 batch_baseline_test.py
"""

import numpy as np
import pandas as pd
import json
import os
import sys
from datetime import datetime
import yfinance as yf
from sklearn.preprocessing import RobustScaler
from sklearn.model_selection import train_test_split

# 导入改进模型
from improved_stock_training import build_baseline_model, BaselineConfig
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
import tensorflow as tf

print("=" * 70)
print("🚀 阶段1: 批量Baseline测试")
print("=" * 70)
print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# ==================== 配置 ====================

# 项目根目录
PROJECT_ROOT = "/Users/Mac/Documents/ETF/AI/Ａi-catch"

# 数据参数
LOOKBACK_DAYS = 60
PREDICTION_DAYS = 5
DATA_PERIOD = "365d"

# 保存路径
RESULTS_DIR = f"{PROJECT_ROOT}/baseline_results"
os.makedirs(RESULTS_DIR, exist_ok=True)


# ==================== 数据加载函数 ====================

def load_orb_watchlist():
    """加载ORB监控列表"""
    watchlist_path = f"{PROJECT_ROOT}/data/orb_watchlist.json"
    
    try:
        with open(watchlist_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 检查JSON格式
        if isinstance(data, dict) and 'watchlist' in data:
            # 新格式: {"watchlist": ["2330", "2317", ...]}
            stock_codes = data['watchlist']
            # 创建代码到名称的映射（使用代码作为默认名称）
            watchlist = {code: f"股票{code}" for code in stock_codes}
        elif isinstance(data, dict):
            # 旧格式: {"2330": "台积电", ...}
            watchlist = data
        else:
            raise ValueError("不支持的JSON格式")
        
        print(f"✅ 成功加载ORB监控列表")
        print(f"   文件: {watchlist_path}")
        print(f"   股票数量: {len(watchlist)}")
        return watchlist
        
    except FileNotFoundError:
        print(f"⚠️ 找不到监控列表: {watchlist_path}")
        print(f"   使用示例股票代码...")
        # 返回示例股票
        return {
            "2330": "台积电",
            "2317": "鸿海",
            "2454": "联发科",
            "3037": "欣兴",
            "2303": "联电"
        }
    except Exception as e:
        print(f"❌ 加载监控列表失败: {str(e)}")
        print(f"   使用示例股票代码...")
        return {
            "2330": "台积电",
            "2317": "鸿海",
            "2454": "联发科"
        }


def fetch_stock_data(stock_code, period="365d"):
    """
    获取股票数据
    
    Parameters:
    -----------
    stock_code: str
        股票代码
    period: str
        数据期间
    
    Returns:
    --------
    DataFrame: 股票数据
    """
    try:
        # 台股需要加.TW后缀
        ticker_symbol = f"{stock_code}.TW"
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=period)
        
        if df.empty:
            print(f"  ⚠️ {stock_code}: 无法获取数据")
            return pd.DataFrame()
        
        return df
    
    except Exception as e:
        print(f"  ❌ {stock_code}: 数据获取失败 - {str(e)}")
        return pd.DataFrame()


def prepare_features(df):
    """准备特征"""
    # 移动平均
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    # 成交量比率
    df['Volume_Ratio'] = df['Volume'] / df['Volume'].rolling(20).mean()
    
    # 价格变化率
    df['Price_Change'] = df['Close'].pct_change()
    
    # 目标变量：未来5天收益率
    df['Future_Return'] = df['Close'].shift(-PREDICTION_DAYS) / df['Close'] - 1
    
    return df.dropna()


def create_sequences(data, lookback=60):
    """创建时间序列"""
    X, y = [], []
    
    for i in range(lookback, len(data)):
        X.append(data[i-lookback:i, :-1])  # 9个特征
        y.append(data[i-1, -1])  # 目标变量
    
    return np.array(X), np.array(y)


def prepare_stock_data(stock_code):
    """
    准备单支股票的训练数据
    
    Returns:
    --------
    tuple: (X_train, X_test, y_train, y_test) 或 None
    """
    # 获取数据
    df = fetch_stock_data(stock_code, DATA_PERIOD)
    
    if df.empty or len(df) < LOOKBACK_DAYS + 100:
        return None
    
    # 特征工程
    df = prepare_features(df)
    
    if len(df) < LOOKBACK_DAYS + 50:
        return None
    
    # 准备特征矩阵
    feature_cols = ['Close', 'MA5', 'MA20', 'MA60', 'RSI', 'MACD', 
                    'MACD_Signal', 'Volume_Ratio', 'Price_Change', 'Future_Return']
    data = df[feature_cols].values
    
    # 标准化
    scaler = RobustScaler()
    data_scaled = scaler.fit_transform(data)
    
    # 创建序列
    X, y = create_sequences(data_scaled, LOOKBACK_DAYS)
    
    # 分割训练/测试集
    # 更新: 从85/15改为75/25，基于8422诊断发现更平衡的分割更稳定
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, shuffle=False
    )
    
    return X_train, X_test, y_train, y_test


# ==================== Baseline测试 ====================

def test_baseline_single_stock(stock_code, stock_name):
    """
    测试单支股票的Baseline性能
    
    Returns:
    --------
    dict: 测试结果
    """
    print(f"\n{'─'*70}")
    print(f"📊 测试: {stock_code} ({stock_name})")
    print(f"{'─'*70}")
    
    try:
        # 准备数据
        print(f"  🔄 准备数据...")
        data = prepare_stock_data(stock_code)
        
        if data is None:
            print(f"  ⚠️ 数据不足，跳过")
            return {
                'stock_code': stock_code,
                'stock_name': stock_name,
                'success': False,
                'reason': 'insufficient_data'
            }
        
        X_train, X_test, y_train, y_test = data
        
        print(f"  ✅ 数据准备完成")
        print(f"     训练集: {X_train.shape[0]} 样本")
        print(f"     测试集: {X_test.shape[0]} 样本")
        
        # 构建Baseline模型
        print(f"  🔨 构建Baseline模型...")
        config = BaselineConfig()
        model = build_baseline_model(config)
        
        # Callbacks
        early_stop = EarlyStopping(
            monitor='val_mae',
            patience=20,
            restore_best_weights=True,
            verbose=0
        )
        
        reduce_lr = ReduceLROnPlateau(
            monitor='val_mae',
            factor=0.5,
            patience=8,
            min_lr=1e-7,
            verbose=0
        )
        
        # 训练
        print(f"  🚀 开始训练...")
        history = model.fit(
            X_train, y_train,
            validation_data=(X_test, y_test),
            epochs=config.max_epochs,
            batch_size=config.batch_size,
            callbacks=[early_stop, reduce_lr],
            verbose=0
        )
        
        # 评估
        test_loss, test_mae = model.evaluate(X_test, y_test, verbose=0)
        train_loss, train_mae = model.evaluate(X_train, y_train, verbose=0)
        
        epochs_trained = len(history.history['loss'])
        gap = test_mae - train_mae
        
        print(f"  ✅ 训练完成！")
        print(f"     训练MAE:   {train_mae:.6f}")
        print(f"     测试MAE:   {test_mae:.6f}")
        print(f"     差距:      {gap:+.6f}")
        print(f"     训练轮数:  {epochs_trained}")
        
        # 分类
        if test_mae < 0.06 and abs(gap) < 0.01:
            category = 'A'
            category_name = '训练良好'
            emoji = '✅'
        elif test_mae > 0.10 or abs(gap) > 0.03:
            category = 'B'
            category_name = '需要改进'
            emoji = '⚠️'
        else:
            category = 'C'
            category_name = '中等难度'
            emoji = '🤔'
        
        print(f"  {emoji} 分类: 类型{category} ({category_name})")
        
        return {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'success': True,
            'test_mae': float(test_mae),
            'train_mae': float(train_mae),
            'gap': float(gap),
            'epochs_trained': epochs_trained,
            'category': category,
            'category_name': category_name
        }
    
    except Exception as e:
        print(f"  ❌ 错误: {str(e)}")
        return {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'success': False,
            'reason': str(e)
        }


# ==================== 主程序 ====================

def main():
    """主程序"""
    
    # 加载监控列表
    watchlist = load_orb_watchlist()
    stock_codes = list(watchlist.keys())
    total_stocks = len(stock_codes)
    
    print(f"\n📋 准备测试 {total_stocks} 支股票")
    print(f"预计时间: {total_stocks * 3} 分钟\n")
    
    input("按 Enter 开始测试...")
    
    # 批量测试
    all_results = {}
    success_count = 0
    failed_count = 0
    
    for i, stock_code in enumerate(stock_codes, 1):
        stock_name = watchlist.get(stock_code, stock_code)
        
        print(f"\n{'='*70}")
        print(f"进度: [{i}/{total_stocks}] ({i/total_stocks*100:.1f}%)")
        print(f"{'='*70}")
        
        result = test_baseline_single_stock(stock_code, stock_name)
        all_results[stock_code] = result
        
        if result['success']:
            success_count += 1
        else:
            failed_count += 1
        
        # 保存中间结果（防中断）
        temp_file = f"{RESULTS_DIR}/baseline_results_temp.json"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    # 保存最终结果
    final_file = f"{RESULTS_DIR}/baseline_results_final.json"
    with open(final_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    # 统计
    print(f"\n\n{'='*70}")
    print(f"📊 测试完成统计")
    print(f"{'='*70}")
    print(f"总股票数:   {total_stocks}")
    print(f"测试成功:   {success_count} ✅")
    print(f"测试失败:   {failed_count} ❌")
    print(f"成功率:     {success_count/total_stocks*100:.1f}%")
    
    # 分类统计
    if success_count > 0:
        successful_results = [r for r in all_results.values() if r['success']]
        type_a = len([r for r in successful_results if r.get('category') == 'A'])
        type_b = len([r for r in successful_results if r.get('category') == 'B'])
        type_c = len([r for r in successful_results if r.get('category') == 'C'])
        
        print(f"\n分类分布:")
        print(f"  类型A (训练良好): {type_a:2d} 支 ({type_a/success_count*100:5.1f}%) ✅")
        print(f"  类型B (需要改进): {type_b:2d} 支 ({type_b/success_count*100:5.1f}%) ⚠️")
        print(f"  类型C (中等难度): {type_c:2d} 支 ({type_c/success_count*100:5.1f}%) 🤔")
    
    print(f"\n📄 结果已保存:")
    print(f"   {final_file}")
    
    print(f"\n{'='*70}")
    print(f"✅ 阶段1完成!")
    print(f"{'='*70}")
    
    print(f"\n💡 下一步:")
    print(f"   1. 查看结果文件: {final_file}")
    print(f"   2. 运行阶段2自动分类:")
    print(f"      python3 run_stage2_classification.py")
    
    return all_results


if __name__ == "__main__":
    try:
        results = main()
    except KeyboardInterrupt:
        print(f"\n\n⚠️ 用户中断")
        print(f"中间结果已保存至: {RESULTS_DIR}/baseline_results_temp.json")
    except Exception as e:
        print(f"\n\n❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()
