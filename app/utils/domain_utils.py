import re
from typing import List, Optional
from publicsuffix2 import get_sld


def extract_root_domain(domain: str) -> str:
    """
    使用 Public Suffix List 提取根域名（注册域名）
    
    Args:
        domain: 输入域名
        
    Returns:
        根域名（注册域名）
        
    Examples:
        extract_root_domain("www.baidu.com") -> "baidu.com"
        extract_root_domain("a.b.c.baidu.com") -> "baidu.com"
        extract_root_domain("baidu.com") -> "baidu.com"
        extract_root_domain("www.example.co.uk") -> "example.co.uk"
        extract_root_domain("subdomain.github.io") -> "subdomain.github.io"
    """
    if not domain:
        return domain
    
    # 标准化域名
    normalized = normalize_domain(domain)
    
    # 使用 publicsuffix2 获取注册域名
    try:
        sld = get_sld(normalized)
        return sld if sld else normalized
    except Exception:
        # 如果解析失败，回退到简单的域名分割
        parts = normalized.split('.')
        if len(parts) <= 2:
            return normalized
        return '.'.join(parts[-2:])


def is_gov_domain(domain: str) -> bool:
    """
    判断是否为政府域名 (*.gov.cn)
    
    Args:
        domain: 域名
        
    Returns:
        是否为政府域名
    """
    normalized = domain.lower().strip()
    return normalized.endswith('.gov.cn') or normalized == 'gov.cn'


def get_domain_hierarchy(domain: str) -> List[str]:
    """
    获取政府域名的层级列表，从最具体到最一般
    
    Args:
        domain: 政府域名
        
    Returns:
        域名层级列表
        
    Examples:
        get_domain_hierarchy("a.b.c.gz.gov.cn") -> 
        ["a.b.c.gz.gov.cn", "b.c.gz.gov.cn", "c.gz.gov.cn", "gz.gov.cn"]
    """
    if not is_gov_domain(domain):
        return [domain]
    
    # 移除协议前缀
    domain = re.sub(r'^https?://', '', domain)
    
    # 移除端口号和路径
    domain = domain.split(':')[0].split('/')[0]
    
    parts = domain.split('.')
    hierarchy = []
    
    # 从完整域名开始，逐级向上
    for i in range(len(parts)):
        if i == 0:
            hierarchy.append(domain)
        else:
            # 去掉最前面的子域名
            subdomain = '.'.join(parts[i:])
            if subdomain.endswith('.gov.cn'):
                hierarchy.append(subdomain)
    
    return hierarchy


def normalize_domain(domain: str) -> str:
    """
    标准化域名格式
    
    Args:
        domain: 输入域名
        
    Returns:
        标准化后的域名
    """
    if not domain:
        return domain
    
    # 移除前后空格
    domain = domain.strip()
    
    # 移除协议前缀 (支持更多协议类型)
    domain = re.sub(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', '', domain, flags=re.IGNORECASE)
    
    # 移除端口号
    domain = domain.split(':')[0]
    
    # 移除路径
    domain = domain.split('/')[0]
    
    # 转换为小写
    domain = domain.lower()
    
    return domain