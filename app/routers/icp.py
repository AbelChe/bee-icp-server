from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.database import get_db
from app.schemas import ICPSearchResponse, ICPQueryParams
from app.services.icp_service import icp_service
from app.auth import auth_dependency

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/company/search", response_model=ICPSearchResponse)
async def search_company_icp(
    word: str = Query(..., min_length=1, description="企业名称"),
    force: Optional[int] = Query(0, description="是否强制查询，1为强制查询"),
    history: Optional[int] = Query(0, description="是否查询历史备案，1为查询历史备案"),
    db: Session = Depends(get_db),
    _: str = auth_dependency
):
    """
    企业名称查询ICP备案信息
    
    Args:
        word: 企业名称
        force: 是否强制查询（1为强制查询，0为使用缓存）
        history: 是否查询历史备案（1为查询历史备案，0为不查询历史备案）
        db: 数据库会话
        
    Returns:
        查询结果
    """
    try:
        logger.info(f"企业名称查询请求: {word}, 强制查询: {bool(force)}, 历史备案: {bool(history)}")
        
        # 调用服务层进行查询
        force_refresh = bool(force)
        include_history = bool(history)
        results = await icp_service.search_by_company(db, word, force_refresh, include_history)
        
        return ICPSearchResponse(
            status=0,
            error_message="",
            data=results
        )
        
    except Exception as e:
        logger.error(f"企业名称查询异常: {word}, 错误: {str(e)}")
        return ICPSearchResponse(
            status=1,
            error_message=f"查询失败: {str(e)}",
            data=[]
        )


@router.get("/company/search/history", response_model=ICPSearchResponse)
async def search_company_history_domains(
    word: str = Query(..., min_length=1, description="企业名称"),
    db: Session = Depends(get_db),
    _: str = auth_dependency
):
    """
    查询企业的历史域名
    
    Args:
        word: 企业名称
        db: 数据库会话
        
    Returns:
        企业的历史域名列表
    """
    try:
        logger.info(f"企业历史域名查询请求: {word}")
        
        # 调用服务层进行查询
        results = await icp_service.search_company_history_domains(db, word)
        
        return ICPSearchResponse(
            status=0,
            error_message="",
            data=results
        )
        
    except Exception as e:
        logger.error(f"企业历史域名查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/search", response_model=ICPSearchResponse)
async def search_domain_icp(
    word: str = Query(..., min_length=1, description="域名"),
    force: Optional[int] = Query(0, description="是否强制查询，1为强制查询"),
    history: Optional[int] = Query(0, description="是否查询历史备案，1为查询历史备案"),
    db: Session = Depends(get_db),
    _: str = auth_dependency
):
    """
    域名归属查询ICP备案信息
    
    Args:
        word: 域名
        force: 是否强制查询（1为强制查询，0为使用缓存）
        history: 是否查询历史备案（1为查询历史备案，0为不查询历史备案）
        db: 数据库会话
        
    Returns:
        查询结果
    """
    try:
        # 验证输入是否为域名或IP
        from app.utils.domain_utils import is_valid_domain_or_ip
        if not is_valid_domain_or_ip(word):
            return ICPSearchResponse(
                status=1,
                error_message="查询内容需为域名/IP",
                data=[]
            )
        
        logger.info(f"域名查询请求: {word}, 强制查询: {bool(force)}, 历史备案: {bool(history)}")
        
        # 调用服务层进行查询
        force_refresh = bool(force)
        include_history = bool(history)
        results = await icp_service.search_by_domain(db, word, force_refresh, include_history)
        
        return ICPSearchResponse(
            status=0,
            error_message="",
            data=results
        )
        
    except Exception as e:
        logger.error(f"域名查询异常: {word}, 错误: {str(e)}")
        return ICPSearchResponse(
            status=1,
            error_message=f"查询失败: {str(e)}",
            data=[]
        )


@router.get("/stats")
async def get_icp_stats(
    db: Session = Depends(get_db),
    _: str = auth_dependency
):
    """
    获取ICP数据统计信息
    
    Args:
        db: 数据库会话
        
    Returns:
        统计信息
    """
    try:
        from app.models import ICPRecord
        from sqlalchemy import func
        
        # 统计总记录数
        total_records = db.query(func.count(ICPRecord.id)).scalar()
        
        # 统计不同数据源的记录数
        chinaz_count = db.query(func.count(ICPRecord.id)).filter(
            ICPRecord.data_source == "chinaz"
        ).scalar()
        
        tianyancha_count = db.query(func.count(ICPRecord.id)).filter(
            ICPRecord.data_source == "tianyancha"
        ).scalar()
        
        # 统计唯一企业数
        unique_companies = db.query(func.count(func.distinct(ICPRecord.company_name))).scalar()
        
        # 统计唯一域名数
        unique_domains = db.query(func.count(func.distinct(ICPRecord.domain))).scalar()
        
        return {
            "status": 0,
            "data": {
                "total_records": total_records,
                "unique_companies": unique_companies,
                "unique_domains": unique_domains,
                "data_sources": {
                    "chinaz": chinaz_count,
                    "tianyancha": tianyancha_count
                }
            }
        }
        
    except Exception as e:
        logger.error(f"获取统计信息异常: {str(e)}")
        return {
            "status": 1,
            "error_message": f"获取统计信息失败: {str(e)}"
        }