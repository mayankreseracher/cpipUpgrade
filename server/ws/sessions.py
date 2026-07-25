"""
WebSocket session management with configurable TTL.

Tracks active execution sessions per device with explicit
lifecycle management and stale session cleanup.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ExecutionSession:
    """Represents an execution session on a device."""
    
    session_id: str
    device_id: str
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    active_modules: list[str] = field(default_factory=list)
    execution_count: int = 0


class SessionManager:
    """Manages execution sessions for connected devices."""

    def __init__(self):
        self._sessions: dict[str, ExecutionSession] = {}

    def create(self, session_id: str, device_id: str) -> ExecutionSession:
        """Create a new execution session."""
        session = ExecutionSession(session_id=session_id, device_id=device_id)
        self._sessions[session_id] = session
        logger.debug(f"Created session {session_id} for device {device_id}")
        return session

    def get(self, session_id: str) -> ExecutionSession | None:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def get_by_device(self, device_id: str) -> list[ExecutionSession]:
        """Get all sessions for a device."""
        return [s for s in self._sessions.values() if s.device_id == device_id]

    def update_activity(self, session_id: str) -> None:
        """Update last activity time for a session."""
        session = self._sessions.get(session_id)
        if session:
            session.last_active = time.time()
            session.execution_count += 1

    def remove(self, session_id: str) -> None:
        """Remove a session."""
        session = self._sessions.pop(session_id, None)
        if session:
            logger.debug(
                f"Removed session {session_id} for device {session.device_id} "
                f"(executions: {session.execution_count})"
            )

    def cleanup_stale(self, max_idle_seconds: int = 3600) -> int:
        """Clean up stale sessions and return count removed.
        
        Args:
            max_idle_seconds: Sessions idle longer than this are removed.
                            Defaults to 1 hour.
        
        Returns:
            Number of stale sessions removed.
        """
        now = time.time()
        stale = [
            (sid, s)
            for sid, s in self._sessions.items()
            if now - s.last_active > max_idle_seconds
        ]
        
        for sid, session in stale:
            idle_time = now - session.last_active
            logger.info(
                f"Cleaning stale session {sid} for device {session.device_id} "
                f"(idle: {idle_time:.0f}s, executions: {session.execution_count})"
            )
            del self._sessions[sid]
        
        if stale:
            logger.info(f"Cleaned {len(stale)} stale session(s)")
        
        return len(stale)

    @property
    def active_count(self) -> int:
        """Get count of active sessions."""
        return len(self._sessions)


session_manager = SessionManager()
