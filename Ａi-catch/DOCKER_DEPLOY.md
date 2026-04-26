# 🐳 Docker 一鍵部署指南

本文檔說明如何使用 Docker 部署 AI 股票分析系統 V3。

---

## 📋 前置需求

- Docker 20.10+
- Docker Compose 2.0+
- 至少 4GB RAM
- 10GB 磁碟空間

---

## 🚀 快速開始

### 1. 複製環境變數範例

```bash
cp env.docker.example .env
```

### 2. 編輯環境變數

```bash
nano .env  # 或使用任何文字編輯器
```

**必須修改的設定：**

```env
# 安全密鑰 (務必更改!)
SECRET_KEY=your-super-secret-key-change-this

# 資料庫密碼
DB_PASSWORD=your-strong-password
```

### 3. 一鍵啟動

```bash
# 建構並啟動所有服務
docker-compose up -d --build

# 查看日誌
docker-compose logs -f
```

### 4. 訪問系統

- **前端**: http://localhost:3000
- **後端 API**: http://localhost:8000
- **API 文檔**: http://localhost:8000/docs

---

## 📦 服務說明

| 服務 | 容器名稱 | 端口 | 說明 |
|------|----------|------|------|
| PostgreSQL | ai-stock-db | 5432 | 資料庫 |
| Backend | ai-stock-backend | 8000 | FastAPI 後端 |
| Frontend | ai-stock-frontend | 3000 | Next.js 前端 |

---

## 🔧 常用命令

### 啟動服務

```bash
# 啟動所有服務
docker-compose up -d

# 只啟動後端和資料庫
docker-compose up -d postgres backend
```

### 停止服務

```bash
# 停止所有服務
docker-compose down

# 停止並刪除數據卷 (⚠️ 會刪除資料庫!)
docker-compose down -v
```

### 查看狀態

```bash
# 查看運行中的容器
docker-compose ps

# 查看日誌
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 重新建構

```bash
# 重新建構單一服務
docker-compose build backend
docker-compose up -d backend

# 重新建構所有服務
docker-compose up -d --build
```

---

## 🔐 富邦 API 設定

如果需要使用富邦 API 即時數據：

### 1. 準備憑證

將您的富邦憑證檔案放置於 `certs/` 目錄：

```bash
mkdir -p certs
cp /path/to/your-cert.pfx certs/
```

### 2. 設定環境變數

編輯 `.env` 文件：

```env
FUBON_USER_ID=你的身分證號
FUBON_PASSWORD=你的密碼
FUBON_CERT_PATH=/app/certs/your-cert.pfx
FUBON_CERT_PASSWORD=憑證密碼
```

### 3. 重啟服務

```bash
docker-compose restart backend
```

---

## 🌐 生產環境部署

### 使用 Nginx 反向代理

1. 建立 nginx.conf：

```nginx
events {
    worker_connections 1024;
}

http {
    upstream frontend {
        server frontend:3000;
    }

    upstream backend {
        server backend:8000;
    }

    server {
        listen 80;
        server_name your-domain.com;

        location / {
            proxy_pass http://frontend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_cache_bypass $http_upgrade;
        }

        location /api {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        location /ws {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
```

2. 啟動生產環境配置：

```bash
docker-compose --profile production up -d
```

---

## 🔄 資料備份與還原

### 備份資料庫

```bash
docker exec ai-stock-db pg_dump -U stockai ai_stock_db > backup.sql
```

### 還原資料庫

```bash
cat backup.sql | docker exec -i ai-stock-db psql -U stockai ai_stock_db
```

---

## ❓ 故障排除

### 資料庫連線失敗

```bash
# 檢查資料庫是否運行
docker-compose ps postgres

# 查看資料庫日誌
docker-compose logs postgres
```

### 前端無法連接後端

```bash
# 確認後端健康狀態
curl http://localhost:8000/api/health

# 檢查網路連接
docker network inspect ai-stock-network
```

### 容器記憶體不足

編輯 docker-compose.yml 調整資源限制：

```yaml
deploy:
  resources:
    limits:
      memory: 4G
```

---

## 📝 版本資訊

- **系統版本**: V3.0
- **建立日期**: 2024-12-18
- **維護者**: AI Stock Team

---

Happy Trading! 📈🚀
