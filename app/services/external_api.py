import httpx
import json
import logging
import asyncio
from typing import List, Dict, Optional
from app.config import settings
from app.schemas import ChinazAPIResponse, TianyanchaSearchResponse, TianyanchaICPResponse

logger = logging.getLogger(__name__)


class ExternalAPIService:
    """外部API调用服务"""
    
    def __init__(self):
        self.chinaz_api_key = settings.chinaz_api_key
        self.tianyancha_api_key = settings.tianyancha_api_key
        self.timeout = 8.0  # 设置超时为8秒
        self.max_retries = 3  # 最大重试次数
    
    async def _query_chinaz_with_retry(self, url: str, params: Dict, query_type: str, keyword: str) -> Optional[List[Dict]]:
        """
        带重试机制的站长之家API查询
        
        Args:
            url: API地址
            params: 查询参数
            query_type: 查询类型（企业/域名）
            keyword: 查询关键词
            
        Returns:
            查询结果列表或None
        """
        for attempt in range(self.max_retries):
            try:
                logger.info(f"使用站长之家API{query_type}查询, keyword: {keyword}, 第{attempt + 1}次查询")
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    
                    data = response.json()
                    if data.get("StateCode") == 1:
                        result = data.get("Result")
                        if result is None:
                            logger.info(f"站长之家API{query_type}查询成功: {keyword}, 但无相关备案信息")
                            return []
                        else:
                            logger.info(f"站长之家API{query_type}查询成功: {keyword}, 返回{len(result)}条记录")
                            return result
                    elif data.get("StateCode") == -1:
                        logger.warning(f"站长之家API{query_type}查询存在异常, keyword: {keyword}, {data.get('StateCode')} {data.get('Reason', '未知错误')}")
                        # StateCode为-1时继续重试
                        continue
                    else:
                        logger.error(f"站长之家API{query_type}查询失败: {keyword}, {data.get('Reason', '未知错误')}")
                        return None
                        
            except httpx.TimeoutException:
                logger.warning(f"站长之家API{query_type}查询超时: {keyword}, 第{attempt + 1}次尝试")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)  # 重试前等待1秒
                    continue
                else:
                    logger.error(f"站长之家API{query_type}查询超时: {keyword}, 已达到最大重试次数")
                    return None
            except Exception as e:
                logger.warning(f"站长之家API{query_type}查询异常: {keyword}, 第{attempt + 1}次尝试, 错误: {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)  # 重试前等待1秒
                    continue
                else:
                    logger.error(f"站长之家API{query_type}查询异常: {keyword}, 已达到最大重试次数, 错误: {str(e)}")
                    return None
        
        return None
    
    async def query_chinaz_by_company(self, company_name: str) -> Optional[List[Dict]]:
        """
        通过站长之家API查询企业备案信息
        
        Args:
            company_name: 企业名称
            
        Returns:
            查询结果列表或None
        """
        if not self.chinaz_api_key:
            logger.warning("站长之家API密钥未配置")
            return None
            
        url = "http://openapiu67.chinaz.net/v1/1001/sponsorunit"
        params = {
            "companyname": company_name,
            "APIKey": self.chinaz_api_key,
            "ChinazVer": "1.0"
        }
        
        return await self._query_chinaz_with_retry(url, params, "企业", company_name)
    
    async def query_chinaz_by_domain(self, domain: str) -> Optional[List[Dict]]:
        """
        通过站长之家API查询域名备案信息
        
        Args:
            domain: 域名
            
        Returns:
            查询结果列表或None
        """
        if not self.chinaz_api_key:
            logger.warning("站长之家API密钥未配置")
            return None
            
        url = "http://openapiu67.chinaz.net/v1/1001/sponsorunit"
        params = {
            "companyname": domain,
            "APIKey": self.chinaz_api_key,
            "ChinazVer": "1.0"
        }
        
        return await self._query_chinaz_with_retry(url, params, "域名", domain)
    
    async def search_tianyancha_company(self, company_name: str) -> Optional[int]:
        """
        通过天眼查API搜索企业获取ID
        
        Args:
            company_name: 企业名称
            
        Returns:
            企业ID或None
        """
        if not self.tianyancha_api_key:
            logger.warning("天眼查API密钥未配置")
            return None
            
        url = "http://open.api.tianyancha.com/services/open/search/2.0"
        params = {
            "word": company_name,
            "pageSize": 20,
            "pageNum": 1
        }
        headers = {
            "Authorization": self.tianyancha_api_key
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                if data.get("error_code") == 0:
                    items = data.get("result", {}).get("items", [])
                    # 查找完全匹配的企业名称
                    for item in items:
                        if item.get("name") == company_name:
                            return item.get("id")
                    # 如果没有完全匹配，认定为未查询到相关单位信息
                    logger.info(f"天眼查搜索未找到完全匹配的企业: {company_name}, 返回结果数: {len(items)}")
                    return None
                else:
                    logger.error(f"天眼查搜索API失败: {data.get('reason', '未知错误')}")
                    return None
                    
        except httpx.TimeoutException:
            logger.error(f"天眼查搜索API超时: {company_name}")
            return None
        except Exception as e:
            logger.error(f"天眼查搜索API异常: {company_name}, 错误: {str(e)}")
            return None
    
    async def query_tianyancha_icp(self, company_id: int) -> Optional[List[Dict]]:
        """
        通过天眼查API查询企业ICP备案信息
        
        Args:
            company_id: 企业ID
            
        Returns:
            ICP备案信息列表或None
        """
        url = "https://api9.tianyancha.com/cloud-intellectual-property/intellectualProperty/icpRecordList"
        params = {
            "id": company_id,
            "pageNum": 1,
            "pageSize": 10
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.159 Safari/537.36",
            "X-Forwarded-For": "127.0.0.1"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                if data.get("state") == "ok" and data.get("errorCode") == 0:
                    return data.get("data", {}).get("item", [])
                else:
                    logger.error(f"天眼查ICP查询API失败: {data.get('message', '未知错误')}")
                    return None
                    
        except httpx.TimeoutException:
            logger.error(f"天眼查ICP查询API超时: {company_id}")
            return None
        except Exception as e:
            logger.error(f"天眼查ICP查询API异常: {company_id}, 错误: {str(e)}")
            return None
    
    async def query_tianyancha_by_company(self, company_name: str) -> Optional[List[Dict]]:
        """
        通过天眼查API查询企业备案信息（完整流程）
        
        Args:
            company_name: 企业名称
            
        Returns:
            查询结果列表或None
        """
        # 第一步：搜索企业获取ID
        company_id = await self.search_tianyancha_company(company_name)
        if not company_id:
            return None
        
        # 第二步：通过ID查询ICP备案信息
        return await self.query_tianyancha_icp(company_id)


# 全局外部API服务实例
external_api_service = ExternalAPIService()