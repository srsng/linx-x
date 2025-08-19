import logging
import uuid
from typing import Dict, Optional
from dataclasses import dataclass
from contextlib import asynccontextmanager

from .consts import consts

logger = logging.getLogger(consts.LOGGER_NAME)


@dataclass
class SessionConfig:
    """会话配置，包含每个客户端的认证信息"""
    access_key: str
    secret_key: str
    endpoint_url: str
    region_name: str
    buckets: list[str]
    session_id: str


class SessionManager:
    """会话管理器，管理所有活跃的SSE连接会话"""
    
    def __init__(self):
        self._sessions: Dict[str, SessionConfig] = {}
    
    def create_session(self, access_key: str, secret_key: str, 
                      endpoint_url: str, region_name: str, 
                      buckets: list[str]) -> str:
        """创建新的会话"""
        session_id = str(uuid.uuid4())
        session_config = SessionConfig(
            access_key=access_key,
            secret_key=secret_key,
            endpoint_url=endpoint_url,
            region_name=region_name,
            buckets=buckets,
            session_id=session_id
        )
        
        self._sessions[session_id] = session_config
        logger.info(f"Created session {session_id} for access_key: {access_key}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[SessionConfig]:
        """获取会话配置"""
        return self._sessions.get(session_id)
    
    def remove_session(self, session_id: str) -> bool:
        """移除会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Removed session {session_id}")
            return True
        return False
    
    def list_sessions(self) -> list[str]:
        """列出所有活跃会话ID"""
        return list(self._sessions.keys())


# 全局会话管理器实例
session_manager = SessionManager()


@asynccontextmanager
async def get_session_context(session_id: str | None):
    """获取会话上下文的异步上下文管理器。必须提供有效的 session_id。"""
    if not session_id:
        raise ValueError("Missing session_id in request context")
    session_config = session_manager.get_session(session_id)
    if not session_config:
        raise ValueError(f"Session {session_id} not found")
    
    try:
        yield session_config
    except Exception as e:
        logger.error(f"Error in session {session_id}: {e}")
        raise
