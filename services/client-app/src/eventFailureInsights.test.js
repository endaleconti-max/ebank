import test from "node:test";
import assert from "node:assert/strict";

import {
  buildFailedEventIdsText,
  formatFailureRateLabel,
  getFailedEventIds,
} from "./eventFailureInsights.js";

test("getFailedEventIds returns only non-empty failed event IDs", () => {
  const events = [
    { event_id: "evt-1", to_status: "CREATED", event_type: "TRANSFER_CREATED" },
    { event_id: "evt-2", to_status: "FAILED", event_type: "TRANSFER_STATUS_TRANSITIONED" },
    { event_id: "", to_status: "FAILED", event_type: "TRANSFER_STATUS_TRANSITIONED" },
    { event_id: "evt-3", event_type: "TRANSFER_CONNECTOR_CALLBACK_FAILED" },
  ];

  assert.deepEqual(getFailedEventIds(events), ["evt-2", "evt-3"]);
});

test("formatFailureRateLabel rounds to nearest percent", () => {
  assert.equal(formatFailureRateLabel(0, 0), "Failure rate 0%");
  assert.equal(formatFailureRateLabel(1, 3), "Failure rate 33%");
  assert.equal(formatFailureRateLabel(2, 3), "Failure rate 67%");
});

test("buildFailedEventIdsText includes transfer header and csv IDs", () => {
  const text = buildFailedEventIdsText(
    [
      { event_id: "evt-1", to_status: "FAILED", event_type: "TRANSFER_STATUS_TRANSITIONED" },
      { event_id: "evt-2", event_type: "TRANSFER_CONNECTOR_CALLBACK_FAILED" },
      { event_id: "evt-3", event_type: "TRANSFER_CREATED", to_status: "CREATED" },
    ],
    "trf-17",
  );

  assert.match(text, /^Transfer: trf-17/m);
  assert.match(text, /^Failed event IDs: 2/m);
  assert.match(text, /evt-1, evt-2/m);
});
