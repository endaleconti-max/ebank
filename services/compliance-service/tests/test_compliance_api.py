"""Tests for the compliance-service API."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.domain.models import Base, get_db
from app.main import app

# ── In-memory DB fixture ──────────────────────────────────────────────────────


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ── Screening: clear ──────────────────────────────────────────────────────────


def test_screen_clear_when_watchlist_empty(client):
    resp = client.post(
        "/v1/compliance/screen",
        json={"subject_id": "user-1", "name": "John Smith"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "clear"
    assert body["matched_entry_id"] is None
    assert body["log_id"] is not None


# ── Screening: exact hit ──────────────────────────────────────────────────────


def test_screen_hit_on_exact_name_match(client):
    client.post(
        "/v1/compliance/watchlist",
        json={"name": "Vladmir Badguy", "reason_code": "OFAC-SDN"},
    )
    resp = client.post(
        "/v1/compliance/screen",
        json={"subject_id": "user-2", "name": "Vladmir Badguy"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "hit"
    assert body["matched_entry_name"] == "Vladmir Badguy"
    assert body["reason_code"] == "OFAC-SDN"


def test_screen_hit_is_case_insensitive(client):
    client.post(
        "/v1/compliance/watchlist",
        json={"name": "Target Person", "reason_code": "UN-SANCTIONS"},
    )
    resp = client.post(
        "/v1/compliance/screen",
        json={"subject_id": "user-3", "name": "target person"},
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "hit"


# ── Screening: potential match (fuzzy) ───────────────────────────────────────


def test_screen_potential_match_within_threshold(client):
    # "Jahn Doe" vs "John Doe" → distance 1 (within default threshold of 2)
    client.post(
        "/v1/compliance/watchlist",
        json={"name": "John Doe", "reason_code": "PEP"},
    )
    resp = client.post(
        "/v1/compliance/screen",
        json={"subject_id": "user-4", "name": "Jahn Doe"},
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "potential_match"


def test_screen_clear_beyond_threshold(client):
    # "Jonathan Bartholomew" vs "John Doe" → large distance → clear
    client.post(
        "/v1/compliance/watchlist",
        json={"name": "John Doe", "reason_code": "PEP"},
    )
    resp = client.post(
        "/v1/compliance/screen",
        json={"subject_id": "user-5", "name": "Jonathan Bartholomew"},
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "clear"


# ── Screening: inactive entry is skipped ─────────────────────────────────────


def test_deactivated_entry_not_matched(client):
    r = client.post(
        "/v1/compliance/watchlist",
        json={"name": "Inactive Target", "reason_code": "INTERNAL-BLOCK"},
    )
    entry_id = r.json()["entry_id"]
    client.delete(f"/v1/compliance/watchlist/{entry_id}")

    resp = client.post(
        "/v1/compliance/screen",
        json={"subject_id": "user-6", "name": "Inactive Target"},
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "clear"


# ── Screening: audit log ──────────────────────────────────────────────────────


def test_screening_logged_after_clear(client):
    client.post(
        "/v1/compliance/screen",
        json={"subject_id": "user-log-1", "name": "Nobody"},
    )
    resp = client.get("/v1/compliance/log?subject_id=user-log-1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["entries"][0]["decision"] == "clear"


def test_screening_logged_after_hit(client):
    client.post(
        "/v1/compliance/watchlist",
        json={"name": "Bad Actor", "reason_code": "OFAC-SDN"},
    )
    client.post(
        "/v1/compliance/screen",
        json={"subject_id": "user-log-2", "name": "Bad Actor"},
    )
    resp = client.get("/v1/compliance/log?decision=hit")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["entries"][0]["matched_entry_name"] == "Bad Actor"


def test_screening_log_records_caller_id(client):
    client.post(
        "/v1/compliance/screen",
        json={"subject_id": "user-caller", "name": "Alice"},
        headers={"X-Caller-Id": "identity-service"},
    )
    resp = client.get("/v1/compliance/log?subject_id=user-caller")
    assert resp.status_code == 200
    assert resp.json()["entries"][0]["caller_id"] == "identity-service"


def test_screening_log_filters_by_decision(client):
    client.post(
        "/v1/compliance/watchlist",
        json={"name": "Evil Corp", "reason_code": "UN-SANCTIONS"},
    )
    client.post("/v1/compliance/screen", json={"subject_id": "u1", "name": "Good Guy"})
    client.post("/v1/compliance/screen", json={"subject_id": "u2", "name": "Evil Corp"})

    hit_resp = client.get("/v1/compliance/log?decision=hit")
    assert hit_resp.json()["total"] == 1

    clear_resp = client.get("/v1/compliance/log?decision=clear")
    assert clear_resp.json()["total"] == 1


# ── Watchlist CRUD ────────────────────────────────────────────────────────────


def test_add_watchlist_entry_success(client):
    resp = client.post(
        "/v1/compliance/watchlist",
        json={"name": "Test Entity", "reason_code": "PEP", "country_code": "KP"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Test Entity"
    assert body["reason_code"] == "PEP"
    assert body["country_code"] == "KP"
    assert body["active"] is True


def test_add_watchlist_empty_name_rejected(client):
    resp = client.post(
        "/v1/compliance/watchlist",
        json={"name": "   ", "reason_code": "PEP"},
    )
    assert resp.status_code == 422


def test_add_watchlist_invalid_reason_code_rejected(client):
    resp = client.post(
        "/v1/compliance/watchlist",
        json={"name": "Someone", "reason_code": "NOT-A-REAL-CODE"},
    )
    assert resp.status_code == 422


def test_list_watchlist_all(client):
    client.post("/v1/compliance/watchlist", json={"name": "Entry A", "reason_code": "PEP"})
    client.post("/v1/compliance/watchlist", json={"name": "Entry B", "reason_code": "UN-SANCTIONS"})
    resp = client.get("/v1/compliance/watchlist")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


def test_list_watchlist_active_only_excludes_deactivated(client):
    r = client.post(
        "/v1/compliance/watchlist",
        json={"name": "To Deactivate", "reason_code": "INTERNAL-BLOCK"},
    )
    entry_id = r.json()["entry_id"]
    client.post("/v1/compliance/watchlist", json={"name": "Keep Active", "reason_code": "PEP"})
    client.delete(f"/v1/compliance/watchlist/{entry_id}")

    resp = client.get("/v1/compliance/watchlist?active_only=true")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["entries"][0]["name"] == "Keep Active"


def test_deactivate_watchlist_entry_returns_204(client):
    r = client.post(
        "/v1/compliance/watchlist",
        json={"name": "Will Deactivate", "reason_code": "UNSPECIFIED"},
    )
    entry_id = r.json()["entry_id"]
    resp = client.delete(f"/v1/compliance/watchlist/{entry_id}")
    assert resp.status_code == 204


def test_deactivate_nonexistent_entry_returns_404(client):
    resp = client.delete("/v1/compliance/watchlist/no-such-entry")
    assert resp.status_code == 404


def test_deactivated_entry_still_listed_in_all(client):
    """Deactivate is a soft delete — entry remains in GET /watchlist (without active_only)."""
    r = client.post(
        "/v1/compliance/watchlist",
        json={"name": "Soft Deleted", "reason_code": "UNSPECIFIED"},
    )
    entry_id = r.json()["entry_id"]
    client.delete(f"/v1/compliance/watchlist/{entry_id}")

    resp = client.get("/v1/compliance/watchlist")
    assert resp.json()["total"] == 1
    assert resp.json()["entries"][0]["active"] is False


# ── Input validation ──────────────────────────────────────────────────────────


def test_screen_empty_subject_id_rejected(client):
    resp = client.post(
        "/v1/compliance/screen",
        json={"subject_id": "", "name": "Alice"},
    )
    assert resp.status_code == 422


def test_screen_empty_name_rejected(client):
    resp = client.post(
        "/v1/compliance/screen",
        json={"subject_id": "user-1", "name": ""},
    )
    assert resp.status_code == 422


def test_screen_invalid_subject_type_rejected(client):
    resp = client.post(
        "/v1/compliance/screen",
        json={"subject_id": "user-1", "subject_type": "unknown_type", "name": "Alice"},
    )
    assert resp.status_code == 422


def test_screen_transfer_subject_type_accepted(client):
    resp = client.post(
        "/v1/compliance/screen",
        json={"subject_id": "txn-999", "subject_type": "transfer", "name": "Alice"},
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "clear"
