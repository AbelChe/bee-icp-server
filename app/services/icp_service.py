import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models import ICPRecord
from app.schemas import ICPRecordBase
from app.services.external_api import external_api_service
from app.config import settings
from app.utils.domain_utils import extract_root_domain, is_gov_domain, get_domain_hierarchy, normalize_domain

logger = logging.getLogger(__name__)


class ICPService:
    """ICP查询服务"""
    
    def __init__(self):
        self.cache_expire_days = settings.cache_expire_days
    
    def _is_data_expired(self, updated_at: datetime) -> bool:
        """
        检查数据是否过期
        
        Args:
            updated_at: 数据更新时间
            
        Returns:
            是否过期
        """
        expire_time = datetime.now() - timedelta(days=self.cache_expire_days)
        return updated_at < expire_time
    
    def _convert_chinaz_data(self, data: Dict, source: str = "chinaz") -> Dict:
        """
        转换站长之家API数据格式
        
        Args:
            data: 原始API数据
            source: 数据来源
            
        Returns:
            转换后的数据
        """
        return {
            "company_name": data.get("UnitName", ""),
            "domain": data.get("Domain", ""),
            "service_licence": data.get("ServiceLicence", ""),
            "site_license": data.get("SiteLicense", ""),
            "site_name": data.get("SiteName", ""),
            "company_type": data.get("CompanyType", ""),
            "owner": data.get("Owner", ""),
            "limit_access": data.get("LimitAccess", ""),
            "verify_time": data.get("VerifyTime", ""),
            "data_source": source,
            "raw_data": json.dumps(data, ensure_ascii=False)
        }
    
    def _convert_tianyancha_data(self, data: Dict, source: str = "tianyancha") -> Dict:
        """
        转换天眼查API数据格式
        
        Args:
            data: 原始API数据
            source: 数据来源
            
        Returns:
            转换后的数据
        """
        return {
            "company_name": data.get("companyName", ""),
            "domain": data.get("ym", ""),
            "service_licence": data.get("liscense", ""),
            "site_license": "",
            "site_name": data.get("webName", ""),
            "company_type": data.get("companyType", ""),
            "owner": "",
            "limit_access": "",
            "verify_time": data.get("examineDate", ""),
            "data_source": source,
            "raw_data": json.dumps(data, ensure_ascii=False)
        }
    
    def _save_records_to_db(self, db: Session, records_data: List[Dict], company_name: str = None) -> List[ICPRecord]:
        """
        保存记录到数据库，遵循数据源优先级原则，并处理历史备案标记
        
        Args:
            db: 数据库会话
            records_data: 记录数据列表
            company_name: 查询的公司名称，用于历史备案标记
            
        Returns:
            保存的记录列表
        """
        saved_records = []
        
        # 定义数据源优先级（数字越小优先级越高）
        source_priority = {
            "chinaz": 1,      # 站长之家 - 最高优先级
            "tianyancha": 2   # 天眼查 - 次优先级
        }
        
        # 如果提供了公司名称，处理历史备案标记
        if company_name:
            # 获取当前查询结果中的所有域名
            current_domains = {record_data["domain"] for record_data in records_data}
            
            # 查询该公司之前的所有非历史备案记录
            existing_company_records = db.query(ICPRecord).filter(
                and_(
                    ICPRecord.company_name == company_name,
                    ICPRecord.is_historical == False
                )
            ).all()
            
            # 标记不在当前查询结果中的域名为历史备案
            for existing_record in existing_company_records:
                if existing_record.domain not in current_domains:
                    existing_record.is_historical = True
                    existing_record.updated_at = datetime.now()
                    logger.info(f"标记域名 {existing_record.domain} 为历史备案，公司: {company_name}")
        
        for record_data in records_data:
            # 检查是否已存在相同记录（公司名称、域名、服务许可证号都匹配）
            existing_record = db.query(ICPRecord).filter(
                and_(
                    ICPRecord.company_name == record_data["company_name"],
                    ICPRecord.domain == record_data["domain"],
                    ICPRecord.service_licence == record_data["service_licence"]
                )
            ).first()
            
            if existing_record:
                # 检查数据源优先级
                existing_priority = source_priority.get(existing_record.data_source, 999)
                new_priority = source_priority.get(record_data["data_source"], 999)
                
                # 只有当新数据源优先级更高时才更新
                if new_priority < existing_priority:
                    logger.info(f"更新记录，数据源从 {existing_record.data_source} 更新为 {record_data['data_source']}")
                    for key, value in record_data.items():
                        if key != "created_at":
                            setattr(existing_record, key, value)
                    existing_record.updated_at = datetime.now()
                    # 如果记录被更新，说明域名重新激活，取消历史备案标记
                    existing_record.is_historical = False
                else:
                    logger.info(f"保持现有记录，数据源 {existing_record.data_source} 优先级高于 {record_data['data_source']}")
                    # 即使不更新数据，也要取消历史备案标记（因为域名重新出现在查询结果中）
                    if existing_record.is_historical:
                        existing_record.is_historical = False
                        existing_record.updated_at = datetime.now()
                        logger.info(f"域名 {existing_record.domain} 重新激活，取消历史备案标记")
                
                saved_records.append(existing_record)
            else:
                # 检查该域名是否被其他公司使用过
                domain_used_by_others = db.query(ICPRecord).filter(
                    and_(
                        ICPRecord.domain == record_data["domain"],
                        ICPRecord.company_name != record_data["company_name"]
                    )
                ).first()
                
                if domain_used_by_others:
                    logger.info(f"域名 {record_data['domain']} 从公司 {domain_used_by_others.company_name} 转移到 {record_data['company_name']}")
                
                # 创建新记录（确保is_historical为False）
                record_data["is_historical"] = False
                new_record = ICPRecord(**record_data)
                db.add(new_record)
                saved_records.append(new_record)
                logger.info(f"创建新记录，数据源: {record_data['data_source']}")
        
        db.commit()
        return saved_records
    
    def _format_response_data(self, records: List[ICPRecord]) -> List[ICPRecordBase]:
        """
        格式化响应数据
        
        Args:
            records: 数据库记录列表
            
        Returns:
            格式化后的响应数据
        """
        result = []
        for record in records:
            result.append(ICPRecordBase(
                name=record.company_name,
                domain=record.domain,
                service_licence=record.service_licence or "",
                last_update=record.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                is_historical=record.is_historical
            ))
        return result
    
    async def search_by_company(self, db: Session, company_name: str, force_refresh: bool = False, include_history: bool = False) -> List[ICPRecordBase]:
        """
        根据企业名称查询ICP备案信息
        
        Args:
            db: 数据库会话
            company_name: 企业名称
            force_refresh: 是否强制刷新
            include_history: 是否包含历史备案
            
        Returns:
            查询结果列表
        """
        # 如果不强制刷新，先查询本地数据库
        if not force_refresh:
            query = db.query(ICPRecord).filter(
                ICPRecord.company_name == company_name
            )
            
            # 根据include_history参数决定是否过滤历史备案
            if not include_history:
                query = query.filter(ICPRecord.is_historical == False)
            
            local_records = query.all()
            
            # 检查数据是否过期
            valid_records = []
            for record in local_records:
                if not self._is_data_expired(record.updated_at):
                    valid_records.append(record)
            
            if valid_records:
                logger.info(f"从本地数据库返回企业查询结果: {company_name}, 包含历史备案: {include_history}")
                return self._format_response_data(valid_records)
        
        # 调用外部API获取数据，按优先级顺序处理
        logger.info(f"调用外部API查询企业: {company_name}")
        all_records_data = []
        
        # 第一优先级：调用站长之家API
        chinaz_data = await external_api_service.query_chinaz_by_company(company_name)
        if chinaz_data:
            logger.info(f"站长之家API返回 {len(chinaz_data)} 条记录")
            for item in chinaz_data:
                all_records_data.append(self._convert_chinaz_data(item))
        
        # 第二优先级：调用天眼查API
        tianyancha_data = await external_api_service.query_tianyancha_by_company(company_name)
        if tianyancha_data:
            logger.info(f"天眼查API返回 {len(tianyancha_data)} 条记录")
            for item in tianyancha_data:
                all_records_data.append(self._convert_tianyancha_data(item))
        
        # 保存到数据库（会自动处理数据源优先级和历史备案标记）
        if all_records_data:
            saved_records = self._save_records_to_db(db, all_records_data, company_name)
            
            # 根据include_history参数过滤结果
            if not include_history:
                saved_records = [record for record in saved_records if not record.is_historical]
            
            return self._format_response_data(saved_records)
        
        return []
    
    def _is_domain_match(self, returned_domain: str, query_root_domain: str) -> bool:
        """
        校验返回的域名是否属于查询域名的根域名
        
        Args:
            returned_domain: API返回的域名
            query_root_domain: 查询的根域名
            
        Returns:
            是否匹配
        """
        if not returned_domain or not query_root_domain:
            return False
        
        # 标准化域名
        returned_domain = normalize_domain(returned_domain)
        query_root_domain = normalize_domain(query_root_domain)
        
        # 提取两个域名的根域名进行比较
        returned_root = extract_root_domain(returned_domain)
        query_root = extract_root_domain(query_root_domain)
        
        return returned_root == query_root
    
    async def _fetch_and_cache_company_records(self, db: Session, company_name: str) -> None:
        """
        获取并缓存单位的所有备案信息
        
        Args:
            db: 数据库会话
            company_name: 单位名称
        """
        try:
            # 检查是否已有该单位的缓存数据且未过期
            existing_records = db.query(ICPRecord).filter(
                ICPRecord.company_name == company_name
            ).all()
            
            # 如果有未过期的数据，跳过查询
            if existing_records:
                for record in existing_records:
                    if not self._is_data_expired(record.updated_at):
                        logger.info(f"单位 {company_name} 已有未过期的缓存数据，跳过查询")
                        return
            
            # 调用外部API获取该单位的所有备案信息
            logger.info(f"获取单位所有备案信息: {company_name}")
            all_records_data = []
            
            # 第一优先级：调用站长之家API
            chinaz_data = await external_api_service.query_chinaz_by_company(company_name)
            if chinaz_data:
                logger.info(f"站长之家API返回 {len(chinaz_data)} 条记录")
                for item in chinaz_data:
                    all_records_data.append(self._convert_chinaz_data(item))
            
            # 第二优先级：调用天眼查API
            tianyancha_data = await external_api_service.query_tianyancha_by_company(company_name)
            if tianyancha_data:
                logger.info(f"天眼查API返回 {len(tianyancha_data)} 条记录")
                for item in tianyancha_data:
                    all_records_data.append(self._convert_tianyancha_data(item))
            
            # 保存到数据库（会自动处理数据源优先级和历史备案标记）
            if all_records_data:
                self._save_records_to_db(db, all_records_data, company_name)
                logger.info(f"成功缓存单位 {company_name} 的 {len(all_records_data)} 条备案信息")
            else:
                logger.info(f"未找到单位 {company_name} 的备案信息")
                
        except Exception as e:
            logger.error(f"获取单位备案信息失败: {company_name}, 错误: {str(e)}")
            raise e

    async def search_by_domain(self, db: Session, domain: str, force_refresh: bool = False, include_history: bool = False) -> List[ICPRecordBase]:
        """
        根据域名查询ICP备案信息，返回该域名所属单位的所有备案资产
        
        Args:
            db: 数据库会话
            domain: 域名
            force_refresh: 是否强制刷新
            include_history: 是否包含历史备案
            
        Returns:
            该域名所属单位的所有备案资产列表
        """
        # 标准化域名
        normalized_domain = normalize_domain(domain)
        
        root_domain = normalized_domain
        if not normalized_domain.endswith('.gov.cn'):
            root_domain = extract_root_domain(normalized_domain)
        
        # 1. 优先检查数据库缓存（只检查域名记录是否存在）
        if not force_refresh: 
            cached_domain_records = db.query(ICPRecord).filter(
                ICPRecord.domain == root_domain,
                ICPRecord.is_historical == (True if include_history else False)
            ).all()
            
            # 如果有域名缓存且未过期，获取单位名称并返回该单位的所有备案资产
            if cached_domain_records:
                # 检查数据是否过期
                latest_record = max(cached_domain_records, key=lambda x: x.updated_at)
                if not self._is_data_expired(latest_record.updated_at):
                    logger.info(f"域名缓存存在: {root_domain}，获取该单位的所有备案资产")
                    # 获取单位名称
                    company_name = latest_record.company_name
                    if company_name:
                        # 刷新该单位的备案资产
                        await self.search_by_company(db, company_name, force_refresh, include_history=include_history)
                        # 只返回用户所查询的域名的备案信息
                        return self._format_response_data(cached_domain_records)
                    else:
                        # 如果没有单位名称，返回域名记录
                        return self._format_response_data(cached_domain_records)
                else:
                    # 2. 无缓存或强制刷新时，进行完整查询流程
                    logger.info(f"未查询到缓存: {normalized_domain}")
        
        logger.info(f"开始查询域名备案: {normalized_domain}")
        
        # 判断是否为政府域名
        result = []
        company_records = []

        if is_gov_domain(normalized_domain):
            gov_records = await self._search_and_cache_gov_domain(db, normalized_domain, include_history)
            result.append(gov_records[0])
        else:
            company_records = await self._search_and_cache_regular_domain(db, normalized_domain, include_history)
            for record in company_records:
                if extract_root_domain(record.domain) == normalized_domain:
                    result.append(record)
                    break

        return result
    
    async def _search_and_cache_regular_domain(self, db: Session, domain: str, include_history: bool = False) -> List[ICPRecordBase]:
        """
        查询普通域名备案并返回该单位的所有备案资产
        
        Args:
            db: 数据库会话
            domain: 域名
            include_history: 是否包含历史备案
            
        Returns:
            该域名所属单位的所有备案资产列表
        """
        root_domain = extract_root_domain(domain)
        
        try:
            # 1. 调用站长之家API查询域名备案
            logger.info(f"调用站长之家API查询域名: {domain}")
            api_results = await external_api_service.query_chinaz_by_domain(domain)
            
            if not api_results:
                logger.info(f"站长之家API未返回数据: {domain}")
                return []
            
            # 2. 校验返回结果是否符合预期（属于查询域名的根域名）
            valid_results = []
            company_name = ''
            
            for result in api_results:
                returned_domain = result.get('Domain', '')
                if self._is_domain_match(returned_domain, root_domain):
                    valid_results.append(result)
                    # 收集单位名称用于补全查询
                    _company_name = result.get('UnitName', '').strip()
                    if _company_name:
                        company_name = _company_name
                        break
                else:
                    logger.info(f"过滤不匹配的域名: {returned_domain} (查询: {root_domain})")
            
            if not valid_results:
                logger.info(f"没有符合预期的域名备案数据: {domain}")
                return []
            
            # 3. 先使用单位名称获取该单位的所有备案资产（在保存域名查询结果之前）
            all_company_records = []
            # 强制刷新获取该单位的所有备案资产
            company_records = await self.search_by_company(db, company_name, force_refresh=True, include_history=include_history)
            all_company_records.extend(company_records)
            
            # 4. 转换并保存域名查询结果（确保域名记录也被保存）
            converted_data = []
            for result in valid_results:
                converted = self._convert_chinaz_data(result)
                converted_data.append(converted)
            
            # 保存域名查询结果到数据库
            self._save_records_to_db(db, converted_data)
            
            # 5. 返回该域名所属单位的所有备案资产
            return all_company_records
            
        except Exception as e:
            logger.error(f"查询普通域名备案失败: {domain}, 错误: {str(e)}")
            return []
    
    async def _search_and_cache_gov_domain(self, db: Session, domain: str, include_history: bool = False) -> List[ICPRecordBase]:
        """
        查询政府域名备案并返回该单位的所有备案资产
        
        Args:
            db: 数据库会话
            domain: 域名
            include_history: 是否包含历史备案
            
        Returns:
            该域名所属单位的所有备案资产列表
        """
        root_domain = extract_root_domain(domain)
        
        try:
            # 获取域名层级用于政府域名查询
            domain_hierarchy = get_domain_hierarchy(domain)
            
            all_results = []
            company_name = ''
            
            # 逐级查询域名层级
            for level_domain in domain_hierarchy:
                logger.info(f"查询政府域名层级: {level_domain}")
                
                api_results = await external_api_service.query_chinaz_by_domain(level_domain)
                if not api_results:
                    continue
                
                # 校验返回结果
                valid_results = []
                for result in api_results:
                    returned_domain = result.get('Domain', '')
                    if self._is_domain_match(returned_domain, root_domain):
                        valid_results.append(result)
                        # 收集单位名称
                        _company_name = result.get('UnitName', '').strip()
                        if _company_name:
                            company_name = _company_name
                
                if valid_results:
                    all_results.extend(valid_results)
                    break  # 找到匹配结果就停止查询
            
            if not all_results:
                logger.info(f"没有符合预期的政府域名备案数据: {domain}")
                return []
            
            # 转换并保存域名查询结果
            converted_data = []
            for result in all_results:
                converted = self._convert_chinaz_data(result)
                converted_data.append(converted)
            
            saved_records = self._save_records_to_db(db, converted_data)
            
            # 使用单位名称补全查询备案信息并获取该单位的所有备案资产
            all_company_records = []
            await self._fetch_and_cache_company_records(db, company_name)
            # 获取该单位的所有备案记录
            company_records = await self.search_by_company(db, company_name, force_refresh=True, include_history=include_history)
            all_company_records.extend(company_records)
            
            # 返回该域名所属单位的所有备案资产
            return all_company_records
            
        except Exception as e:
            logger.error(f"查询政府域名备案失败: {domain}, 错误: {str(e)}")
            return []
    
    async def _search_regular_domain(self, db: Session, domain: str, force_refresh: bool = False, include_history: bool = False) -> List[ICPRecordBase]:
        """
        查询非政府域名的备案信息
        """
        # 提取根域名
        root_domain = extract_root_domain(domain)
        logger.info(f"非政府域名查询: 原域名={domain}, 根域名={root_domain}")
        
        # 如果不强制刷新，先查询本地数据库
        if not force_refresh:
            query = db.query(ICPRecord).filter(
                ICPRecord.domain == root_domain
            )
            
            # 根据include_history参数决定是否过滤历史备案
            if not include_history:
                query = query.filter(ICPRecord.is_historical == False)
            
            local_records = query.all()
            
            # 检查数据是否过期
            valid_records = []
            for record in local_records:
                if not self._is_data_expired(record.updated_at):
                    valid_records.append(record)
            
            if valid_records:
                logger.info(f"从本地数据库返回域名查询结果: {root_domain}, 包含历史备案: {include_history}")
                return self._format_response_data(valid_records)
        
        # 调用外部API获取数据
        logger.info(f"调用外部API查询根域名: {root_domain}")
        all_records_data = []
        
        # 调用站长之家API（域名查询）
        logger.info(f"调用站长之家API查询域名: {root_domain}")
        chinaz_data = await external_api_service.query_chinaz_by_domain(root_domain)
        if chinaz_data:
            for item in chinaz_data:
                converted_data = self._convert_chinaz_data(item)
                # 校验返回的域名是否属于查询域名的根域名
                returned_domain = converted_data.get("domain", "")
                if returned_domain and self._is_domain_match(returned_domain, root_domain):
                    all_records_data.append(converted_data)
                    logger.info(f"域名匹配成功: 返回域名={returned_domain}, 查询根域名={root_domain}")
                else:
                    logger.info(f"域名不匹配，跳过: 返回域名={returned_domain}, 查询根域名={root_domain}")
        
        # 保存到数据库并获取单位名称
        company_names = set()
        if all_records_data:
            saved_records = self._save_records_to_db(db, all_records_data)
            
            # 收集单位名称，用于后续查询该单位的所有备案信息
            for record in saved_records:
                if record.company_name:
                    company_names.add(record.company_name)
            
            # 根据include_history参数过滤结果
            if not include_history:
                saved_records = [record for record in saved_records if not record.is_historical]
            
            # 如果找到了备案信息，自动查询该单位的所有备案信息并缓存
            for company_name in company_names:
                logger.info(f"自动查询单位所有备案信息: {company_name}")
                try:
                    await self._fetch_and_cache_company_records(db, company_name)
                except Exception as e:
                    logger.error(f"自动查询单位备案信息失败: {company_name}, 错误: {str(e)}")
            
            return self._format_response_data(saved_records)
        
        return []
    
    async def _search_gov_domain(self, db: Session, domain: str, force_refresh: bool = False, include_history: bool = False) -> List[ICPRecordBase]:
        """
        查询政府域名的备案信息，支持递归查询
        """
        logger.info(f"政府域名查询: {domain}")
        
        # 如果不强制刷新，先查询本地数据库的完全匹配
        if not force_refresh:
            query = db.query(ICPRecord).filter(
                ICPRecord.domain == domain
            )
            
            # 根据include_history参数决定是否过滤历史备案
            if not include_history:
                query = query.filter(ICPRecord.is_historical == False)
            
            local_records = query.all()
            
            # 检查数据是否过期
            valid_records = []
            for record in local_records:
                if not self._is_data_expired(record.updated_at):
                    valid_records.append(record)
            
            if valid_records:
                logger.info(f"从本地数据库返回政府域名查询结果: {domain}, 包含历史备案: {include_history}")
                return self._format_response_data(valid_records)
        
        # 获取域名层级列表
        domain_hierarchy = get_domain_hierarchy(domain)
        logger.info(f"政府域名层级: {domain_hierarchy}")
        
        # 从当前域名开始，逐级向上查询外部API
        for current_domain in domain_hierarchy:
            logger.info(f"查询外部API: {current_domain}")
            
            # 调用站长之家API
            logger.info(f"调用站长之家API查询域名: {current_domain}")
            chinaz_data = await external_api_service.query_chinaz_by_domain(current_domain)
            if chinaz_data:
                logger.info(f"在域名 {current_domain} 找到备案信息")
                all_records_data = []
                company_names = set()
                
                for item in chinaz_data:
                    converted_data = self._convert_chinaz_data(item)
                    # 校验返回的域名是否属于查询域名的根域名
                    returned_domain = converted_data.get("domain", "")
                    if returned_domain and self._is_domain_match(returned_domain, current_domain):
                        all_records_data.append(converted_data)
                        logger.info(f"政府域名匹配成功: 返回域名={returned_domain}, 查询域名={current_domain}")
                    else:
                        logger.info(f"政府域名不匹配，跳过: 返回域名={returned_domain}, 查询域名={current_domain}")
                
                # 保存到数据库并获取单位名称
                if all_records_data:
                    saved_records = self._save_records_to_db(db, all_records_data)
                    
                    # 收集单位名称，用于后续查询该单位的所有备案信息
                    for record in saved_records:
                        if record.company_name:
                            company_names.add(record.company_name)
                    
                    # 根据include_history参数过滤结果
                    if not include_history:
                        saved_records = [record for record in saved_records if not record.is_historical]
                    
                    # 如果找到了备案信息，自动查询该单位的所有备案信息并缓存
                    for company_name in company_names:
                        logger.info(f"自动查询政府单位所有备案信息: {company_name}")
                        try:
                            await self._fetch_and_cache_company_records(db, company_name)
                        except Exception as e:
                            logger.error(f"自动查询政府单位备案信息失败: {company_name}, 错误: {str(e)}")
                    
                    return self._format_response_data(saved_records)
        
        logger.info(f"政府域名 {domain} 未找到任何备案信息")
        return []

    async def search_company_history_domains(self, db: Session, company_name: str) -> List[ICPRecordBase]:
        """
        查询企业的历史域名
        
        Args:
            db: 数据库会话
            company_name: 企业名称
            
        Returns:
            企业的历史域名列表（只返回历史备案记录）
        """
        try:
            # 查询数据库中该企业的所有历史备案记录
            historical_records = db.query(ICPRecord).filter(
                ICPRecord.company_name == company_name,
                ICPRecord.is_historical == True
            ).all()
            
            logger.info(f"查询到企业 {company_name} 的历史域名记录数量: {len(historical_records)}")
            
            return self._format_response_data(historical_records)
            
        except Exception as e:
            logger.error(f"查询企业历史域名失败: {str(e)}")
            raise e


# 全局ICP服务实例
icp_service = ICPService()