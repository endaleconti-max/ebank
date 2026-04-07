import test from "node:test";
import assert from "node:assert/strict";

import { buildRollingDateRange } from "./eventDateShortcuts.js";

test("buildRollingDateRange returns same-day range for 24h window anchored at noon", () => {
  const range = buildRollingDateRange(
    { hours: 24 },
    new Date("2026-04-06T12:00:00Z"),
  );

  assert.deepEqual(range, { fromDate: "2026-04-05", toDate: "2026-04-06" });
});

test("buildRollingDateRange returns inclusive multi-day range", () => {
  const range = buildRollingDateRange(
    { days: 7 },
    new Date("2026-04-06T08:00:00Z"),
  );

  assert.deepEqual(range, { fromDate: "2026-03-31", toDate: "2026-04-06" });
});
