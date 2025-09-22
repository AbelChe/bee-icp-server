"""
应用程序配置模块
"""
import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用程序配置类"""
    
    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8600
    debug: bool = False
    
    # 数据库配置
    database_url: str = "mysql+pymysql://root:password@localhost:3306/icp_database"
    
    # API密钥配置
    chinaz_api_key: Optional[str] = None
    tianyancha_api_key: Optional[str] = None
    
    # 认证配置
    api_key: str = "your-secret-api-key-here"
    
    # 缓存配置
    cache_expire_days: int = 30
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 创建全局配置实例
settings = Settings()