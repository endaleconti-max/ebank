"""
Pytest configuration for api-gateway tests.

Disables authentication enforcement during tests to allow unauth requests.
"""
import os
import sys

# Disable authentication before importing app
os.environ["ENFORCE_AUTHENTICATION"] = "false"
os.environ["ENFORCE_AUTHORIZATION"] = "false"

import pytest


# Re-import app config to pick up the env var
from app.config import settings as _settings


@pytest.fixture(scope="session", autouse=True)
def verify_auth_disabled():
    """Verify authentication is disabled for tests."""
    assert _settings.enforce_authentication is False, "Authentication should be disabled for tests"
    assert _settings.enforce_authorization is False, "Authorization should be disabled for tests"

