import test from "node:test";
import assert from "node:assert/strict";

import { isFailedOnlyEnabled, toggleFailedOnlyStatus } from "./eventFilterModes.js";

test("isFailedOnlyEnabled returns true only for FAILED status", () => {
  assert.equal(isFailedOnlyEnabled({ toStatus: "FAILED" }), true);
  assert.equal(isFailedOnlyEnabled({ toStatus: "SETTLED" }), false);
  assert.equal(isFailedOnlyEnabled({}), false);
});

test("toggleFailedOnlyStatus toggles toStatus between FAILED and empty", () => {
  assert.deepEqual(toggleFailedOnlyStatus({ eventType: "TRANSFER_CREATED", toStatus: "" }), {
    eventType: "TRANSFER_CREATED",
    toStatus: "FAILED",
  });

  assert.deepEqual(toggleFailedOnlyStatus({ eventType: "TRANSFER_CREATED", toStatus: "FAILED" }), {
    eventType: "TRANSFER_CREATED",
    toStatus: "",
  });
});
