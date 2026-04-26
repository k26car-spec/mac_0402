#!/bin/bash
# ========================================
# AI 股票分析系統 V3 - Docker 部署腳本
# ========================================

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印帶顏色的訊息
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 標題
echo ""
echo "================================================"
echo "   🐳 AI 股票分析系統 V3 - Docker 部署工具"
echo "================================================"
echo ""

# 檢查 Docker
check_docker() {
    print_info "檢查 Docker 環境..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安裝，請先安裝 Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose 未安裝"
        exit 1
    fi
    
    print_success "Docker 環境正常"
}

# 檢查環境變數
check_env() {
    print_info "檢查環境變數..."
    
    if [ ! -f ".env" ]; then
        print_warning ".env 檔案不存在"
        if [ -f "env.docker.example" ]; then
            print_info "從範例檔案建立 .env..."
            cp env.docker.example .env
            print_success "已建立 .env 檔案，請編輯設定後重新執行"
            exit 0
        fi
    fi
    
    print_success "環境變數檔案存在"
}

# 建構映像
build_images() {
    print_info "建構 Docker 映像..."
    
    docker-compose build --no-cache
    
    print_success "映像建構完成"
}

# 啟動服務
start_services() {
    print_info "啟動服務..."
    
    docker-compose up -d
    
    print_success "服務啟動中..."
    
    # 等待服務就緒
    print_info "等待服務就緒..."
    sleep 10
    
    # 檢查服務狀態
    docker-compose ps
}

# 停止服務
stop_services() {
    print_info "停止服務..."
    docker-compose down
    print_success "服務已停止"
}

# 查看日誌
show_logs() {
    docker-compose logs -f
}

# 健康檢查
health_check() {
    print_info "執行健康檢查..."
    
    # 檢查後端
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        print_success "後端 API: ✅ 正常 (http://localhost:8000)"
    else
        print_error "後端 API: ❌ 無回應"
    fi
    
    # 檢查前端
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        print_success "前端介面: ✅ 正常 (http://localhost:3000)"
    else
        print_error "前端介面: ❌ 無回應"
    fi
    
    # 檢查資料庫
    if docker exec ai-stock-db pg_isready -U stockai > /dev/null 2>&1; then
        print_success "資料庫: ✅ 正常"
    else
        print_error "資料庫: ❌ 無回應"
    fi
}

# 顯示使用說明
show_help() {
    echo "使用方式: $0 [選項]"
    echo ""
    echo "選項:"
    echo "  build     建構 Docker 映像"
    echo "  start     啟動所有服務"
    echo "  stop      停止所有服務"
    echo "  restart   重啟所有服務"
    echo "  logs      查看服務日誌"
    echo "  status    查看服務狀態"
    echo "  health    執行健康檢查"
    echo "  clean     清理 Docker 資源"
    echo "  help      顯示此說明"
    echo ""
}

# 清理資源
clean_resources() {
    print_warning "這將刪除所有容器、映像和數據卷"
    read -p "確定要繼續嗎？(y/N) " confirm
    
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        docker-compose down -v --rmi all
        print_success "清理完成"
    else
        print_info "取消操作"
    fi
}

# 主函數
main() {
    case "$1" in
        build)
            check_docker
            check_env
            build_images
            ;;
        start)
            check_docker
            check_env
            start_services
            health_check
            ;;
        stop)
            stop_services
            ;;
        restart)
            stop_services
            start_services
            health_check
            ;;
        logs)
            show_logs
            ;;
        status)
            docker-compose ps
            ;;
        health)
            health_check
            ;;
        clean)
            clean_resources
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo "🚀 互動模式"
            echo ""
            echo "請選擇操作："
            echo "  1) 建構並啟動 (首次部署)"
            echo "  2) 啟動服務"
            echo "  3) 停止服務"
            echo "  4) 查看狀態"
            echo "  5) 查看日誌"
            echo "  6) 健康檢查"
            echo "  0) 退出"
            echo ""
            read -p "請輸入選項: " choice
            
            case $choice in
                1)
                    check_docker
                    check_env
                    build_images
                    start_services
                    health_check
                    ;;
                2)
                    start_services
                    ;;
                3)
                    stop_services
                    ;;
                4)
                    docker-compose ps
                    ;;
                5)
                    show_logs
                    ;;
                6)
                    health_check
                    ;;
                0)
                    exit 0
                    ;;
                *)
                    print_error "無效選項"
                    ;;
            esac
            ;;
    esac
}

# 執行主函數
main "$@"
