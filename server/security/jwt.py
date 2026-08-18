"""
JWT token management and validation.

Handles creation, validation, and introspection of JWT tokens
for API authentication and service-to-service auth.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # Subject (usually user_id or device_id)
    iat: int  # Issued at (unix timestamp)
    exp: int  # Expiration (unix timestamp)
    aud: str = "cpip"  # Audience
    iss: str = "cpip-server"  # Issuer
    scopes: list[str] = []  # Permission scopes
    device_id: Optional[str] = None  # Optional device identifier
    client_id: Optional[str] = None  # Optional client identifier
    extra: dict[str, Any] = {}

    class Config:
        json_schema_extra = {
            "example": {
                "sub": "user-123",
                "iat": 1692547200,
                "exp": 1692633600,
                "aud": "cpip",
                "iss": "cpip-server",
                "scopes": ["read:packages", "write:builds"],
                "device_id": "termux-dev-001",
            }
        }


class TokenResponse(BaseModel):
    """Token response with metadata."""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int  # Seconds until expiration
    scope: str = ""


class JWTManager:
    """Manages JWT token lifecycle."""

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        expiration_hours: int = 24,
        refresh_expiration_days: int = 7,
    ):
        """
        Initialize JWT manager.

        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT algorithm (HS256, RS256, etc.)
            expiration_hours: Access token expiration time
            refresh_expiration_days: Refresh token expiration time
        """
        if not secret_key or secret_key == "cpip-dev-secret-change-in-production":
            logger.warning(
                "Using default or empty JWT secret! "
                "Set JWT_SECRET environment variable in production."
            )

        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expiration_hours = expiration_hours
        self.refresh_expiration_days = refresh_expiration_days

    def create_token(
        self,
        subject: str,
        scopes: list[str] | None = None,
        device_id: str | None = None,
        client_id: str | None = None,
        expires_delta: timedelta | None = None,
        extra: dict[str, Any] | None = None,
    ) -> str:
        """
        Create a new JWT access token.

        Args:
            subject: Token subject (user_id, device_id, etc.)
            scopes: List of permission scopes
            device_id: Optional device identifier
            client_id: Optional client identifier
            expires_delta: Custom expiration time (default: 24 hours)
            extra: Extra claims to add to payload

        Returns:
            Encoded JWT token
        """
        if expires_delta is None:
            expires_delta = timedelta(hours=self.expiration_hours)

        now = datetime.now(timezone.utc)
        expires = now + expires_delta

        payload = {
            "sub": subject,
            "iat": int(now.timestamp()),
            "exp": int(expires.timestamp()),
            "aud": "cpip",
            "iss": "cpip-server",
            "scopes": scopes or [],
            "device_id": device_id,
            "client_id": client_id,
            "extra": extra or {},
        }

        try:
            encoded = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.debug(f"Created JWT token for subject={subject}")
            return encoded
        except Exception as e:
            logger.error(f"Failed to create JWT token: {e}")
            raise

    def create_token_pair(
        self,
        subject: str,
        scopes: list[str] | None = None,
        device_id: str | None = None,
        client_id: str | None = None,
    ) -> tuple[str, str]:
        """
        Create access + refresh token pair.

        Args:
            subject: Token subject
            scopes: Permission scopes
            device_id: Optional device identifier
            client_id: Optional client identifier

        Returns:
            Tuple of (access_token, refresh_token)
        """
        access_token = self.create_token(
            subject=subject,
            scopes=scopes,
            device_id=device_id,
            client_id=client_id,
        )

        refresh_token = self.create_token(
            subject=subject,
            scopes=[],  # Refresh tokens don't have scopes
            expires_delta=timedelta(days=self.refresh_expiration_days),
            extra={"type": "refresh"},
        )

        return access_token, refresh_token

    def verify_token(self, token: str) -> TokenPayload:
        """
        Verify and decode JWT token.

        Args:
            token: JWT token string (with or without 'Bearer ' prefix)

        Returns:
            Decoded token payload

        Raises:
            JWTError: If token is invalid or expired
        """
        # Strip 'Bearer ' prefix if present
        if token.startswith("Bearer "):
            token = token[7:]

        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience="cpip",
                issuer="cpip-server",
            )
            return TokenPayload(**payload)
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            raise

    def refresh_access_token(self, refresh_token: str) -> str:
        """
        Create a new access token from a refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New access token

        Raises:
            JWTError: If refresh token is invalid
        """
        try:
            payload = self.verify_token(refresh_token)

            # Verify this is a refresh token
            if payload.extra.get("type") != "refresh":
                raise JWTError("Token is not a refresh token")

            # Create new access token with same subject and scopes
            new_access_token = self.create_token(
                subject=payload.sub,
                scopes=payload.scopes,
                device_id=payload.device_id,
                client_id=payload.client_id,
            )

            logger.debug(f"Refreshed access token for subject={payload.sub}")
            return new_access_token

        except JWTError as e:
            logger.error(f"Failed to refresh access token: {e}")
            raise

    def token_response(
        self,
        access_token: str,
        refresh_token: str | None = None,
        scopes: str = "",
    ) -> TokenResponse:
        """
        Format tokens as OAuth2-compatible response.

        Args:
            access_token: JWT access token
            refresh_token: Optional JWT refresh token
            scopes: Space-separated scopes

        Returns:
            TokenResponse with metadata
        """
        try:
            payload = self.verify_token(access_token)
            expires_in = payload.exp - int(datetime.now(timezone.utc).timestamp())

            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=max(0, expires_in),
                scope=scopes,
            )
        except JWTError:
            # If we can't decode, estimate expiration
            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=self.expiration_hours * 3600,
                scope=scopes,
            )
