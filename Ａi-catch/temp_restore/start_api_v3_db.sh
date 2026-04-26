#!/bin/bash

# 启动 FastAPI v3.0（带数据库集成）
# 使用 uvicorn 正确启动

cd "$(dirname "$0")/backend-v3"

# 启动虚擬環境
source venv/bin/activate

# 使用 uvicorn 启动（会自动设置 PYTHONPATH）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
