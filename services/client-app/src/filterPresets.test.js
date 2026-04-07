import test from "node:test";
import assert from "node:assert/strict";

import { findFilterPreset, normalizePresetName, removeFilterPreset, upsertFilterPreset } from "./filterPresets.js";

test("normalizePresetName trims and collapses whitespace", () => {
  assert.equal(normalizePresetName("  High   value   failed  "), "High value failed");
});

test("upsertFilterPreset inserts and replaces case-insensitively", () => {
  const presets = upsertFilterPreset([], {
    name: "Failures",
    filters: { status: "FAILED" },
  });
  const updated = upsertFilterPreset(presets, {
    name: "failures",
    filters: { status: "FAILED", createdAtFrom: "2026-04-01" },
  });

  assert.equal(updated.length, 1);
  assert.deepEqual(updated[0].filters, { status: "FAILED", createdAtFrom: "2026-04-01" });
});

test("removeFilterPreset removes matching preset names", () => {
  const presets = [
    { name: "Failures", filters: { status: "FAILED" } },
    { name: "Settled", filters: { status: "SETTLED" } },
  ];

  const trimmed = removeFilterPreset(presets, " failures ");
  assert.equal(trimmed.length, 1);
  assert.equal(trimmed[0].name, "Settled");
});

test("findFilterPreset returns the matching preset or null", () => {
  const presets = [{ name: "Recent Failed", filters: { status: "FAILED" } }];
  assert.equal(findFilterPreset(presets, "recent failed")?.name, "Recent Failed");
  assert.equal(findFilterPreset(presets, "missing"), null);
});