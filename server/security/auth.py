"""
Authentication middleware and dependencies for FastAPI.

Provides JWT verification middleware, dependency injection for
protected endpoints, and optional auth support.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, SecurityScopes
from jose import JWTError

from server.security.jwt import JWTManager, TokenPayload

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


class AuthContext:
    """Context information about authenticated request."""

    def __init__(self, token_payload: TokenPayload | None = None, is_anonymous: bool = False):
        """Initialize auth context.

        Args:
            token_payload: Decoded JWT payload (None if anonymous)
            is_anonymous: True if request has no authentication
        """
        self.token_payload = token_payload
        self.is_anonymous = is_anonymous
        self.subject = token_payload.sub if token_payload else "anonymous"
        self.scopes = token_payload.scopes if token_payload else []
        self.device_id = token_payload.device_id if token_payload else None
        self.client_id = token_payload.client_id if token_payload else None

    def has_scope(self, scope: str) -> bool:
        """Check if context has a specific scope.

        Args:
            scope: Scope to check (e.g., "write:builds")

        Returns:
            True if scope is present
        """
        return scope in self.scopes or "*" in self.scopes

    def __bool__(self) -> bool:
        """Return True if authenticated (not anonymous)."""
        return not self.is_anonymous


def create_jwt_dependency(jwt_manager: JWTManager, optional: bool = False):
    """
    Create a dependency for JWT verification.

    Args:
        jwt_manager: JWTManager instance
        optional: If True, anonymous requests are allowed

    Returns:
        Dependency function
    """

    async def verify_jwt(
        security_scopes: SecurityScopes,
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
    ) -> AuthContext:
        """
        Verify JWT token from Authorization header.

        Args:
            security_scopes: Scopes required for this endpoint
            credentials: Authorization credentials from header

        Returns:
            AuthContext with decoded token

        Raises:
            HTTPException: If token is invalid and not optional
        """
        if credentials is None:
            if optional:
                logger.debug("Anonymous request allowed (optional auth)")
                return AuthContext(is_anonymous=True)
            else:
                logger.warning("Missing authorization credentials")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing authorization credentials",
                    headers={"WWW-Authenticate": 'Bearer realm="cpip"'},
                )

        try:
            token_payload = jwt_manager.verify_token(credentials.credentials)

            # Check required scopes
            if security_scopes.scopes:
                has_required = any(
                    token_payload.has_scope(scope) for scope in security_scopes.scopes
                )
                if not has_required:
                    logger.warning(
                        f"Token missing required scopes: {security_scopes.scopes} "
                        f"has: {token_payload.scopes}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Insufficient permissions. Required: {security_scopes.scopes}",
                    )

            logger.debug(f"JWT verified for subject={token_payload.sub}")
            return AuthContext(token_payload=token_payload)

        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid authentication credentials: {str(e)}",
                headers={"WWW-Authenticate": 'Bearer realm="cpip"'},
            )
        except Exception as e:
            logger.error(f"Unexpected error in JWT verification: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication error",
            )

    return verify_jwt


def require_auth(jwt_manager: JWTManager, *required_scopes: str):
    """
    Decorator for endpoints requiring authentication.

    Args:
        jwt_manager: JWTManager instance
        *required_scopes: Scopes required for this endpoint

    Returns:
        Dependency function

    Example:
        @app.get("/api/v1/builds")
        async def list_builds(
            auth: AuthContext = Depends(require_auth(jwt_manager, "read:builds"))
        ):
            if not auth:
                raise HTTPException(status_code=401)
            ...
    """

    async def dependency(
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
    ) -> AuthContext:
        if credentials is None:
            logger.warning("Missing authorization credentials for protected endpoint")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization credentials",
                headers={"WWW-Authenticate": 'Bearer realm="cpip"'},
            )

        try:
            token_payload = jwt_manager.verify_token(credentials.credentials)

            # Check required scopes
            if required_scopes:
                has_required = any(
                    token_payload.has_scope(scope) for scope in required_scopes
                )
                if not has_required:
                    logger.warning(
                        f"Token missing required scopes: {required_scopes} "
                        f"has: {token_payload.scopes}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Insufficient permissions. Required: {required_scopes}",
                    )

            logger.debug(f"JWT verified for subject={token_payload.sub}")
            return AuthContext(token_payload=token_payload)

        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid authentication credentials: {str(e)}",
                headers={"WWW-Authenticate": 'Bearer realm="cpip"'},
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in JWT verification: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication error",
            )

    return dependency


def optional_auth(jwt_manager: JWTManager):
    """
    Dependency for endpoints with optional authentication.

    Args:
        jwt_manager: JWTManager instance

    Returns:
        Dependency function

    Example:
        @app.get("/api/v1/health")
        async def health(
            auth: AuthContext = Depends(optional_auth(jwt_manager))
        ):
            ...
    """

    async def dependency(
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
    ) -> AuthContext:
        if credentials is None:
            logger.debug("Anonymous request (optional auth)")
            return AuthContext(is_anonymous=True)

        try:
            token_payload = jwt_manager.verify_token(credentials.credentials)
            logger.debug(f"JWT verified for subject={token_payload.sub}")
            return AuthContext(token_payload=token_payload)
        except JWTError as e:
            logger.warning(f"JWT verification failed, allowing anonymous: {e}")
            return AuthContext(is_anonymous=True)
        except Exception as e:
            logger.warning(f"Error in optional JWT verification: {e}, allowing anonymous")
            return AuthContext(is_anonymous=True)

    return dependency
