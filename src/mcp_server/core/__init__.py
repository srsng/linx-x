from ..config import config
from .storage import load as load_storage
from .media_processing import load as load_media_processing
from .cdn import load as load_cdn
from .version import load as load_version


def load():
    # 加载配置
    cfg = config.load_config()

    # 版本
    load_version(cfg)
    # 存储业务 - 注册会话感知的工具
    load_storage(cfg, use_session_aware=True)
    # # CDN
    # load_cdn(cfg)
    # # 智能多媒体
    # load_media_processing(cfg)
