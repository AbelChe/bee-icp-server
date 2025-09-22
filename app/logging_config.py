"""
日志配置模块
"""
import logging
import sys
from typing import Optional


def setup_logging(level: str = "INFO", format_string: Optional[str] = None) -> None:
    """
    配置应用程序的日志系统
    
    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: 自定义日志格式字符串
    """
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 获取日志级别
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # 配置根日志器
    logging.basicConfig(
        level=log_level,
        format=format_string,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ],
        force=True  # 强制重新配置，覆盖已有配置
    )
    
    # 设置第三方库的日志级别，避免过多输出
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    
    # 记录配置完成
    logger = logging.getLogger(__name__)
    logger.info(f"日志系统已配置，级别: {level}")


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志器
    
    Args:
        name: 日志器名称
        
    Returns:
        配置好的日志器实例
    """
    return logging.getLogger(name)