import contextvars
from typing import Optional

# Context variable to hold the current session_id during a request/connection
current_session_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "current_session_id", default=None
)
