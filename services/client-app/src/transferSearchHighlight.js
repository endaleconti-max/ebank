function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function highlightMatchedText(text, searchText) {
  const rawText = String(text || "");
  const normalizedSearch = String(searchText || "").trim();
  if (!normalizedSearch) {
    return escapeHtml(rawText);
  }

  const pattern = new RegExp(`(${escapeRegExp(normalizedSearch)})`, "ig");
  return escapeHtml(rawText).replace(pattern, '<mark class="inline-highlight">$1</mark>');
}

export function buildTransferSearchContext(transfer, searchText) {
  const normalizedSearch = String(searchText || "").trim().toLowerCase();
  if (!normalizedSearch) {
    return [];
  }

  const contexts = [];
  if (String(transfer.note || "").toLowerCase().includes(normalizedSearch)) {
    contexts.push({
      label: "Note",
      html: highlightMatchedText(transfer.note, searchText),
    });
  }
  if (String(transfer.failure_reason || "").toLowerCase().includes(normalizedSearch)) {
    contexts.push({
      label: "Failure",
      html: highlightMatchedText(transfer.failure_reason, searchText),
    });
  }
  return contexts;
}