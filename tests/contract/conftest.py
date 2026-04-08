"""
Cross-service contract test suite.

Each test loads multiple FastAPI service apps in-process, wires them to
isolated file-based SQLite DBs, and exercises realistic multi-step flows
that span more than one service boundary.

Run from the project root with the identity-service venv:

    .venv-contract/bin/pytest tests/contract/ -v

Environment requirements
------------------------
The repo-local contract-test environment must include the shared dependencies
used across all in-process services (see requirements-contract.txt).

How module isolation works
--------------------------
All services share the same internal package structure (app.main, app.config …).
_load_service() clears all app.* entries from sys.modules and prepends the
target service directory to sys.path before each import.  Once the FastAPI app
object and the SQLAlchemy Base/engine references are captured, the modules can
be safely renamed in sys.modules (or the next service can overwrite them)
because the captured objects hold all necessary closures (Depends(get_db) was
already bound to the service-specific SessionLocal at decoration time).
"""

import importlib
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SERVICES_ROOT = _PROJECT_ROOT / "services"

# One shared temp directory for all contract-test DB files
_TMPDIR = tempfile.mkdtemp(prefix="ebank_contract_")

# Map logical name → SQLite file path
_DB_FILES: Dict[str, str] = {
    "identity": os.path.join(_TMPDIR, "identity.db"),
    "alias": os.path.join(_TMPDIR, "alias.db"),
    "ledger": os.path.join(_TMPDIR, "ledger.db"),
    "orchestrator": os.path.join(_TMPDIR, "orchestrator.db"),
    "api_gateway": os.path.join(_TMPDIR, "api_gateway_unused.db"),
    "connector": os.path.join(_TMPDIR, "connector.db"),
    "recon": os.path.join(_TMPDIR, "recon.db"),
}


def _load_service(
    service_dir_name: str,
    env_prefix: str,
    db_key: str,
    has_db: bool = True,
) -> Dict[str, Any]:
    """
    Load a service's FastAPI app in an isolated sys.modules context.
    Returns dict with keys: app, Base, engine.
    """
    service_path = str(_SERVICES_ROOT / service_dir_name)
    db_url = f"sqlite:///{_DB_FILES[db_key]}"

    # 1. Purge all app.* modules so the next service gets a fresh namespace
    for key in list(sys.modules.keys()):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]

    # 2. Set DB URL env var before pydantic-settings reads it (if service has DB)
    if has_db:
        os.environ[f"{env_prefix}_DATABASE_URL"] = db_url

    # 3. Put this service's directory first in sys.path
    sys.path = [service_path] + [p for p in sys.path if p != service_path]

    # 4. Import fresh copies of the service modules
    main_mod = importlib.import_module("app.main")
    if has_db:
        db_mod = importlib.import_module("app.infrastructure.db")
        return {
            "app": main_mod.app,
            "Base": db_mod.Base,
            "engine": db_mod.engine,
        }

    return {
        "app": main_mod.app,
    }


# ---------------------------------------------------------------------------
# Load all services once at module scope (before any pytest fixtures run).
# Order matters: each _load_service() overwrites sys.modules['app.*'], but the
# previously captured app/Base/engine references remain valid Python objects.
# ---------------------------------------------------------------------------
_services: Dict[str, Dict[str, Any]] = {}


def _init_all_services() -> None:
    _services["identity"] = _load_service("identity-service", "IDENTITY", "identity")
    _services["alias"] = _load_service("alias-service", "ALIAS", "alias")
    _services["ledger"] = _load_service("ledger-service", "LEDGER", "ledger")
    os.environ["ORCHESTRATOR_CONNECTOR_SUBMISSION_ENABLED"] = "true"
    os.environ["ORCHESTRATOR_CONNECTOR_SUBMISSION_MODE"] = "mock"
    _services["orchestrator"] = _load_service("payment-orchestrator", "ORCHESTRATOR", "orchestrator")
    _services["api_gateway"] = _load_service("api-gateway", "API_GATEWAY", "api_gateway", has_db=False)
    _services["connector"] = _load_service("connector-gateway", "CONNECTOR", "connector")

    # Reconciliation needs file paths to the ledger + connector DBs (raw sqlite3)
    os.environ["RECON_LEDGER_DB_PATH"] = _DB_FILES["ledger"]
    os.environ["RECON_CONNECTOR_DB_PATH"] = _DB_FILES["connector"]
    _services["recon"] = _load_service("reconciliation-service", "RECON", "recon")


_init_all_services()

# Create one TestClient per service (reused across tests; tables are reset by fixture)
_clients: Dict[str, TestClient] = {
    name: TestClient(svc["app"]) for name, svc in _services.items()
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_all_dbs() -> None:
    """Drop and recreate every service's tables before each test."""
    for svc in _services.values():
        if "Base" in svc and "engine" in svc:
            svc["Base"].metadata.drop_all(bind=svc["engine"])
            svc["Base"].metadata.create_all(bind=svc["engine"])


@pytest.fixture()
def identity_client() -> TestClient:
    return _clients["identity"]


@pytest.fixture()
def alias_client() -> TestClient:
    return _clients["alias"]


@pytest.fixture()
def ledger_client() -> TestClient:
    return _clients["ledger"]


@pytest.fixture()
def orchestrator_client() -> TestClient:
    return _clients["orchestrator"]


@pytest.fixture()
def connector_client() -> TestClient:
    return _clients["connector"]


@pytest.fixture()
def recon_client() -> TestClient:
    return _clients["recon"]


@pytest.fixture()
def gateway_client() -> TestClient:
    return _clients["api_gateway"]
