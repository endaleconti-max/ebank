import test from "node:test";
import assert from "node:assert/strict";

import { buildFailedEventsDigest, getFailureEvents } from "./eventFailureDigest.js";

test("getFailureEvents returns only failure-related events", () => {
  const events = [
    { event_id: "evt-1", event_type: "TRANSFER_CREATED", to_status: "CREATED" },
    { event_id: "evt-2", event_type: "TRANSFER_STATUS_TRANSITIONED", to_status: "FAILED" },
    { event_id: "evt-3", event_type: "TRANSFER_CONNECTOR_CALLBACK_FAILED", to_status: "SUBMITTED_TO_RAIL" },
    { event_id: "evt-4", event_type: "TRANSFER_STATUS_TRANSITIONED", to_status: "SETTLED", failure_reason: "late_settlement" },
  ];

  const failed = getFailureEvents(events);
  assert.deepEqual(failed.map((event) => event.event_id), ["evt-2", "evt-3", "evt-4"]);
});

test("buildFailedEventsDigest includes header and only failed event lines", () => {
  const digest = buildFailedEventsDigest(
    [
      {
        created_at: "2026-04-07T10:00:00Z",
        event_type: "TRANSFER_CREATED",
        from_status: null,
        to_status: "CREATED",
        failure_reason: null,
      },
      {
        created_at: "2026-04-07T10:01:00Z",
        event_type: "TRANSFER_STATUS_TRANSITIONED",
        from_status: "CREATED",
        to_status: "FAILED",
        failure_reason: "connector_timeout",
      },
    ],
    "trf-88",
  );

  assert.match(digest, /^Transfer: trf-88/m);
  assert.match(digest, /^Failed events: 1/m);
  assert.match(digest, /^1\. 2026-04-07T10:01:00Z TRANSFER_STATUS_TRANSITIONED CREATED->FAILED reason=connector_timeout/m);
});

test("buildFailedEventsDigest handles no failed events", () => {
  const digest = buildFailedEventsDigest(
    [{ event_type: "TRANSFER_CREATED", to_status: "CREATED", created_at: "2026-04-07T10:00:00Z" }],
    "trf-99",
  );

  assert.match(digest, /^Transfer: trf-99/m);
  assert.match(digest, /^Failed events: 0/m);
});
