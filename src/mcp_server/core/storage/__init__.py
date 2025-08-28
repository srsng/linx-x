from .tools import register_session_aware_tools
from .resource import register_resource_provider


def load():
    # 注册会话感知的工具
    register_session_aware_tools()

    # 注册资源提供者
    register_resource_provider()


__all__ = ["load"]
