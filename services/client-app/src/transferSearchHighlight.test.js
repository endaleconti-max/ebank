import test from "node:test";
import assert from "node:assert/strict";

import { buildTransferSearchContext, highlightMatchedText } from "./transferSearchHighlight.js";

test("highlightMatchedText wraps case-insensitive matches in mark tags", () => {
  const html = highlightMatchedText("Dinner refund for Sam", "refund");
  assert.match(html, /Dinner <mark class="inline-highlight">refund<\/mark> for Sam/i);
});

test("buildTransferSearchContext includes matching note and failure snippets", () => {
  const contexts = buildTransferSearchContext(
    {
      note: "Dinner refund for Sam",
      failure_reason: "connector timeout",
    },
    "refund",
  );

  assert.equal(contexts.length, 1);
  assert.equal(contexts[0].label, "Note");
});

test("buildTransferSearchContext returns both note and failure matches", () => {
  const contexts = buildTransferSearchContext(
    {
      note: "timeout follow-up",
      failure_reason: "connector timeout",
    },
    "timeout",
  );

  assert.equal(contexts.length, 2);
});