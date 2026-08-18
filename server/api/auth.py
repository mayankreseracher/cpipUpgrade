"""
Authentication API endpoints.

Provides token generation, refresh, and introspection endpoints.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from server.config import server_config
from server.security.auth import AuthContext, optional_auth
from server.security.jwt import JWTManager, TokenResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# Initialize JWT manager
jwt_manager = JWTManager(
    secret_key=server_config.jwt_secret,
    algorithm=server_config.jwt_algorithm,
    expiration_hours=server_config.jwt_expiration_hours,
    refresh_expiration_days=server_config.jwt_refresh_expiration_days,
)


class TokenRequest(BaseModel):
    """Request for new access token."""

    subject: str = Field(..., description="Subject for token (user_id, device_id, etc.)")
    scopes: list[str] = Field(default=[], description="Permission scopes")
    device_id: Optional[str] = Field(None, description="Optional device identifier")
    client_id: Optional[str] = Field(None, description="Optional client identifier")


class RefreshTokenRequest(BaseModel):
    """Request to refresh access token."""

    refresh_token: str = Field(..., description="Valid refresh token")


class TokenIntrospectionRequest(BaseModel):
    """Request to introspect token."""

    token: str = Field(..., description="Token to introspect")


class TokenIntrospectionResponse(BaseModel):
    """Token introspection response."""

    active: bool = Field(..., description="Whether token is valid and not expired")
    scope: str = Field("", description="Space-separated scopes")
    sub: Optional[str] = None
    aud: str = "cpip"
    iss: str = "cpip-server"
    iat: Optional[int] = None
    exp: Optional[int] = None
    device_id: Optional[str] = None
    client_id: Optional[str] = None


@router.post("/token", response_model=TokenResponse, summary="Generate new token")
async def create_token(request: TokenRequest) -> TokenResponse:
    """
    Generate new access token + refresh token.

    Returns:
        TokenResponse with access_token, refresh_token, and metadata
    """
    try:
        access_token, refresh_token = jwt_manager.create_token_pair(
            subject=request.subject,
            scopes=request.scopes,
            device_id=request.device_id,
            client_id=request.client_id,
        )

        logger.info(
            f"Generated token pair for subject={request.subject} "
            f"scopes={request.scopes}"
        )

        return jwt_manager.token_response(
            access_token=access_token,
            refresh_token=refresh_token,
            scopes=" ".join(request.scopes),
        )

    except Exception as e:
        logger.error(f"Failed to generate token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate token",
        )


@router.post("/refresh", response_model=TokenResponse, summary="Refresh access token")
async def refresh_token(request: RefreshTokenRequest) -> TokenResponse:
    """
    Generate new access token from refresh token.

    Returns:
        TokenResponse with new access_token
    """
    try:
        new_access_token = jwt_manager.refresh_access_token(request.refresh_token)
        logger.info("Successfully refreshed access token")

        return jwt_manager.token_response(access_token=new_access_token)

    except Exception as e:
        logger.warning(f"Failed to refresh token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )


@router.post(
    "/introspect",
    response_model=TokenIntrospectionResponse,
    summary="Introspect token",
)
async def introspect_token(request: TokenIntrospectionRequest) -> TokenIntrospectionResponse:
    """
    Introspect a token to get its claims and validity.

    Returns:
        TokenIntrospectionResponse with token claims
    """
    try:
        payload = jwt_manager.verify_token(request.token)
        logger.debug(f"Introspected token for subject={payload.sub}")

        return TokenIntrospectionResponse(
            active=True,
            scope=" ".join(payload.scopes),
            sub=payload.sub,
            aud=payload.aud,
            iss=payload.iss,
            iat=payload.iat,
            exp=payload.exp,
            device_id=payload.device_id,
            client_id=payload.client_id,
        )

    except Exception as e:
        logger.warning(f"Token introspection failed: {e}")
        return TokenIntrospectionResponse(active=False)


@router.get("/me", summary="Get current user info")
async def get_current_user(
    auth: AuthContext = Depends(optional_auth(jwt_manager)),
):
    """
    Get information about the current authenticated user/device.

    Returns:
        User information from token payload
    """
    if not auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    return {
        "subject": auth.subject,
        "device_id": auth.device_id,
        "client_id": auth.client_id,
        "scopes": auth.scopes,
    }
