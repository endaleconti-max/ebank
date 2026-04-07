function isEditableTarget(target) {
  if (!target) return false;
  const tagName = target.tagName?.toLowerCase();
  return target.isContentEditable || tagName === "input" || tagName === "textarea" || tagName === "select";
}

export function getShortcutAction(event) {
  if (isEditableTarget(event.target)) {
    return null;
  }
  if (!event.altKey || !event.shiftKey || event.metaKey || event.ctrlKey) {
    return null;
  }

  const key = String(event.key || "").toLowerCase();
  if (key === "i") return "copy-transfer-id";
  if (key === "l") return "copy-transfer-link";
  if (key === "r") return "reload-transfer-details";
  if (key === "p") return "apply-selected-preset";
  if (key === "f") return "copy-event-filters";
  if (key === "d") return "copy-event-digest";
  if (key === "y") return "copy-failed-event-digest";
  if (key === "u") return "copy-failed-event-ids";
  if (key === "n") return "sort-events-newest";
  if (key === "o") return "sort-events-oldest";
  if (key === "c") return "clear-event-filters";
  if (key === "x") return "toggle-event-failed-only";
  if (key === "j") return "event-expand-previous";
  if (key === "k") return "event-expand-next";
  if (key === "q") return "event-failure-previous";
  if (key === "w") return "event-failure-next";
  return null;
}