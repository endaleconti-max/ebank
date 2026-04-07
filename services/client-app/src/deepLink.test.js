import test from "node:test";
import assert from "node:assert/strict";

import { getDeepLinkTransferId, buildDeepLinkUrl } from "./deepLink.js";

test("getDeepLinkTransferId returns the transfer param from a search string", () => {
  assert.equal(getDeepLinkTransferId("?transfer=tid-abc123"), "tid-abc123");
});

test("getDeepLinkTransferId returns null when param is absent", () => {
  assert.equal(getDeepLinkTransferId("?apiBase=http://localhost:8000"), null);
  assert.equal(getDeepLinkTransferId(""), null);
});

test("buildDeepLinkUrl sets the transfer param", () => {
  const result = buildDeepLinkUrl("http://localhost/index.html?apiBase=http://localhost:8000", "tid-xyz");
  const params = new URL(result).searchParams;
  assert.equal(params.get("transfer"), "tid-xyz");
  assert.equal(params.get("apiBase"), "http://localhost:8000");
});

test("buildDeepLinkUrl removes the transfer param when id is falsy", () => {
  const result = buildDeepLinkUrl("http://localhost/index.html?transfer=old-id&apiBase=http://localhost:8000", null);
  const params = new URL(result).searchParams;
  assert.equal(params.get("transfer"), null);
  assert.equal(params.get("apiBase"), "http://localhost:8000");
});
