#!/bin/bash

# Redis 快速安装脚本（macOS）
# 不依赖 Homebrew

echo "🚀 Redis 快速安装"
echo "=================================="
echo ""

# 检查是否已经安装
if command -v redis-server &> /dev/null; then
    echo "✅ Redis 已安装"
    redis-server --version
    echo ""
    echo "启动 Redis："
    echo "redis-server &"
    exit 0
fi

# 方案 1: 使用 Homebrew（如果可用）
if command -v brew &> /dev/null; then
    echo "📦 使用 Homebrew 安装..."
    brew install redis
    brew services start redis
    redis-cli ping
    exit 0
fi

# 方案 2: 从源码编译（快速方式）
echo "📥 从源码安装 Redis..."
echo ""

# 创建临时目录
TEMP_DIR="/tmp/redis-install"
mkdir -p $TEMP_DIR
cd $TEMP_DIR

# 下载 Redis
echo "下载 Redis 7.2..."
curl -L https://download.redis.io/releases/redis-7.2.4.tar.gz -o redis.tar.gz

# 解压
echo "解压..."
tar xzf redis.tar.gz
cd redis-7.2.4

# 编译
echo "编译（这可能需要几分钟）..."
make

# 安装到用户目录
echo "安装..."
mkdir -p ~/redis/bin
cp src/redis-server ~/redis/bin/
cp src/redis-cli ~/redis/bin/

# 添加到 PATH
echo ""
echo "✅ Redis 安装完成！"
echo ""
echo "添加到 PATH:"
echo 'export PATH="$HOME/redis/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

echo ""
echo "启动 Redis:"
echo "  ~/redis/bin/redis-server &"
echo ""
echo "测试连接:"
echo "  ~/redis/bin/redis-cli ping"
