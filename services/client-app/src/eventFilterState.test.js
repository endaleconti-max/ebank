import test from "node:test";
import assert from "node:assert/strict";

import { normalizeEventFilters, readStoredEventFilters, writeStoredEventFilters } from "./eventFilterState.js";

function createStorage(initial = {}) {
  const state = { ...initial };
  return {
    getItem(key) {
      return Object.prototype.hasOwnProperty.call(state, key) ? state[key] : null;
    },
    setItem(key, value) {
      state[key] = String(value);
    },
    dump() {
      return { ...state };
    },
  };
}

test("normalizeEventFilters enforces known keys and trims search text", () => {
  const normalized = normalizeEventFilters({
    eventType: "TRANSFER_CREATED",
    toStatus: "FAILED",
    createdAtFrom: "2026-04-01",
    createdAtTo: "2026-04-06",
    searchText: "  fail  ",
  });

  assert.deepEqual(normalized, {
    eventType: "TRANSFER_CREATED",
    toStatus: "FAILED",
    createdAtFrom: "2026-04-01",
    createdAtTo: "2026-04-06",
    searchText: "fail",
  });
});

test("readStoredEventFilters falls back to defaults for invalid JSON", () => {
  const storage = createStorage({ key: "{invalid" });
  assert.deepEqual(readStoredEventFilters("key", storage), {
    eventType: "",
    toStatus: "",
    createdAtFrom: "",
    createdAtTo: "",
    searchText: "",
  });
});

test("writeStoredEventFilters serializes normalized values", () => {
  const storage = createStorage();
  writeStoredEventFilters("key", { searchText: "  timeout  " }, storage);

  const payload = JSON.parse(storage.dump().key);
  assert.equal(payload.searchText, "timeout");
  assert.equal(payload.eventType, "");
});
