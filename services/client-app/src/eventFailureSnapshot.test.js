import test from "node:test";
import assert from "node:assert/strict";

import { buildFailureSnapshotText } from "./eventFailureSnapshot.js";

test("buildFailureSnapshotText includes counts, rate, ids, and filters", () => {
  const text = buildFailureSnapshotText({
    transferId: "trf-300",
    filterQuery: "evStatus=FAILED&evQ=ledger",
    events: [
      { event_id: "evt-1", event_type: "TRANSFER_CREATED", to_status: "CREATED" },
      { event_id: "evt-2", event_type: "TRANSFER_STATUS_TRANSITIONED", to_status: "FAILED" },
      { event_id: "evt-3", event_type: "TRANSFER_CONNECTOR_CALLBACK_FAILED", to_status: "SUBMITTED_TO_RAIL" },
    ],
  });

  assert.match(text, /^Transfer: trf-300/m);
  assert.match(text, /^Visible events: 3/m);
  assert.match(text, /^Failed events: 2/m);
  assert.match(text, /^Failure rate 67%/m);
  assert.match(text, /^Failed IDs: evt-2, evt-3/m);
  assert.match(text, /^Filters: \?evStatus=FAILED&evQ=ledger/m);
});

test("buildFailureSnapshotText handles no failures and no filters", () => {
  const text = buildFailureSnapshotText({
    transferId: "trf-301",
    events: [{ event_id: "evt-1", event_type: "TRANSFER_CREATED", to_status: "CREATED" }],
    filterQuery: "",
  });

  assert.match(text, /^Failed events: 0/m);
  assert.match(text, /^Failure rate 0%/m);
  assert.match(text, /^Failed IDs: -/m);
  assert.match(text, /^Filters: \(none\)/m);
});
