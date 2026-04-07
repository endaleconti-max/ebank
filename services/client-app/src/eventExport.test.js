import test from "node:test";
import assert from "node:assert/strict";

import { buildTransferEventsCsv, buildTransferEventsJson } from "./eventExport.js";

test("buildTransferEventsCsv emits header and rows", () => {
  const csv = buildTransferEventsCsv([
    {
      transfer_id: "trf-1",
      event_type: "TRANSFER_CREATED",
      from_status: null,
      to_status: "CREATED",
      failure_reason: null,
      created_at: "2026-04-06T10:00:00Z",
    },
  ]);

  assert.match(csv, /^transfer_id,event_type,from_status,to_status,failure_reason,created_at/);
  assert.match(csv, /trf-1,TRANSFER_CREATED,,CREATED,,2026-04-06T10:00:00Z/);
});

test("buildTransferEventsCsv escapes commas and quotes", () => {
  const csv = buildTransferEventsCsv([
    {
      transfer_id: "trf-2",
      event_type: "TRANSFER_STATUS_TRANSITIONED",
      from_status: "SUBMITTED_TO_RAIL",
      to_status: "FAILED",
      failure_reason: 'gateway said "timeout, retry"',
      created_at: "2026-04-06T11:00:00Z",
    },
  ]);

  assert.match(csv, /"gateway said ""timeout, retry"""/);
});

test("buildTransferEventsJson pretty prints event arrays", () => {
  const json = buildTransferEventsJson(
    [{ event_type: "TRANSFER_CREATED" }],
    {
      transferId: "trf-json-1",
      generatedAt: "2026-04-06T12:00:00Z",
      filters: { toStatus: "FAILED" },
    },
  );
  const payload = JSON.parse(json);
  assert.equal(payload.transfer_id, "trf-json-1");
  assert.equal(payload.generated_at, "2026-04-06T12:00:00Z");
  assert.equal(payload.event_count, 1);
  assert.deepEqual(payload.applied_filters, { toStatus: "FAILED" });
  assert.equal(payload.events[0].event_type, "TRANSFER_CREATED");
});
