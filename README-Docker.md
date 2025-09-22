# Docker 容器化部署指南

本文档介绍如何使用Docker将ICP备案查询服务部署到生产环境。

## 🚀 快速开始

### 1. 环境准备

确保服务器已安装以下软件：

```bash
# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.prod .env

# 编辑环境变量（重要！）
vim .env
```

**必须修改的配置项：**
- `MYSQL_ROOT_PASSWORD`: MySQL root密码
- `MYSQL_PASSWORD`: MySQL用户密码
- `API_KEY`: API认证密钥
- `CHINAZ_API_KEY`: 站长之家API密钥
- `TIANYANCHA_API_KEY`: 天眼查API密钥

### 3. 一键部署

```bash
# 执行部署脚本
./deployment/scripts/deploy.sh
```

部署脚本会自动完成：
- ✅ 检查依赖环境
- ✅ 创建必要目录
- ✅ 构建Docker镜像
- ✅ 启动所有服务
- ✅ 等待服务就绪
- ✅ 运行数据库迁移
- ✅ 显示服务状态

## 📋 服务架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Nginx       │    │   ICP App       │    │     MySQL       │
│   (反向代理)     │───▶│  (FastAPI)      │───▶│   (数据库)       │
│   Port: 80/443  │    │   Port: 8600    │    │   Port: 3306    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 服务组件

1. **Nginx** - 反向代理和负载均衡
   - 处理HTTP/HTTPS请求
   - 静态文件服务
   - 请求限流和安全防护

2. **ICP App** - 主应用服务
   - FastAPI Web框架
   - 异步处理API请求
   - 业务逻辑处理

3. **MySQL** - 数据存储
   - 持久化数据存储
   - 查询结果缓存
   - 数据备份和恢复

## 🛠️ 管理命令

### 启动服务

```bash
# 开发环境启动
./deployment/scripts/start.sh

# 生产环境启动
./deployment/scripts/start.sh prod
```

### 停止服务

```bash
# 开发环境停止
./deployment/scripts/stop.sh

# 生产环境停止
./deployment/scripts/stop.sh prod
```

### 查看服务状态

```bash
# 查看所有容器状态
docker-compose -f docker-compose.prod.yml ps

# 查看服务日志
docker-compose -f docker-compose.prod.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.prod.yml logs -f icp-app
```

### 数据库管理

```bash
# 连接MySQL数据库
docker-compose -f docker-compose.prod.yml exec mysql mysql -u root -p

# 运行数据库迁移
docker-compose -f docker-compose.prod.yml exec icp-app python -m alembic upgrade head

# 数据库备份
docker-compose -f docker-compose.prod.yml exec mysql mysqldump -u root -p icp_database > backup.sql
```

## 🔧 配置说明

### Docker Compose 配置

项目提供两个Docker Compose配置文件：

- `docker-compose.yml` - 开发环境配置
- `docker-compose.prod.yml` - 生产环境配置

### 环境变量

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `MYSQL_ROOT_PASSWORD` | MySQL root密码 | - | ✅ |
| `MYSQL_PASSWORD` | MySQL用户密码 | - | ✅ |
| `API_KEY` | API认证密钥 | - | ✅ |
| `CHINAZ_API_KEY` | 站长之家API密钥 | - | ✅ |
| `TIANYANCHA_API_KEY` | 天眼查API密钥 | - | ✅ |
| `DEBUG` | 调试模式 | false | ❌ |
| `CACHE_EXPIRE_DAYS` | 缓存过期天数 | 30 | ❌ |

### 数据持久化

生产环境数据存储在以下目录：
- MySQL数据: `/data/mysql`
- 应用日志: `/data/logs`
- Nginx日志: `/data/logs/nginx`

## 🔒 安全配置

### 1. 网络安全

- 使用Docker内部网络通信
- 只暴露必要的端口（80, 443）
- 配置防火墙规则

### 2. 应用安全

- 非root用户运行容器
- 安全的环境变量管理
- API密钥认证

### 3. 数据库安全

- 强密码策略
- 限制连接数
- 定期备份

## 📊 监控和日志

### 健康检查

所有服务都配置了健康检查：

```bash
# 检查应用健康状态
curl http://localhost/health

# 检查服务状态
docker-compose -f docker-compose.prod.yml ps
```

### 日志管理

```bash
# 查看实时日志
docker-compose -f docker-compose.prod.yml logs -f

# 查看错误日志
docker-compose -f docker-compose.prod.yml logs --tail=100 icp-app | grep ERROR
```

## 🚨 故障排除

### 常见问题

1. **服务启动失败**
   ```bash
   # 检查容器状态
   docker-compose -f docker-compose.prod.yml ps
   
   # 查看错误日志
   docker-compose -f docker-compose.prod.yml logs
   ```

2. **数据库连接失败**
   ```bash
   # 检查MySQL服务状态
   docker-compose -f docker-compose.prod.yml exec mysql mysqladmin ping
   
   # 检查网络连接
   docker-compose -f docker-compose.prod.yml exec icp-app ping mysql
   ```

3. **API请求失败**
   ```bash
   # 检查Nginx配置
   docker-compose -f docker-compose.prod.yml exec nginx nginx -t
   
   # 重启Nginx
   docker-compose -f docker-compose.prod.yml restart nginx
   ```

### 性能优化

1. **资源限制**
   - 在`docker-compose.prod.yml`中配置CPU和内存限制
   - 监控资源使用情况

2. **数据库优化**
   - 调整MySQL配置参数
   - 定期清理过期数据

3. **缓存策略**
   - 配置适当的缓存过期时间
   - 使用Redis缓存（可选）

## 📞 技术支持

如遇到问题，请检查：
1. 环境变量配置是否正确
2. 服务日志中的错误信息
3. 网络连接是否正常
4. 磁盘空间是否充足

更多技术细节请参考项目主README文档。