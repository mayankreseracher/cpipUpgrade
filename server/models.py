"""
Pydantic request/response models for validation and serialization.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, validator


class DeviceRegistration(BaseModel):
    """Device registration request model."""
    
    device_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique device identifier",
        example="device-abc123",
    )
    platform: str | None = Field(
        None,
        max_length=50,
        description="Platform (e.g., 'android', 'termux')",
    )
    version: str | None = Field(
        None,
        max_length=50,
        description="Client version",
    )
    
    @validator("device_id")
    def validate_device_id(cls, v: str) -> str:
        """Validate device ID format."""
        # Allow alphanumeric, hyphens, and underscores
        import re
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                "device_id must contain only alphanumeric characters, hyphens, and underscores"
            )
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "device_id": "device-001",
                "platform": "android",
                "version": "1.0.0",
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    status: int = Field(..., description="HTTP status code")
    details: dict | None = Field(None, description="Additional error details")


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(..., example="healthy")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
