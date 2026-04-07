import test from "node:test";
import assert from "node:assert/strict";

import { buildEventEmptyStateMessage, buildTransferEmptyStateMessage } from "./emptyStateGuidance.js";

test("buildTransferEmptyStateMessage adapts to active filters", () => {
  assert.match(buildTransferEmptyStateMessage(false), /No transfers yet/);
  assert.match(buildTransferEmptyStateMessage(true), /No transfers matched/);
});

test("buildEventEmptyStateMessage adapts to active filters", () => {
  assert.match(buildEventEmptyStateMessage(false), /No events yet/);
  assert.match(buildEventEmptyStateMessage(true), /No events matched/);
});