import test from "node:test";
import assert from "node:assert/strict";

import { buildFailureSnapshotReport } from "./eventFailureReport.js";

test("buildFailureSnapshotReport includes summary and failed timeline entries", () => {
  const text = buildFailureSnapshotReport({
    transferId: "trf-901",
    filterQuery: "evStatus=FAILED&evQ=connector",
    events: [
      { event_id: "evt-1", event_type: "TRANSFER_CREATED", to_status: "CREATED", created_at: "2026-04-07T10:00:00Z" },
      {
        event_id: "evt-2",
        event_type: "TRANSFER_STATUS_TRANSITIONED",
        from_status: "CREATED",
        to_status: "FAILED",
        created_at: "2026-04-07T10:01:00Z",
        failure_reason: "connector_timeout",
      },
    ],
  });

  assert.match(text, /^Failure Snapshot Report/m);
  assert.match(text, /^Transfer: trf-901/m);
  assert.match(text, /^Visible events: 2/m);
  assert.match(text, /^Failed events: 1/m);
  assert.match(text, /^Failure rate 50%/m);
  assert.match(text, /^Filters: \?evStatus=FAILED&evQ=connector/m);
  assert.match(text, /^Failed Event IDs/m);
  assert.match(text, /^evt-2$/m);
  assert.match(text, /^1\. 2026-04-07T10:01:00Z TRANSFER_STATUS_TRANSITIONED CREATED->FAILED reason=connector_timeout/m);
});

test("buildFailureSnapshotReport handles no failed events", () => {
  const text = buildFailureSnapshotReport({
    transferId: "trf-902",
    events: [{ event_id: "evt-1", event_type: "TRANSFER_CREATED", to_status: "CREATED", created_at: "2026-04-07T10:00:00Z" }],
    filterQuery: "",
  });

  assert.match(text, /^Failed events: 0/m);
  assert.match(text, /^Failure rate 0%/m);
  assert.match(text, /^Filters: \(none\)/m);
  assert.match(text, /^Failed Event Timeline/m);
  assert.match(text, /^-$/m);
});
