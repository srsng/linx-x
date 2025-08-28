import logging
from typing import List, Optional
from attr import dataclass

from ..consts import consts

# HTTP headers for authentication
_HEADER_ACCESS_KEY = "X-AK"
_HEADER_SECRET_KEY = "X-SK"
_HEADER_REGION_NAME = "X-REGION-NAME"
_HEADER_BUCKETS = "X-BUCKETS"

logger = logging.getLogger(consts.LOGGER_NAME)


@dataclass
class Config:
    access_key: str
    secret_key: str
    endpoint_url: str
    region_name: str
    buckets: List[str]


def load_config_from_headers(headers: dict) -> tuple[Optional[Config], Optional[str]]:
    """从HTTP headers加载配置（大小写不敏感）"""
    # 归一化为小写键
    headers_lc = {str(k).lower(): v for k, v in headers.items()}

    # 支持多种写法
    def _h(name: str) -> Optional[str]:
        return headers_lc.get(name.lower())

    # 检查必需的认证头
    access_key = _h(_HEADER_ACCESS_KEY)
    secret_key = _h(_HEADER_SECRET_KEY)
    region_name = _h(_HEADER_REGION_NAME)
    # 通过region_name动态生成endpoint_url
    endpoint_url = f"https://s3.{region_name}.qiniucs.com"
    buckets_str = _h(_HEADER_BUCKETS)

    if not access_key or not secret_key:
        error_msg = "Missing required authentication headers (X-AK, X-SK)"
        logger.warning(error_msg)
        return None, error_msg

    if not region_name:
        error_msg = "Missing required region header (X-REGION-NAME)"
        logger.warning(error_msg)
        return None, error_msg

    if not buckets_str:
        error_msg = "Missing required buckets header (X-BUCKETS)"
        logger.warning(error_msg)
        return None, error_msg

    # 解析buckets配置
    buckets = [b.strip() for b in buckets_str.split(",") if b.strip()]
    if not buckets:
        error_msg = "X-BUCKETS header is empty or invalid"
        logger.warning(error_msg)
        return None, error_msg

    cfg = Config(
        access_key=access_key,
        secret_key=secret_key,
        endpoint_url=endpoint_url,
        region_name=region_name,
        buckets=buckets,
    )

    logger.info(f"Loaded config from headers for access_key: {access_key}")
    return cfg, None
