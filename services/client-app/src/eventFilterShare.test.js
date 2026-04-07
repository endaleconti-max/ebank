import test from "node:test";
import assert from "node:assert/strict";

import { buildActiveEventFilterChips, buildEventFilterQueryString } from "./eventFilterShare.js";

test("buildActiveEventFilterChips returns only active filters in a stable order", () => {
  const chips = buildActiveEventFilterChips({
    eventType: "TRANSFER_CREATED",
    toStatus: "FAILED",
    createdAtFrom: "2026-04-01",
    createdAtTo: "2026-04-06",
    searchText: "timeout",
  });

  assert.deepEqual(chips.map((chip) => chip.key), [
    "eventType",
    "toStatus",
    "createdAtFrom",
    "createdAtTo",
    "searchText",
  ]);
  assert.equal(chips[0].label, "Type");
});

test("buildEventFilterQueryString maps client filters to query params", () => {
  const query = buildEventFilterQueryString({
    eventType: "TRANSFER_STATUS_TRANSITIONED",
    toStatus: "SETTLED",
    createdAtFrom: "2026-04-01",
    createdAtTo: "2026-04-06",
    searchText: "settled",
  });

  const parsed = new URLSearchParams(query);
  assert.equal(parsed.get("event_type"), "TRANSFER_STATUS_TRANSITIONED");
  assert.equal(parsed.get("to_status"), "SETTLED");
  assert.equal(parsed.get("created_at_from"), "2026-04-01");
  assert.equal(parsed.get("created_at_to"), "2026-04-06");
  assert.equal(parsed.get("search_text"), "settled");
});
