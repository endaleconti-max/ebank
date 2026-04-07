import test from "node:test";
import assert from "node:assert/strict";

import { appendUniqueEvents, didEventFiltersChange } from "./eventFeedState.js";

test("appendUniqueEvents appends in order and ignores duplicate event_id entries", () => {
  const existing = [
    { event_id: "e-1", event_type: "TRANSFER_CREATED" },
    { event_id: "e-2", event_type: "TRANSFER_STATUS_TRANSITIONED" },
  ];

  const incoming = [
    { event_id: "e-2", event_type: "TRANSFER_STATUS_TRANSITIONED" },
    { event_id: "e-3", event_type: "TRANSFER_CONNECTOR_CALLBACK_CONFIRMED" },
    { event_id: "e-4", event_type: "TRANSFER_STATUS_TRANSITIONED" },
  ];

  const merged = appendUniqueEvents(existing, incoming);
  assert.deepEqual(
    merged.map((event) => event.event_id),
    ["e-1", "e-2", "e-3", "e-4"],
  );
});

test("didEventFiltersChange returns true when either filter value changes", () => {
  const prev = { eventType: "", toStatus: "" };

  assert.equal(didEventFiltersChange(prev, { eventType: "TRANSFER_CREATED", toStatus: "" }), true);
  assert.equal(didEventFiltersChange(prev, { eventType: "", toStatus: "FAILED" }), true);
});

test("didEventFiltersChange returns false when filters are unchanged", () => {
  const prev = { eventType: "TRANSFER_CREATED", toStatus: "FAILED" };
  const next = { eventType: "TRANSFER_CREATED", toStatus: "FAILED" };

  assert.equal(didEventFiltersChange(prev, next), false);
});

test("didEventFiltersChange detects createdAtFrom/To changes", () => {
  const base = { eventType: "", toStatus: "", createdAtFrom: "", createdAtTo: "" };

  assert.equal(
    didEventFiltersChange(base, { ...base, createdAtFrom: "2024-01-01T00:00:00Z" }),
    true,
  );
  assert.equal(
    didEventFiltersChange(base, { ...base, createdAtTo: "2024-12-31T23:59:59Z" }),
    true,
  );
  assert.equal(
    didEventFiltersChange(
      { ...base, createdAtFrom: "2024-01-01T00:00:00Z", createdAtTo: "2024-12-31T23:59:59Z" },
      { ...base, createdAtFrom: "2024-01-01T00:00:00Z", createdAtTo: "2024-12-31T23:59:59Z" },
    ),
    false,
  );
});

test("didEventFiltersChange detects searchText changes", () => {
  const base = { eventType: "", toStatus: "", createdAtFrom: "", createdAtTo: "", searchText: "" };

  assert.equal(
    didEventFiltersChange(base, { ...base, searchText: "failure" }),
    true,
  );
  assert.equal(
    didEventFiltersChange({ ...base, searchText: "failure" }, { ...base, searchText: "failure" }),
    false,
  );
});
