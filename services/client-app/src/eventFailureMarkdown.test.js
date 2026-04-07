import test from "node:test";
import assert from "node:assert/strict";

import { buildFailureMarkdownSummary } from "./eventFailureMarkdown.js";

test("buildFailureMarkdownSummary includes summary bullets and failed timeline", () => {
  const text = buildFailureMarkdownSummary({
    transferId: "trf-720",
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

  assert.match(text, /^## Failure Summary/m);
  assert.match(text, /^- Transfer: trf-720/m);
  assert.match(text, /^- Visible events: 2/m);
  assert.match(text, /^- Failed events: 1/m);
  assert.match(text, /^- Failure rate 50%/m);
  assert.match(text, /^- Filters: \?evStatus=FAILED&evQ=connector/m);
  assert.match(text, /^- Failed IDs: evt-2/m);
  assert.match(text, /^### Failed Timeline/m);
  assert.match(text, /^- 2026-04-07T10:01:00Z TRANSFER_STATUS_TRANSITIONED CREATED->FAILED reason=connector_timeout/m);
});

test("buildFailureMarkdownSummary handles no failed events", () => {
  const text = buildFailureMarkdownSummary({
    transferId: "trf-721",
    filterQuery: "",
    events: [{ event_id: "evt-1", event_type: "TRANSFER_CREATED", to_status: "CREATED", created_at: "2026-04-07T10:00:00Z" }],
  });

  assert.match(text, /^- Failed events: 0/m);
  assert.match(text, /^- Failure rate 0%/m);
  assert.match(text, /^- Filters: \(none\)/m);
  assert.match(text, /^- Failed IDs: -/m);
  assert.match(text, /^- None$/m);
});
