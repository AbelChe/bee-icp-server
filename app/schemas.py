from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ICPRecordBase(BaseModel):
    """ICP记录基础模型"""
    name: str = Field(..., description="公司名称")
    domain: str = Field(..., description="备案域名")
    service_licence: Optional[str] = Field(None, description="服务许可证号")
    last_update: str = Field(..., description="最后更新时间")
    is_historical: bool = Field(False, description="是否为历史备案")


class ICPSearchResponse(BaseModel):
    """ICP查询响应模型"""
    status: int = Field(..., description="状态码，0代表正常，1代表异常")
    error_message: str = Field("", description="异常信息")
    data: List[ICPRecordBase] = Field([], description="查询结果数据")


class ICPQueryParams(BaseModel):
    """ICP查询参数模型"""
    word: str = Field(..., min_length=1, description="查询关键词")
    force: Optional[int] = Field(0, description="是否强制查询，1为强制查询")


# 外部API响应模型
class ChinazAPIResponse(BaseModel):
    """站长之家API响应模型"""
    StateCode: int
    Reason: str
    Result: List[dict]


class TianyanchaSearchResponse(BaseModel):
    """天眼查搜索API响应模型"""
    error_code: int
    reason: str
    result: dict


class TianyanchaICPResponse(BaseModel):
    """天眼查ICP查询API响应模型"""
    state: str
    message: str
    errorCode: int
    data: dict