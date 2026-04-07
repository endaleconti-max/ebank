import test from "node:test";
import assert from "node:assert/strict";

import { buildTimelineRows } from "./eventTimelineLayout.js";

test("buildTimelineRows inserts day separators when date changes", () => {
  const rows = buildTimelineRows([
    { event_id: "e-1", created_at: "2026-04-06T10:00:00Z" },
    { event_id: "e-2", created_at: "2026-04-06T12:00:00Z" },
    { event_id: "e-3", created_at: "2026-04-07T08:00:00Z" },
  ]);

  assert.deepEqual(rows.map((row) => row.kind), ["day", "event", "event", "day", "event"]);
  assert.equal(rows[0].dayKey, "2026-04-06");
  assert.equal(rows[3].dayKey, "2026-04-07");
});

test("buildTimelineRows falls back to unknown date for invalid timestamps", () => {
  const rows = buildTimelineRows([{ event_id: "e-1", created_at: "not-a-date" }]);
  assert.equal(rows[0].kind, "day");
  assert.equal(rows[0].dayKey, "Unknown date");
});
