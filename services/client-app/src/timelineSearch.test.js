import test from "node:test";
import assert from "node:assert/strict";

import { filterEventsBySearch } from "./timelineSearch.js";

test("filterEventsBySearch returns all events when search text is blank", () => {
  const events = [{ event_id: "e-1", event_type: "TRANSFER_CREATED" }];
  assert.equal(filterEventsBySearch(events, "   ").length, 1);
});

test("filterEventsBySearch matches event_type and failure_reason case-insensitively", () => {
  const events = [
    { event_id: "e-1", event_type: "TRANSFER_CREATED", failure_reason: null, from_status: null, to_status: "CREATED" },
    { event_id: "e-2", event_type: "TRANSFER_CONNECTOR_CALLBACK_FAILED", failure_reason: "Bank timeout", from_status: "SUBMITTED_TO_RAIL", to_status: "FAILED" },
  ];

  assert.deepEqual(filterEventsBySearch(events, "callback").map((event) => event.event_id), ["e-2"]);
  assert.deepEqual(filterEventsBySearch(events, "timeout").map((event) => event.event_id), ["e-2"]);
  assert.deepEqual(filterEventsBySearch(events, "failed").map((event) => event.event_id), ["e-2"]);
});