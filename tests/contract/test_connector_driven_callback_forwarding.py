"""
Contract: connector-driven callback forwarding settles orchestrator transfer.

This validates the path:
connector simulate-callback -> connector forwarding hook -> orchestrator callback endpoint.
"""

def test_connector_driven_callback_forwarding_settles_transfer(
    orchestrator_client, connector_client
) -> None:
    # 1) Create transfer and move to SUBMITTED_TO_RAIL so callback is valid
    create = orchestrator_client.post(
        "/v1/transfers",
        json={
            "sender_user_id": "u-cdf-1",
            "recipient_phone_e164": "+15550404040",
            "currency": "USD",
            "amount_minor": 880,
        },
        headers={"Idempotency-Key": "connector-driven-forward-1"},
    )
    assert create.status_code == 201
    transfer_id = create.json()["transfer_id"]

    orchestrator_client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "VALIDATED"})
    orchestrator_client.post(f"/v1/transfers/{transfer_id}/transition", json={"status": "RESERVED"})
    submitted = orchestrator_client.post(
        f"/v1/transfers/{transfer_id}/transition", json={"status": "SUBMITTED_TO_RAIL"}
    )
    assert submitted.status_code == 200
    external_ref = submitted.json()["connector_external_ref"]

    # 2) Create connector transaction for same external_ref
    payout = connector_client.post(
        "/v1/connectors/mock-bank-a/payouts",
        json={
            "transfer_id": transfer_id,
            "external_ref": external_ref,
            "amount_minor": 880,
            "currency": "USD",
            "destination": "acct-cdf-1",
        },
    )
    assert payout.status_code == 201

    # 3) Patch connector service forwarder to call orchestrator in-process
    simulate_route = next(
        r for r in connector_client.app.routes if getattr(r, "path", "") == "/v1/connectors/simulate-callback"
    )
    connector_globals = simulate_route.endpoint.__globals__
    ConnectorService = connector_globals["ConnectorGatewayService"]
    connector_settings = ConnectorService.apply_webhook.__globals__["settings"]

    old_enabled = connector_settings.callback_forward_enabled
    connector_settings.callback_forward_enabled = True

    original_forward = ConnectorService._forward_callback_to_orchestrator

    def _forward_inproc(self, txn):
        resp = orchestrator_client.post(
            "/v1/transfers/callbacks/connector",
            json={"external_ref": txn.external_ref, "status": txn.status.value},
        )
        return resp.status_code < 500

    ConnectorService._forward_callback_to_orchestrator = _forward_inproc

    try:
        simulate = connector_client.post(
            "/v1/connectors/simulate-callback",
            json={"external_ref": external_ref, "status": "CONFIRMED"},
        )
        assert simulate.status_code == 200
        assert simulate.json()["accepted"] is True

        transfer_after = orchestrator_client.get(f"/v1/transfers/{transfer_id}")
        assert transfer_after.status_code == 200
        assert transfer_after.json()["status"] == "SETTLED"
    finally:
        connector_settings.callback_forward_enabled = old_enabled
        ConnectorService._forward_callback_to_orchestrator = original_forward
