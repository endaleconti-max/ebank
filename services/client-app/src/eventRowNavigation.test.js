import test from "node:test";
import assert from "node:assert/strict";

import {
  getAdjacentEventId,
  getAdjacentFailureEventId,
  isFailureEvent,
} from "./eventRowNavigation.js";

test("getAdjacentEventId returns null for empty lists", () => {
  assert.equal(getAdjacentEventId([], null, "next"), null);
});

test("getAdjacentEventId starts at first/last when no current id", () => {
  const ids = ["evt-1", "evt-2", "evt-3"];
  assert.equal(getAdjacentEventId(ids, null, "next"), "evt-1");
  assert.equal(getAdjacentEventId(ids, null, "previous"), "evt-3");
});

test("getAdjacentEventId moves and wraps around", () => {
  const ids = ["evt-1", "evt-2", "evt-3"];
  assert.equal(getAdjacentEventId(ids, "evt-2", "next"), "evt-3");
  assert.equal(getAdjacentEventId(ids, "evt-3", "next"), "evt-1");
  assert.equal(getAdjacentEventId(ids, "evt-1", "previous"), "evt-3");
  assert.equal(getAdjacentEventId(ids, "evt-2", "previous"), "evt-1");
});

test("getAdjacentEventId falls back when current id is not visible", () => {
  const ids = ["evt-1", "evt-2"];
  assert.equal(getAdjacentEventId(ids, "evt-missing", "next"), "evt-1");
  assert.equal(getAdjacentEventId(ids, "evt-missing", "previous"), "evt-2");
});

test("isFailureEvent detects failure by status, type, or reason", () => {
  assert.equal(isFailureEvent({ to_status: "FAILED" }), true);
  assert.equal(isFailureEvent({ event_type: "TRANSFER_CONNECTOR_CALLBACK_FAILED" }), true);
  assert.equal(isFailureEvent({ failure_reason: "connector_unavailable" }), true);
  assert.equal(isFailureEvent({ to_status: "SETTLED", event_type: "TRANSFER_STATUS_TRANSITIONED" }), false);
});

test("getAdjacentFailureEventId navigates only failure events with wrap-around", () => {
  const events = [
    { event_id: "evt-1", to_status: "CREATED", event_type: "TRANSFER_CREATED" },
    { event_id: "evt-2", to_status: "FAILED", event_type: "TRANSFER_STATUS_TRANSITIONED" },
    { event_id: "evt-3", to_status: "SETTLED", event_type: "TRANSFER_STATUS_TRANSITIONED" },
    { event_id: "evt-4", event_type: "TRANSFER_CONNECTOR_CALLBACK_FAILED" },
  ];

  assert.equal(getAdjacentFailureEventId(events, null, "next"), "evt-2");
  assert.equal(getAdjacentFailureEventId(events, null, "previous"), "evt-4");
  assert.equal(getAdjacentFailureEventId(events, "evt-2", "next"), "evt-4");
  assert.equal(getAdjacentFailureEventId(events, "evt-4", "next"), "evt-2");
  assert.equal(getAdjacentFailureEventId(events, "evt-2", "previous"), "evt-4");
});
