from fastapi import FastAPI
from app.config import settings
from app.database import engine, Base
from app.routers import icp_router
from app.logging_config import setup_logging
import uvicorn

# 配置日志系统
setup_logging(level="INFO")

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 创建FastAPI应用实例
app = FastAPI(
    title="ICP备案查询服务",
    description="企业ICP备案域名查询API服务",
    version="1.0.0",
    debug=settings.debug
)

# 注册路由
app.include_router(icp_router, prefix="/icp", tags=["ICP查询"])


@app.get("/")
async def root():
    """根路径健康检查"""
    return {"message": "ICP备案查询服务运行正常", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "service": "icp-query-service"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )