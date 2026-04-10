"""
Token validation service for API Gateway authentication.

Supports:
- Bearer token extraction from Authorization header
- Token validation (JWT verification or service-level validation)
- Token expiration and revocation tracking
"""
import os
import json
from typing import Optional
from datetime import datetime, timedelta
import hashlib

from app.domain.auth_models import RequestIdentity, TokenValidationResult, CallerType, Permission


class TokenValidator:
    """
    Validates bearer tokens and extracts caller identity.
    
    For the initial implementation:
    - Supports hardcoded test tokens (for development)
    - Can be extended to support JWT verification or external validation
    - In production, should integrate with secure token service
    """
    
    # Development/test tokens - in production these come from secure token store
    KNOWN_TOKENS = {
        "token-sys-orchestrator": {
            "caller_id": "orchestrator-service",
            "caller_type": CallerType.SERVICE,
            "permissions": [Permission.VIEW_TRANSFER, Permission.UPDATE_TRANSFER_NOTE],
        },
        "token-sys-lexn-reconciliation": {
            "caller_id": "reconciliation-service",
            "caller_type": CallerType.SERVICE,
            "permissions": [Permission.VIEW_RECONCILIATION, Permission.RUN_RECONCILIATION],
        },
        "token-sys-alias": {
            "caller_id": "alias-service",
            "caller_type": CallerType.SERVICE,
            "permissions": [Permission.VIEW_ALIASES, Permission.MANAGE_ALIASES],
        },
        "token-user-admin-001": {
            "caller_id": "admin-user-001",
            "caller_type": CallerType.ADMIN,
            "permissions": [
                Permission.LIST_TRANSFERS,
                Permission.CREATE_TRANSFER,
                Permission.VIEW_TRANSFER,
                Permission.CANCEL_TRANSFER,
                Permission.UPDATE_TRANSFER_NOTE,
                Permission.TRANSITION_TRANSFER,
                Permission.LIST_CONNECTORS,
                Permission.VIEW_CONNECTOR_TRANSACTIONS,
                Permission.VIEW_RECONCILIATION,
                Permission.RUN_RECONCILIATION,
                Permission.VIEW_AUTH_AUDIT,
                Permission.CREATE_USER,
                Permission.VIEW_USER,
                Permission.SUBMIT_KYC,
                Permission.VIEW_ALIASES,
                Permission.VIEW_ALIAS_AUDIT,
            ],
        },
        "token-user-app-001": {
            "caller_id": "user-app-001",
            "caller_type": CallerType.USER,
            "permissions": [Permission.LIST_TRANSFERS, Permission.CREATE_TRANSFER, Permission.VIEW_TRANSFER],
        },
    }
    
    def __init__(self):
        """Initialize token validator with optional environment-based token store."""
        self._revoked_tokens = set()
        # In production: load tokens from secure store via environment config
        self._tokens = self.KNOWN_TOKENS.copy()
    
    def validate_bearer_token(self, bearer_token: str) -> TokenValidationResult:
        """
        Validate a bearer token and extract caller identity.
        
        Args:
            bearer_token: The token string (without 'Bearer ' prefix)
            
        Returns:
            TokenValidationResult with identity if valid, error if not
        """
        if not bearer_token:
            return TokenValidationResult(
                valid=False,
                error_detail="Bearer token is empty"
            )
        
        # Check if token is revoked
        if bearer_token in self._revoked_tokens:
            return TokenValidationResult(
                valid=False,
                error_detail="Token has been revoked"
            )
        
        # Look up known tokens (development)
        if bearer_token in self._tokens:
            token_data = self._tokens[bearer_token]
            identity = RequestIdentity(
                caller_id=token_data["caller_id"],
                caller_type=token_data["caller_type"],
                permissions=token_data["permissions"],
                token=bearer_token,
            )
            return TokenValidationResult(valid=True, identity=identity)
        
        # In production: attempt JWT verification here
        # For now, return invalid for unknown tokens
        return TokenValidationResult(
            valid=False,
            error_detail=f"Unknown or invalid token: {bearer_token[:20]}..."
        )
    
    def extract_bearer_token(self, auth_header: Optional[str]) -> Optional[str]:
        """
        Extract bearer token from Authorization header.
        
        Args:
            auth_header: The Authorization header value
            
        Returns:
            Token string if valid Bearer format, None otherwise
        """
        if not auth_header:
            return None
        
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        
        return parts[1]
    
    def revoke_token(self, bearer_token: str) -> None:
        """
        Revoke a token so it can no longer be used.
        
        Args:
            bearer_token: The token to revoke
        """
        self._revoked_tokens.add(bearer_token)
    
    def create_test_token(
        self,
        caller_id: str,
        caller_type: CallerType,
        permissions: list = None,
    ) -> str:
        """
        Create a test token for development/testing.
        
        Args:
            caller_id: Unique identifier for caller
            caller_type: Type of caller
            permissions: List of permissions to grant
            
        Returns:
            A test bearer token string
        """
        if permissions is None:
            permissions = []
        
        # Generate simple hash-based token for testing
        token_material = f"{caller_id}:{caller_type.value}:{datetime.utcnow().isoformat()}"
        token = "token-" + hashlib.sha256(token_material.encode()).hexdigest()[:32]
        
        self._tokens[token] = {
            "caller_id": caller_id,
            "caller_type": caller_type,
            "permissions": permissions,
        }
        
        return token


# Global token validator instance
_validator = TokenValidator()


def get_token_validator() -> TokenValidator:
    """Get the global token validator instance."""
    return _validator
