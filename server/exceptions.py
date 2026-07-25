"""
Custom exception classes for structured error handling.

Provides domain-specific exceptions with error codes, status codes,
and formatted error responses.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    """Standard error codes for API responses."""
    
    # Connection/WebSocket errors
    WS_ACCEPT_FAILED = "WS_ACCEPT_FAILED"
    WS_SEND_FAILED = "WS_SEND_FAILED"
    WS_RECEIVE_FAILED = "WS_RECEIVE_FAILED"
    WS_CLOSE_FAILED = "WS_CLOSE_FAILED"
    
    # Session errors
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    SESSION_INVALID = "SESSION_INVALID"
    
    # Database errors
    DB_CONNECT_FAILED = "DB_CONNECT_FAILED"
    DB_QUERY_FAILED = "DB_QUERY_FAILED"
    DB_TRANSACTION_FAILED = "DB_TRANSACTION_FAILED"
    
    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_DEVICE_ID = "INVALID_DEVICE_ID"
    
    # RPC errors
    RPC_METHOD_NOT_FOUND = "RPC_METHOD_NOT_FOUND"
    RPC_INVALID_PARAMS = "RPC_INVALID_PARAMS"
    RPC_INTERNAL_ERROR = "RPC_INTERNAL_ERROR"
    
    # General errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NOT_FOUND = "NOT_FOUND"


class CPIPException(Exception):
    """Base exception for CPIP errors."""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode | str = ErrorCode.INTERNAL_ERROR,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.error_code = error_code if isinstance(error_code, str) else error_code.value
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert exception to JSON-serializable dict."""
        return {
            "error": self.error_code,
            "message": self.message,
            "status": self.status_code,
            **(self.details or {}),
        }


class WebSocketError(CPIPException):
    """WebSocket connection or communication error."""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode | str = ErrorCode.WS_SEND_FAILED,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, error_code, 1008, details)


class SessionError(CPIPException):
    """Session-related error."""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode | str = ErrorCode.SESSION_INVALID,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, error_code, 400, details)


class DatabaseError(CPIPException):
    """Database operation error."""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode | str = ErrorCode.DB_QUERY_FAILED,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, error_code, 500, details)


class ValidationError(CPIPException):
    """Request validation error."""
    
    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, ErrorCode.VALIDATION_ERROR, 422, details)


class RPCError(CPIPException):
    """RPC call error."""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode | str = ErrorCode.RPC_INTERNAL_ERROR,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, error_code, 400, details)
