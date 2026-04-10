"""
Authentication and authorization domain models for API Gateway.

Provides:
- Request identity context (caller ID, user type, permissions)
- Token validation contract
"""
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class CallerType(str, Enum):
    """Represents the type of caller making the request."""
    SERVICE = "service"
    USER = "user"
    ADMIN = "admin"
    SYSTEM = "system"


class Permission(str, Enum):
    """Represents granular permissions that can be granted to callers."""
    LIST_TRANSFERS = "transfer:list"
    CREATE_TRANSFER = "transfer:create"
    VIEW_TRANSFER = "transfer:view"
    CANCEL_TRANSFER = "transfer:cancel"
    UPDATE_TRANSFER_NOTE = "transfer:update_note"
    TRANSITION_TRANSFER = "transfer:transition"
    
    LIST_CONNECTORS = "connector:list"
    VIEW_CONNECTOR_TRANSACTIONS = "connector:view_transactions"
    SIMULATE_CONNECTOR_CALLBACK = "connector:simulate_callback"
    
    VIEW_RECONCILIATION = "reconciliation:view"
    RUN_RECONCILIATION = "reconciliation:run"
    VIEW_AUTH_AUDIT = "auth:view_audit"

    CREATE_USER = "identity:create_user"
    VIEW_USER = "identity:view_user"
    SUBMIT_KYC = "identity:submit_kyc"
    MANAGE_ACCOUNT_STATUS = "identity:manage_account_status"
    VIEW_ACCOUNT_AUDIT_LOG = "identity:view_account_audit_log"
    
    VIEW_ALIASES = "alias:view"
    MANAGE_ALIASES = "alias:manage"
    VIEW_ALIAS_AUDIT = "alias:view_audit"

    VIEW_RISK_RULES = "risk:view_rules"
    MANAGE_RISK_RULES = "risk:manage_rules"
    VIEW_RISK_LOG = "risk:view_log"
    EVALUATE_RISK = "risk:evaluate"

    VIEW_COMPLIANCE_WATCHLIST = "compliance:view_watchlist"
    MANAGE_COMPLIANCE_WATCHLIST = "compliance:manage_watchlist"
    VIEW_COMPLIANCE_LOG = "compliance:view_log"
    SCREEN_COMPLIANCE_SUBJECT = "compliance:screen"


@dataclass
class RequestIdentity:
    """
    Represents the authenticated identity making a request.
    
    Attributes:
        caller_id: Unique identifier for the caller (user ID, service name, etc)
        caller_type: Type of caller (service, user, admin, system)
        permissions: Set of permissions granted to this caller
        token: The raw bearer token (not typically exposed to downstream services)
    """
    caller_id: str
    caller_type: CallerType
    permissions: List[Permission]
    token: Optional[str] = None
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if this identity has a specific permission."""
        return permission in self.permissions
    
    def to_headers(self) -> dict:
        """Convert identity to headers for downstream service calls."""
        return {
            "X-Caller-Id": self.caller_id,
            "X-Caller-Type": self.caller_type.value,
            "X-Caller-Permissions": ",".join(p.value for p in self.permissions),
        }


@dataclass
class TokenValidationResult:
    """Result of token validation during auth."""
    valid: bool
    identity: Optional[RequestIdentity] = None
    error_detail: Optional[str] = None
