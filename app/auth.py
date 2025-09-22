from fastapi import HTTPException, Header, Depends
from typing import Optional
from app.config import settings


def verify_api_key(x_api_key: Optional[str] = Header(None, alias="AuthKey")) -> str:
    """
    验证API密钥
    
    Args:
        x_api_key: 请求头中的API密钥
        
    Returns:
        验证通过的API密钥
        
    Raises:
        HTTPException: 当API密钥无效或缺失时抛出401错误
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API密钥缺失，请在请求头中添加 AuthKey"
        )
    
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=401,
            detail="API密钥无效"
        )
    
    return x_api_key


# 认证依赖
auth_dependency = Depends(verify_api_key)