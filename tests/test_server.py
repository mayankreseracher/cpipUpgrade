"""
Tests for FastAPI server and core functionality.
"""

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from server.models import DeviceRegistration
from server.exceptions import ValidationError as CPIPValidationError, ErrorCode


class TestDeviceRegistration:
    """Tests for device registration validation."""
    
    def test_valid_device_registration(self):
        """Test valid device registration model."""
        device = DeviceRegistration(
            device_id="device-001",
            platform="android",
            version="1.0.0",
        )
        assert device.device_id == "device-001"
        assert device.platform == "android"
    
    def test_invalid_device_id_format(self):
        """Test that invalid device_id format is rejected."""
        with pytest.raises(ValidationError):
            DeviceRegistration(
                device_id="invalid@device$id",  # Invalid characters
                platform="android",
            )
    
    def test_empty_device_id_rejected(self):
        """Test that empty device_id is rejected."""
        with pytest.raises(ValidationError):
            DeviceRegistration(device_id="", platform="android")
    
    def test_device_id_too_long_rejected(self):
        """Test that very long device_id is rejected."""
        with pytest.raises(ValidationError):
            DeviceRegistration(
                device_id="x" * 300,  # Exceeds max_length=255
                platform="android",
            )


class TestExceptionHandling:
    """Tests for exception handling and error responses."""
    
    def test_cpip_exception_to_dict(self):
        """Test CPIP exception serialization."""
        from server.exceptions import CPIPException
        
        exc = CPIPException(
            message="Test error",
            error_code=ErrorCode.INTERNAL_ERROR,
            status_code=500,
            details={"extra": "info"},
        )
        
        result = exc.to_dict()
        assert result["error"] == "INTERNAL_ERROR"
        assert result["message"] == "Test error"
        assert result["status"] == 500
        assert result["extra"] == "info"
    
    def test_validation_error_response(self):
        """Test validation error exception."""
        exc = CPIPValidationError(
            message="Invalid request",
            details={"field": "device_id"},
        )
        
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.status_code == 422


class TestServerIntegration:
    """Integration tests for server endpoints."""
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint returns API info."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient):
        """Test health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
