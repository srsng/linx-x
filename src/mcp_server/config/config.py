import logging
import os
from typing import List, Optional
from attr import dataclass
from dotenv import load_dotenv

from ..consts import consts

_CONFIG_ENV_KEY_ACCESS_KEY = "QINIU_ACCESS_KEY"
_CONFIG_ENV_KEY_SECRET_KEY = "QINIU_SECRET_KEY"
_CONFIG_ENV_KEY_ENDPOINT_URL = "QINIU_ENDPOINT_URL"
_CONFIG_ENV_KEY_REGION_NAME = "QINIU_REGION_NAME"
_CONFIG_ENV_KEY_BUCKETS = "QINIU_BUCKETS"

# HTTP headers for authentication
_HEADER_ACCESS_KEY = "X-AK"
_HEADER_SECRET_KEY = "X-SK"
_HEADER_ENDPOINT_URL = "X-ENDPOINT-URL"
_HEADER_REGION_NAME = "X-REGION-NAME"
_HEADER_BUCKETS = "X-BUCKETS"

logger = logging.getLogger(consts.LOGGER_NAME)

# Load environment variables at package initialization
load_dotenv()


@dataclass
class Config:
    access_key: str
    secret_key: str
    endpoint_url: str
    region_name: str
    buckets: List[str]


def load_config() -> Config:
    """从环境变量加载默认配置"""
    config = Config(
        access_key=os.getenv(_CONFIG_ENV_KEY_ACCESS_KEY),
        secret_key=os.getenv(_CONFIG_ENV_KEY_SECRET_KEY),
        endpoint_url=os.getenv(_CONFIG_ENV_KEY_ENDPOINT_URL),
        region_name=os.getenv(_CONFIG_ENV_KEY_REGION_NAME),
        buckets=_get_configured_buckets_from_env(),
    )

    if not config.access_key or len(config.access_key) == 0:
        config.access_key = "YOUR_QINIU_ACCESS_KEY"
    if not config.secret_key or len(config.secret_key) == 0:
        config.secret_key = "YOUR_QINIU_SECRET_KEY"
    if not config.endpoint_url or len(config.endpoint_url) == 0:
        config.endpoint_url = "YOUR_QINIU_ENDPOINT_URL"
    if not config.region_name or len(config.region_name) == 0:
        config.region_name = "YOUR_QINIU_REGION_NAME"

    logger.info(f"Configured   access_key: {config.access_key}")
    logger.info(f"Configured endpoint_url: {config.endpoint_url}")
    logger.info(f"Configured  region_name: {config.region_name}")
    logger.info(f"Configured      buckets: {config.buckets}")
    return config


def load_config_from_headers(headers: dict) -> Optional[Config]:
    """从HTTP headers加载配置（大小写不敏感）"""
    # 归一化为小写键
    headers_lc = {str(k).lower(): v for k, v in headers.items()}
    
    # 支持多种写法
    def _h(name: str) -> Optional[str]:
        return headers_lc.get(name.lower())

    # 检查必需的认证头
    access_key = _h(_HEADER_ACCESS_KEY)
    secret_key = _h(_HEADER_SECRET_KEY)
    
    if not access_key or not secret_key:
        logger.warning("Missing required authentication headers")
        return None
    
    # 获取可选配置
    endpoint_url = _h(_HEADER_ENDPOINT_URL)
    region_name = _h(_HEADER_REGION_NAME)
    buckets_str = _h(_HEADER_BUCKETS)
    
    # 如果headers中没有提供，使用环境变量默认值
    if not endpoint_url:
        endpoint_url = os.getenv(_CONFIG_ENV_KEY_ENDPOINT_URL, "YOUR_QINIU_ENDPOINT_URL")
    if not region_name:
        region_name = os.getenv(_CONFIG_ENV_KEY_REGION_NAME, "YOUR_QINIU_REGION_NAME")
    if not buckets_str:
        buckets = _get_configured_buckets_from_env()
    else:
        buckets = [b.strip() for b in buckets_str.split(",") if b.strip()]
    
    cfg = Config(
        access_key=access_key,
        secret_key=secret_key,
        endpoint_url=endpoint_url,
        region_name=region_name,
        buckets=buckets
    )
    
    logger.info(f"Loaded config from headers for access_key: {access_key}")
    return cfg


def _get_configured_buckets_from_env() -> List[str]:
    bucket_list = os.getenv(_CONFIG_ENV_KEY_BUCKETS)
    if bucket_list:
        buckets = [b.strip() for b in bucket_list.split(",")]
        return buckets
    else:
        return []
