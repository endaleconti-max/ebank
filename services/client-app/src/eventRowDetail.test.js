import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { buildEventRowDetailHtml, buildEventRowCopyText } from "./eventRowDetail.js";

describe("buildEventRowDetailHtml", () => {
  it("renders all available fields as a detail grid", () => {
    const event = {
      event_id: "evt-001",
      event_type: "TRANSFER_CREATED",
      from_status: "NONE",
      to_status: "CREATED",
      failure_reason: null,
      created_at: "2026-04-05T10:00:00Z",
    };
    const html = buildEventRowDetailHtml(event);
    assert.ok(html.includes("evt-001"), "should include event_id");
    assert.ok(html.includes("TRANSFER_CREATED"), "should include event_type");
    assert.ok(html.includes("NONE"), "should include from_status");
    assert.ok(html.includes("CREATED"), "should include to_status");
    assert.ok(html.includes("2026-04-05T10:00:00Z"), "should include timestamp");
    assert.ok(html.includes("class=\"event-row-detail\""), "should have detail container class");
  });

  it("renders failure reason when present", () => {
    const event = {
      event_id: "evt-002",
      event_type: "TRANSFER_FAILED",
      from_status: "SUBMITTED_TO_RAIL",
      to_status: "FAILED",
      failure_reason: "connector_unavailable",
      created_at: "2026-04-05T11:00:00Z",
    };
    const html = buildEventRowDetailHtml(event);
    assert.ok(html.includes("connector_unavailable"), "should include failure_reason");
    assert.ok(html.includes("erow-failure"), "should apply failure style class");
  });
});

describe("buildEventRowCopyText", () => {
  it("produces pipe-separated text with all populated fields", () => {
    const event = {
      event_id: "evt-abc",
      event_type: "TRANSFER_SETTLED",
      from_status: "SUBMITTED_TO_RAIL",
      to_status: "SETTLED",
      failure_reason: null,
      created_at: "2026-04-06T09:30:00Z",
    };
    const text = buildEventRowCopyText(event);
    assert.ok(text.includes("Event ID: evt-abc"), "should include event_id");
    assert.ok(text.includes("Type: TRANSFER_SETTLED"), "should include type");
    assert.ok(text.includes("From: SUBMITTED_TO_RAIL"), "should include from");
    assert.ok(text.includes("To: SETTLED"), "should include to");
    assert.ok(text.includes("Timestamp: 2026-04-06T09:30:00Z"), "should include timestamp");
    assert.ok(!text.includes("Reason:"), "should omit null failure_reason");
  });

  it("includes failure reason when present", () => {
    const event = {
      event_id: "evt-xyz",
      event_type: "TRANSFER_FAILED",
      from_status: "RESERVED",
      to_status: "FAILED",
      failure_reason: "ledger_error",
      created_at: "2026-04-06T10:00:00Z",
    };
    const text = buildEventRowCopyText(event);
    assert.ok(text.includes("Reason: ledger_error"), "should include failure reason");
  });
});
