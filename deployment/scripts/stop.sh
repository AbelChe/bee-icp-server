#!/bin/bash

# ICP服务停止脚本

set -e

# 颜色定义
GREEN='\033[0;32m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_info "停止ICP服务..."

if [ "$1" = "prod" ]; then
    log_info "停止生产环境服务"
    docker-compose -f docker-compose.prod.yml down
else
    log_info "停止开发环境服务"
    docker-compose down
fi

log_info "服务已停止"