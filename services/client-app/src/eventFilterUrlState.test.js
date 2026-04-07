import test from "node:test";
import assert from "node:assert/strict";

import { buildUrlWithEventFilters, readEventFiltersFromSearch } from "./eventFilterUrlState.js";

test("buildUrlWithEventFilters adds event filter params and keeps existing params", () => {
  const nextUrl = buildUrlWithEventFilters(
    "http://localhost:5173/?apiBase=http://localhost:8000&transfer=trf-1",
    {
      eventType: "TRANSFER_CREATED",
      toStatus: "FAILED",
      createdAtFrom: "2026-04-01",
      createdAtTo: "2026-04-06",
      searchText: "timeout",
    },
  );

  const params = new URL(nextUrl).searchParams;
  assert.equal(params.get("apiBase"), "http://localhost:8000");
  assert.equal(params.get("transfer"), "trf-1");
  assert.equal(params.get("evType"), "TRANSFER_CREATED");
  assert.equal(params.get("evStatus"), "FAILED");
  assert.equal(params.get("evFrom"), "2026-04-01");
  assert.equal(params.get("evTo"), "2026-04-06");
  assert.equal(params.get("evQ"), "timeout");
});

test("buildUrlWithEventFilters removes cleared event filter params", () => {
  const nextUrl = buildUrlWithEventFilters(
    "http://localhost:5173/?evType=TRANSFER_CREATED&evStatus=FAILED&evQ=timeout",
    {
      eventType: "",
      toStatus: "",
      createdAtFrom: "",
      createdAtTo: "",
      searchText: "",
    },
  );

  const params = new URL(nextUrl).searchParams;
  assert.equal(params.get("evType"), null);
  assert.equal(params.get("evStatus"), null);
  assert.equal(params.get("evQ"), null);
});

test("readEventFiltersFromSearch parses filters and reports presence", () => {
  const result = readEventFiltersFromSearch("?evType=TRANSFER_CREATED&evStatus=FAILED&evQ=timeout");

  assert.equal(result.hasUrlFilters, true);
  assert.equal(result.filters.eventType, "TRANSFER_CREATED");
  assert.equal(result.filters.toStatus, "FAILED");
  assert.equal(result.filters.searchText, "timeout");
});

test("readEventFiltersFromSearch reports no filters when absent", () => {
  const result = readEventFiltersFromSearch("?apiBase=http://localhost:8000");

  assert.equal(result.hasUrlFilters, false);
  assert.deepEqual(result.filters, {
    eventType: "",
    toStatus: "",
    createdAtFrom: "",
    createdAtTo: "",
    searchText: "",
  });
});
