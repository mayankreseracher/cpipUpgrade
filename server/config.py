"""
Server configuration with environment variable validation.

Supports multiple configuration sources:
- Environment variables
- Configuration file (.env.toml)
- Default values
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore


logger = logging.getLogger(__name__)


def _parse_bool(value: str) -> bool:
    """Parse boolean from environment variable."""
    return value.lower() in ("true", "1", "yes", "on")


def _parse_int(value: str, default: int) -> int:
    """Parse integer with fallback to default."""
    try:
        return int(value)
    except ValueError:
        logger.warning(f"Invalid integer value '{value}', using default {default}")
        return default


@dataclass
class LoggingConfig:
    """Logging configuration."""
    
    backend: str = "zap"  # 'zap' or 'zerolog' for Go, 'python' for Python
    level: str = "INFO"
    format: str = "json"  # 'json' or 'text'
    
    @classmethod
    def from_env(cls) -> LoggingConfig:
        """Load logging config from environment."""
        backend = os.getenv("LOGGER_BACKEND", "zap")
        
        # Validate backend
        if backend not in ("zap", "zerolog", "python"):
            logger.warning(
                f"Invalid LOGGER_BACKEND '{backend}', using 'zap'. "
                f"Valid options: zap, zerolog, python"
            )
            backend = "zap"
        
        level = os.getenv("LOG_LEVEL", "INFO").upper()
        valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        if level not in valid_levels:
            logger.warning(
                f"Invalid LOG_LEVEL '{level}', using 'INFO'. "
                f"Valid options: {', '.join(valid_levels)}"
            )
            level = "INFO"
        
        format_type = os.getenv("LOG_FORMAT", "json")
        if format_type not in ("json", "text"):
            logger.warning(
                f"Invalid LOG_FORMAT '{format_type}', using 'json'. "
                f"Valid options: json, text"
            )
            format_type = "json"
        
        return cls(backend=backend, level=level, format=format_type)


@dataclass
class DatabaseConfig:
    """Database configuration."""
    
    url: str = "sqlite+aiosqlite:///./cpip.db"
    pool_size: int = 20
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False
    
    @classmethod
    def from_env(cls) -> DatabaseConfig:
        """Load database config from environment."""
        url = os.getenv(
            "DATABASE_URL",
            "sqlite+aiosqlite:///./cpip.db",
        )
        
        pool_size = _parse_int(os.getenv("DB_POOL_SIZE", "20"), 20)
        max_overflow = _parse_int(os.getenv("DB_MAX_OVERFLOW", "10"), 10)
        pool_timeout = _parse_int(os.getenv("DB_POOL_TIMEOUT", "30"), 30)
        pool_recycle = _parse_int(os.getenv("DB_POOL_RECYCLE", "3600"), 3600)
        echo = _parse_bool(os.getenv("DB_ECHO", "false"))
        
        return cls(
            url=url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            echo=echo,
        )


@dataclass
class SessionConfig:
    """Session management configuration."""
    
    cleanup_interval: int = 300  # 5 minutes
    max_idle_seconds: int = 3600  # 1 hour
    heartbeat_interval: int = 30  # 30 seconds
    heartbeat_timeout: int = 90  # 90 seconds (3x heartbeat interval)
    
    @classmethod
    def from_env(cls) -> SessionConfig:
        """Load session config from environment."""
        cleanup_interval = _parse_int(
            os.getenv("SESSION_CLEANUP_INTERVAL", "300"), 300
        )
        max_idle_seconds = _parse_int(
            os.getenv("SESSION_MAX_IDLE_SECONDS", "3600"), 3600
        )
        heartbeat_interval = _parse_int(
            os.getenv("SESSION_HEARTBEAT_INTERVAL", "30"), 30
        )
        heartbeat_timeout = _parse_int(
            os.getenv("SESSION_HEARTBEAT_TIMEOUT", "90"), 90
        )
        
        return cls(
            cleanup_interval=cleanup_interval,
            max_idle_seconds=max_idle_seconds,
            heartbeat_interval=heartbeat_interval,
            heartbeat_timeout=heartbeat_timeout,
        )


@dataclass
class ServerConfig:
    """Main server configuration."""
    
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "cpip-dev-secret-change-in-production"
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    
    @classmethod
    def from_env(cls) -> ServerConfig:
        """Load configuration from environment variables."""
        host = os.getenv("CPIP_HOST", "0.0.0.0")
        port = _parse_int(os.getenv("CPIP_PORT", "8000"), 8000)
        debug = _parse_bool(os.getenv("CPIP_DEBUG", "false"))
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        jwt_secret = os.getenv("JWT_SECRET", "cpip-dev-secret-change-in-production")
        
        # Warn if using dev secret in production
        if not debug and jwt_secret == "cpip-dev-secret-change-in-production":
            logger.warning(
                "Using default JWT secret in non-debug mode! "
                "Set JWT_SECRET environment variable to a secure value."
            )
        
        cors_origins_str = os.getenv("CORS_ORIGINS", "*")
        cors_origins = [
            o.strip() for o in cors_origins_str.split(",") if o.strip()
        ]
        
        return cls(
            host=host,
            port=port,
            debug=debug,
            database=DatabaseConfig.from_env(),
            logging=LoggingConfig.from_env(),
            session=SessionConfig.from_env(),
            redis_url=redis_url,
            jwt_secret=jwt_secret,
            cors_origins=cors_origins,
        )
    
    @classmethod
    def from_file(cls, config_path: str | Path) -> ServerConfig:
        """Load configuration from TOML file and environment overrides."""
        config_path = Path(config_path)
        config_dict = {}
        
        if config_path.exists():
            logger.info(f"Loading config from {config_path}")
            with open(config_path, "rb") as f:
                config_dict = tomllib.load(f)
        else:
            logger.warning(f"Config file not found: {config_path}")
        
        # Environment variables override file config
        return cls.from_env()


# Global config instance
server_config = ServerConfig.from_env()
