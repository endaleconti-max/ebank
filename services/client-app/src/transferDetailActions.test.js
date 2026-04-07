import test from "node:test";
import assert from "node:assert/strict";

import { buildTransferDetailActionPayload } from "./transferDetailActions.js";

test("buildTransferDetailActionPayload exposes copyable transfer fields", () => {
  const payload = buildTransferDetailActionPayload(
    {
      transfer_id: "tid-123",
      sender_user_id: "u-1",
      recipient_phone_e164: "+15550001111",
      status: "SETTLED",
    },
    "http://localhost:5173/?apiBase=http://localhost:8000",
  );

  assert.equal(payload.transferIdText, "tid-123");
  assert.equal(payload.recipientText, "+15550001111");
  assert.match(payload.shareUrl, /transfer=tid-123/);
  assert.match(payload.shareText, /SETTLED/);
});