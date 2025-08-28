from .tools import register_tools


def load():
    register_tools()


__all__ = ["load"]
