import test from "node:test";
import assert from "node:assert/strict";

import { getShortcutAction } from "./keyboardShortcuts.js";

test("getShortcutAction maps supported alt+shift shortcuts", () => {
  assert.equal(getShortcutAction({ key: "I", altKey: true, shiftKey: true, metaKey: false, ctrlKey: false, target: { tagName: "DIV" } }), "copy-transfer-id");
  assert.equal(getShortcutAction({ key: "L", altKey: true, shiftKey: true, metaKey: false, ctrlKey: false, target: { tagName: "DIV" } }), "copy-transfer-link");
  assert.equal(getShortcutAction({ key: "R", altKey: true, shiftKey: true, metaKey: false, ctrlKey: false, target: { tagName: "DIV" } }), "reload-transfer-details");
  assert.equal(getShortcutAction({ key: "P", altKey: true, shiftKey: true, metaKey: false, ctrlKey: false, target: { tagName: "DIV" } }), "apply-selected-preset");
  assert.equal(getShortcutAction({ key: "F", altKey: true, shiftKey: true, metaKey: false, ctrlKey: false, target: { tagName: "DIV" } }), "copy-event-filters");
  assert.equal(getShortcutAction({ key: "D", altKey: true, shiftKey: true, metaKey: false, ctrlKey: false, target: { tagName: "DIV" } }), "copy-event-digest");
  assert.equal(getShortcutAction({ key: "Y", altKey: true, shiftKey: true, metaKey: false, ctrlKey: false, target: { tagName: "DIV" } }), "copy-failed-event-digest");
  assert.equal(getShortcutAction({ key: "N", altKey: true, shiftKey: true, metaKey: false, ctrlKey: false, target: { tagName: "DIV" } }), "sort-events-newest");
  assert.equal(getShortcutAction({ key: "O", altKey: true, shiftKey: true, metaKey: false, ctrlKey: false, target: { tagName: "DIV" } }), "sort-events-oldest");
  assert.equal(getShortcutAction({ key: "C", altKey: true, shiftKey: true, metaKey: false, ctrlKey: false, target: { tagName: "DIV" } }), "clear-event-filters");
  assert.equal(getShortcutAction({ key: "X", altKey: true, shiftKey: true, metaKey: false, ctrlKey: false, target: { tagName: "DIV" } }), "toggle-event-failed-only");
  assert.equal(getShortcutAction({ key: "J", altKey: true, shiftKey: true, metaKey: false, ctrlKey: false, target: { tagName: "DIV" } }), "event-expand-previous");
  assert.equal(getShortcutAction({ key: "K", altKey: true, shiftKey: true, metaKey: false, ctrlKey: false, target: { tagName: "DIV" } }), "event-expand-next");
  assert.equal(getShortcutAction({ key: "Q", altKey: true, shiftKey: true, metaKey: false, ctrlKey: false, target: { tagName: "DIV" } }), "event-failure-previous");
  assert.equal(getShortcutAction({ key: "W", altKey: true, shiftKey: true, metaKey: false, ctrlKey: false, target: { tagName: "DIV" } }), "event-failure-next");
});

test("getShortcutAction ignores editable targets and unsupported modifier combos", () => {
  assert.equal(getShortcutAction({ key: "I", altKey: true, shiftKey: true, metaKey: false, ctrlKey: false, target: { tagName: "INPUT" } }), null);
  assert.equal(getShortcutAction({ key: "I", altKey: false, shiftKey: true, metaKey: false, ctrlKey: false, target: { tagName: "DIV" } }), null);
});