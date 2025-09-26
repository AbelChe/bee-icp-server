import re
import ipaddress
from typing import List, Optional
from publicsuffix2 import get_sld, get_public_suffix


def is_valid_domain_or_ip(input_str: str) -> bool:
    """
    验证输入是否为有效的域名或IP地址
    
    Args:
        input_str: 输入字符串
        
    Returns:
        是否为有效的域名或IP地址
    """
    if not input_str or not isinstance(input_str, str):
        return False
    
    input_str = input_str.strip()
    
    # 检查是否为IP地址
    if is_valid_ip(input_str):
        return True
    
    # 检查是否为域名
    return is_valid_domain(input_str)



def is_valid_ip(ip_str: str) -> bool:
    """
    验证是否为有效的IP地址（IPv4或IPv6）
    
    Args:
        ip_str: IP地址字符串
        
    Returns:
        是否为有效的IP地址
    """
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False


def is_private_ip(ip_str: str) -> bool:
    """
    判断IP地址是否为内网IP（私有IP地址）
    
    Args:
        ip_str: IP地址字符串
        
    Returns:
        是否为内网IP地址
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private
    except ValueError:
        return False


def is_valid_domain(domain: str) -> bool:
    """
    验证是否为有效的域名格式
    
    Args:
        domain: 域名字符串
        
    Returns:
        是否为有效的域名
    """
    if not domain or len(domain) > 253:
        return False
    
    # 如果是IP地址，则不是域名
    if is_valid_ip(domain):
        return False
    
    # 域名正则表达式
    # 允许字母、数字、连字符和点，但不能以连字符开头或结尾
    domain_pattern = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
    
    if not re.match(domain_pattern, domain):
        return False
    
    # 检查每个标签的长度（不超过63个字符）
    labels = domain.split('.')
    for label in labels:
        if len(label) > 63 or len(label) == 0:
            return False
    
    # 至少包含一个点（顶级域名）
    if '.' not in domain:
        return False
    
    # 域名必须包含至少一个字母（不能全是数字）
    if not re.search(r'[a-zA-Z]', domain):
        return False
    
    return True


def is_icann_domain(domain: str) -> bool:
    """
    判断域名是否为 ICANN 注册的域名
    
    Args:
        domain: 域名
        
    Returns:
        是否为 ICANN 注册的域名
    """
    if not domain:
        return False
    
    # 标准化域名
    normalized = normalize_domain(domain)
    
    if get_public_suffix(normalized, strict=True) is None:
        return False
    return True

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