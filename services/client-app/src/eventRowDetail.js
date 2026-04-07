/**
 * eventRowDetail.js
 * Helpers for per-event inline detail expansion and single-event copy text.
 */

/**
 * Build the HTML string for the collapsible detail strip below an event row.
 * @param {object} event - Transfer event object.
 * @returns {string} HTML fragment for the detail panel.
 */
export function buildEventRowDetailHtml(event) {
  const rows = [];

  if (event.event_id) {
    rows.push(`<span class="erow-label">Event ID</span><span class="erow-value">${event.event_id}</span>`);
  }
  if (event.event_type) {
    rows.push(`<span class="erow-label">Type</span><span class="erow-value">${event.event_type}</span>`);
  }
  if (event.from_status) {
    rows.push(`<span class="erow-label">From</span><span class="erow-value">${event.from_status}</span>`);
  }
  if (event.to_status) {
    rows.push(`<span class="erow-label">To</span><span class="erow-value">${event.to_status}</span>`);
  }
  if (event.failure_reason) {
    rows.push(`<span class="erow-label">Reason</span><span class="erow-value erow-failure">${event.failure_reason}</span>`);
  }
  if (event.created_at) {
    rows.push(`<span class="erow-label">Timestamp</span><span class="erow-value">${event.created_at}</span>`);
  }

  if (!rows.length) {
    return '<div class="event-row-detail"><em>No detail available.</em></div>';
  }

  return `<div class="event-row-detail"><dl class="erow-grid">${rows.map(r => `<div class="erow-pair">${r}</div>`).join("")}</dl></div>`;
}

/**
 * Build a plain-text copy string for a single event row.
 * @param {object} event - Transfer event object.
 * @returns {string} Human-readable tab-separated event summary.
 */
export function buildEventRowCopyText(event) {
  const parts = [];

  if (event.event_id)       parts.push(`Event ID: ${event.event_id}`);
  if (event.event_type)     parts.push(`Type: ${event.event_type}`);
  if (event.from_status)    parts.push(`From: ${event.from_status}`);
  if (event.to_status)      parts.push(`To: ${event.to_status}`);
  if (event.failure_reason) parts.push(`Reason: ${event.failure_reason}`);
  if (event.created_at)     parts.push(`Timestamp: ${event.created_at}`);

  return parts.join(" | ");
}
