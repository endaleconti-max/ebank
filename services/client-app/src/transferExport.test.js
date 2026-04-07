import test from "node:test";
import assert from "node:assert/strict";

import { buildTransfersCsv } from "./transferExport.js";

test("buildTransfersCsv emits a header row and transfer data", () => {
  const csv = buildTransfersCsv([
    {
      transfer_id: "t-1",
      status: "CREATED",
      sender_user_id: "u-1",
      recipient_phone_e164: "+15550001111",
      currency: "USD",
      amount_minor: 1234,
      note: "Dinner split",
      failure_reason: null,
      connector_external_ref: null,
      created_at: "2026-04-06T10:00:00Z",
      updated_at: "2026-04-06T10:00:00Z",
    },
  ]);

  assert.match(csv, /^transfer_id,status,sender_user_id,/);
  assert.match(csv, /t-1,CREATED,u-1/);
});

test("buildTransfersCsv escapes commas, quotes, and null values", () => {
  const csv = buildTransfersCsv([
    {
      transfer_id: "t-2",
      status: "FAILED",
      sender_user_id: "u-2",
      recipient_phone_e164: "+15550002222",
      currency: "USD",
      amount_minor: 500,
      note: 'said "refund, please"',
      failure_reason: "bad,address",
      connector_external_ref: null,
      created_at: "2026-04-06T10:00:00Z",
      updated_at: "2026-04-06T11:00:00Z",
    },
  ]);

  assert.match(csv, /"said ""refund, please"""/);
  assert.match(csv, /"bad,address"/);
  assert.match(csv, /,,2026-04-06T10:00:00Z/);
});