from .storage import load as load_storage
from .version import load as load_version
# from .cdn import load as load_cdn
# from .media_processing import load as load_media_processing


def load():
    # 版本
    load_version()
    # 存储业务 - 注册会话感知的工具
    load_storage()
    # # CDN
    # load_cdn()
    # # 智能多媒体
    # load_media_processing()
