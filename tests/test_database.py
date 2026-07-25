"""
Tests for database configuration and connection pooling.
"""

import pytest
from unittest.mock import patch, MagicMock

from server.config import DatabaseConfig, ServerConfig
from server.exceptions import DatabaseError, ErrorCode


class TestDatabaseConfig:
    """Tests for database configuration."""
    
    def test_default_database_config(self):
        """Test default database configuration."""
        config = DatabaseConfig()
        
        assert "sqlite" in config.url
        assert config.pool_size == 20
        assert config.max_overflow == 10
        assert config.pool_timeout == 30
        assert config.pool_recycle == 3600
    
    @patch.dict("os.environ", {"DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db"})
    def test_postgres_database_url(self):
        """Test PostgreSQL database URL from environment."""
        config = DatabaseConfig.from_env()
        
        assert "postgresql" in config.url
    
    @patch.dict("os.environ", {
        "DB_POOL_SIZE": "50",
        "DB_MAX_OVERFLOW": "20",
        "DB_POOL_TIMEOUT": "45",
        "DB_POOL_RECYCLE": "7200",
    })
    def test_custom_pool_settings(self):
        """Test custom connection pool settings from environment."""
        config = DatabaseConfig.from_env()
        
        assert config.pool_size == 50
        assert config.max_overflow == 20
        assert config.pool_timeout == 45
        assert config.pool_recycle == 7200
    
    @patch.dict("os.environ", {"DB_POOL_SIZE": "invalid"})
    def test_invalid_pool_size_uses_default(self):
        """Test that invalid pool_size falls back to default."""
        config = DatabaseConfig.from_env()
        assert config.pool_size == 20


class TestServerConfig:
    """Tests for server configuration."""
    
    @patch.dict("os.environ", {})
    def test_default_server_config(self):
        """Test default server configuration."""
        config = ServerConfig.from_env()
        
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.debug is False
    
    @patch.dict("os.environ", {
        "CPIP_HOST": "127.0.0.1",
        "CPIP_PORT": "9000",
        "CPIP_DEBUG": "true",
    })
    def test_custom_server_config(self):
        """Test custom server configuration from environment."""
        config = ServerConfig.from_env()
        
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.debug is True
    
    @patch.dict("os.environ", {"CORS_ORIGINS": "http://localhost:3000,https://example.com"})
    def test_cors_origins_from_env(self):
        """Test CORS origins configuration."""
        config = ServerConfig.from_env()
        
        assert "http://localhost:3000" in config.cors_origins
        assert "https://example.com" in config.cors_origins
