"""
Authentication middleware for API Gateway.

Enforces bearer token requirement on all protected routes and extracts request identity.
"""
from typing import Optional

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.domain.token_validator import get_token_validator


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Enforces bearer token authentication on protected routes.
    
    Behavior:
    - Extracts Authorization header from request
    - Validates bearer token
    - Stores request identity in request.state for downstream access
    - Returns 401 Unauthorized if token is missing or invalid
    - Propagates caller identity to all downstream service calls
    """
    
    # Routes that don't require authentication (e.g., health checks, public endpoints)
    UNPROTECTED_PATHS = {
        "/health",
        "/healthz",
        "/health/live",
        "/health/ready",
        "/docs",
        "/openapi.json",
        "/redoc",
    }
    
    def __init__(self, app):
        super().__init__(app)
        self._validator = get_token_validator()
    
    async def dispatch(self, request: Request, call_next):
        # Check if this is a protected route
        if not self._is_protected_path(request.url.path):
            # Unprotected path - proceed without auth check
            return await call_next(request)
        
        # Protected path - require authentication
        auth_header = request.headers.get("Authorization")
        bearer_token = self._validator.extract_bearer_token(auth_header)
        
        if not bearer_token:
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid Authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Validate the token
        validation_result = self._validator.validate_bearer_token(bearer_token)
        if not validation_result.valid:
            raise HTTPException(
                status_code=401,
                detail=validation_result.error_detail or "Invalid bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Store identity in request state for use in route handlers
        request.state.identity = validation_result.identity
        
        # Proceed to next middleware/route
        response = await call_next(request)
        
        # Add caller context to response headers for audit trail
        if hasattr(request.state, "identity"):
            response.headers["X-Caller-Id"] = request.state.identity.caller_id
        
        return response
    
    def _is_protected_path(self, path: str) -> bool:
        """Check if a path requires authentication."""
        # Unprotected paths are allowed without auth
        for unprotected in self.UNPROTECTED_PATHS:
            if path == unprotected or path.startswith(unprotected):
                return False
        
        # Everything else requires auth
        return True
