import test from "node:test";
import assert from "node:assert/strict";

import { buildTransferEventsDigest } from "./eventDigest.js";

test("buildTransferEventsDigest includes transfer header and numbered event lines", () => {
  const digest = buildTransferEventsDigest(
    [
      {
        created_at: "2026-04-06T10:00:00Z",
        event_type: "TRANSFER_CREATED",
        from_status: null,
        to_status: "CREATED",
        failure_reason: null,
      },
      {
        created_at: "2026-04-06T10:01:00Z",
        event_type: "TRANSFER_STATUS_TRANSITIONED",
        from_status: "CREATED",
        to_status: "FAILED",
        failure_reason: "connector_timeout",
      },
    ],
    "trf-77",
  );

  assert.match(digest, /^Transfer: trf-77/m);
  assert.match(digest, /^Events: 2/m);
  assert.match(digest, /^1\. 2026-04-06T10:00:00Z TRANSFER_CREATED CREATED/m);
  assert.match(digest, /^2\. 2026-04-06T10:01:00Z TRANSFER_STATUS_TRANSITIONED CREATED->FAILED reason=connector_timeout/m);
});
