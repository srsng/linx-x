from .storage import StorageService
from .tools import register_tools, register_session_aware_tools
from .resource import register_resource_provider
from ...config import config


def load(cfg: config.Config, use_session_aware: bool = False):
    storage = StorageService(cfg)

    if use_session_aware:
        # 注册会话感知的工具
        register_session_aware_tools()
    else:
        # 注册传统工具（兼容模式）
        register_tools(storage)

    register_resource_provider(storage)


__all__ = ["load"]
