from sqlalchemy import Column, Integer, String, DateTime, Text, Index, Boolean
from sqlalchemy.sql import func
from app.database import Base


class ICPRecord(Base):
    """ICP备案记录模型"""
    __tablename__ = "icp_records"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 基础信息
    company_name = Column(String(255), nullable=False, comment="公司名称")
    domain = Column(String(255), nullable=False, comment="备案域名")
    service_licence = Column(String(100), nullable=True, comment="服务许可证号")
    site_license = Column(String(100), nullable=True, comment="网站许可证号")
    
    # 详细信息
    site_name = Column(String(255), nullable=True, comment="网站名称")
    company_type = Column(String(50), nullable=True, comment="公司类型")
    owner = Column(String(255), nullable=True, comment="所有者")
    limit_access = Column(String(10), nullable=True, comment="是否限制访问")
    verify_time = Column(String(50), nullable=True, comment="审核时间")
    
    # 备案状态
    is_historical = Column(Boolean, default=False, nullable=False, comment="是否为历史备案")
    
    # 数据来源和更新时间
    data_source = Column(String(50), nullable=False, comment="数据来源(chinaz/tianyancha)")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 原始数据备份
    raw_data = Column(Text, nullable=True, comment="原始API返回数据")
    
    # 创建索引
    __table_args__ = (
        Index('idx_company_name', 'company_name'),
        Index('idx_domain', 'domain'),
        Index('idx_service_licence', 'service_licence'),
        Index('idx_updated_at', 'updated_at'),
        Index('idx_company_domain', 'company_name', 'domain'),
        Index('idx_is_historical', 'is_historical'),
    )