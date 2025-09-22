#!/bin/bash

# ICP服务部署脚本
# 用于生产环境的Docker容器化部署

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker和Docker Compose
check_dependencies() {
    log_info "检查依赖..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    log_info "依赖检查完成"
}

# 检查环境变量文件
check_env_file() {
    log_info "检查环境变量文件..."
    
    if [ ! -f ".env" ]; then
        log_warn ".env文件不存在，从.env.example复制"
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_warn "请编辑.env文件配置正确的环境变量"
        else
            log_error ".env.example文件不存在"
            exit 1
        fi
    fi
    
    log_info "环境变量文件检查完成"
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."
    
    mkdir -p /data/mysql
    mkdir -p /data/logs/nginx
    mkdir -p logs
    
    log_info "目录创建完成"
}

# 构建镜像
build_images() {
    log_info "构建Docker镜像..."
    
    docker-compose -f docker-compose.prod.yml build --no-cache
    
    log_info "镜像构建完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    # 停止现有服务
    docker-compose -f docker-compose.prod.yml down
    
    # 启动服务
    docker-compose -f docker-compose.prod.yml up -d
    
    log_info "服务启动完成"
}

# 等待服务就绪
wait_for_services() {
    log_info "等待服务就绪..."
    
    # 等待MySQL就绪
    log_info "等待MySQL服务..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if docker-compose -f docker-compose.prod.yml exec -T mysql mysqladmin ping -h localhost --silent; then
            log_info "MySQL服务就绪"
            break
        fi
        sleep 2
        timeout=$((timeout-2))
    done
    
    if [ $timeout -le 0 ]; then
        log_error "MySQL服务启动超时"
        exit 1
    fi
    
    # 等待应用服务
    log_info "等待应用服务..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if curl -f http://localhost:8600/health &> /dev/null; then
            log_info "应用服务就绪"
            break
        fi
        sleep 2
        timeout=$((timeout-2))
    done
    
    if [ $timeout -le 0 ]; then
        log_error "应用服务启动超时"
        exit 1
    fi
    
    log_info "所有服务就绪"
}

# 运行数据库迁移
run_migrations() {
    log_info "运行数据库迁移..."
    
    docker-compose -f docker-compose.prod.yml exec -T icp-app python -m alembic upgrade head
    
    log_info "数据库迁移完成"
}

# 显示服务状态
show_status() {
    log_info "服务状态："
    docker-compose -f docker-compose.prod.yml ps
    
    log_info "服务访问地址："
    echo "  - 应用服务: http://localhost:8600"
    echo "  - Nginx代理: http://localhost"
    echo "  - 健康检查: http://localhost/health"
}

# 主函数
main() {
    log_info "开始部署ICP服务..."
    
    check_dependencies
    check_env_file
    create_directories
    build_images
    start_services
    wait_for_services
    run_migrations
    show_status
    
    log_info "部署完成！"
}

# 执行主函数
main "$@"