from .storage import load as load_storage
from .version import load as load_version


def load():
    # 版本
    load_version()
    # 存储业务 - 注册会话感知的工具
    load_storage()
