#!/bin/bash

# ICP服务快速启动脚本

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# 检查环境变量文件
if [ ! -f ".env" ]; then
    log_warn ".env文件不存在，从.env.example复制"
    cp .env.example .env
    log_warn "请编辑.env文件配置正确的环境变量"
fi

# 创建日志目录
mkdir -p logs

# 启动服务
log_info "启动ICP服务..."

if [ "$1" = "prod" ]; then
    log_info "使用生产环境配置启动"
    docker-compose -f docker-compose.prod.yml up -d
else
    log_info "使用开发环境配置启动"
    docker-compose up -d
fi

log_info "服务启动完成"
log_info "访问地址: http://localhost"
log_info "健康检查: http://localhost/health"