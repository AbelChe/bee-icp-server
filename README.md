# ICP备案查询服务

企业ICP备案域名查询API服务，支持根据企业名称查询备案域名，以及根据域名查询所属企业。

## 功能特性

- 🔍 **企业名称查询**: 根据企业名称查询ICP备案域名
- 🌐 **域名归属查询**: 根据域名查询所属备案企业
- 💾 **数据本地化**: 自动缓存查询结果到本地数据库
- 🔄 **智能缓存**: 支持数据过期检查和强制刷新
- 📊 **多数据源**: 集成站长之家和天眼查API
- ⚡ **高性能**: 基于FastAPI构建，支持异步处理

## 技术栈

- **编程语言**: Python 3.8+
- **Web框架**: FastAPI
- **数据库**: MySQL
- **ORM**: SQLAlchemy
- **HTTP客户端**: httpx

## 安装部署

### 1. 环境准备

```bash
# 创建conda环境
conda create -n icp-server python=3.8
conda activate icp-server

# 安装依赖
pip install -r requirements.txt
```

### 2. 数据库配置

创建MySQL数据库：

```sql
CREATE DATABASE icp_database CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. 环境变量配置

复制环境变量示例文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置数据库连接和API密钥：

```env
# 数据库配置
DATABASE_URL=mysql+pymysql://username:password@localhost:3306/icp_database

# API 密钥配置
CHINAZ_API_KEY=your_chinaz_api_key_here
TIANYANCHA_API_KEY=your_tianyancha_api_key_here

# 服务配置
HOST=0.0.0.0
PORT=8600
DEBUG=True

# 缓存配置
CACHE_EXPIRE_DAYS=30

# 认证配置
API_KEY=your-secret-api-key-here
```

### 4. 启动服务

```bash
python main.py
```

服务将在 `http://localhost:8600` 启动。

## API接口

> **注意**: 所有API接口都需要在请求头中添加 `AuthKey` 进行认证。

### 认证方式

在请求头中添加 `AuthKey` 字段：

```bash
curl -H "AuthKey: your-secret-api-key" "http://localhost:8600/icp/company/search?word=百度"
```

### 1. 企业名称查询

**接口**: `GET /icp/company/search`

**参数**:
- `word` (必填): 企业名称
- `force` (可选): 是否强制查询，1为强制查询
- `history` (可选): 是否查询历史备案，1为查询历史备案，0为不查询历史备案

**示例**:
```bash
curl -H "AuthKey: your-secret-api-key" "http://localhost:8600/icp/company/search?word=百度&force=0&history=0"
```

**响应**:
```json
{
  "status": 0,
  "error_message": "",
  "data": [
    {
      "name": "北京百度网讯科技有限公司",
      "domain": "baidu.com",
      "service_licence": "京ICP证030173号-1",
      "last_update": "2025-01-19 15:30:11",
      "is_historical": false
    }
  ]
}
```

### 2. 企业历史域名查询

**接口**: `GET /icp/company/search/history`

**参数**:
- `word` (必填): 企业名称

**示例**:
```bash
curl -H "AuthKey: your-secret-api-key" "http://localhost:8600/icp/company/search/history?word=北京百度网讯科技有限公司"
```

**响应**:
```json
{
  "status": 0,
  "error_message": "",
  "data": [
    {
      "name": "北京百度网讯科技有限公司",
      "domain": "test-historical.com",
      "service_licence": "ICP备12345678号",
      "last_update": "2025-09-19 18:58:21",
      "is_historical": true
    }
  ]
}
```

### 3. 域名归属查询

**接口**: `GET /icp/search`

**参数**:
- `word` (必填): 域名
- `force` (可选): 是否强制查询，1为强制查询
- `history` (可选): 是否查询历史备案，1为查询历史备案，0为不查询历史备案

**示例**:
```bash
curl -H "AuthKey: your-secret-api-key" "http://localhost:8600/icp/search?word=baidu.com&force=0&history=0"
```

**响应**:
```json
{
  "status": 0,
  "error_message": "",
  "data": [
    {
      "name": "北京百度网讯科技有限公司",
      "domain": "baidu.com",
      "service_licence": "京ICP证030173号-1",
      "last_update": "2025-01-19 15:30:11",
      "is_historical": false
    }
  ]
}
```

### 4. 数据统计

**接口**: `GET /icp/stats`

**示例**:
```bash
curl -H "AuthKey: your-secret-api-key" "http://localhost:8600/icp/stats"
```

### 5. 健康检查

**接口**: `GET /health`

**示例**:
```bash
curl "http://localhost:8600/health"
```

## 数据源说明

### 站长之家API
- 支持企业名称和域名查询
- 返回详细的ICP备案信息
- 需要配置API密钥

### 天眼查API
- 支持企业名称查询
- 需要先搜索企业获取ID，再查询ICP信息
- 需要配置API密钥

## 缓存机制

- 查询结果自动缓存到本地MySQL数据库
- 默认缓存30天，可通过 `CACHE_EXPIRE_DAYS` 配置
- 支持 `force=1` 参数强制刷新缓存
- 自动检查数据过期时间

## 项目结构

```
bee-icp-server/
├── app/
│   ├── __init__.py
│   ├── config.py          # 配置管理
│   ├── database.py        # 数据库连接
│   ├── models.py          # 数据库模型
│   ├── schemas.py         # Pydantic模型
│   ├── routers/           # API路由
│   │   ├── __init__.py
│   │   └── icp.py
│   └── services/          # 业务逻辑
│       ├── __init__.py
│       ├── external_api.py # 外部API调用
│       └── icp_service.py  # ICP查询服务
├── main.py               # 应用入口
├── requirements.txt      # 依赖包
├── .env.example         # 环境变量示例
└── README.md           # 项目说明
```

## 开发说明

### 添加新的数据源

1. 在 `app/services/external_api.py` 中添加新的API调用方法
2. 在 `app/services/icp_service.py` 中添加数据转换逻辑
3. 更新数据库模型（如需要）

### 自定义缓存策略

修改 `app/services/icp_service.py` 中的 `_is_data_expired` 方法。

## 注意事项

1. 请确保API密钥的安全性，不要提交到版本控制系统
2. 建议在生产环境中使用HTTPS
3. 根据API调用频率限制合理设置缓存时间
4. 定期备份数据库数据