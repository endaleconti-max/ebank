import { getFailureEvents } from "./eventFailureDigest.js";
import { getFailedEventIds, formatFailureRateLabel } from "./eventFailureInsights.js";

export function buildFailureSnapshotReport({ transferId, events, filterQuery }) {
  const visibleEvents = events || [];
  const failedEvents = getFailureEvents(visibleEvents);
  const failedEventIds = getFailedEventIds(visibleEvents);

  const lines = [];
  lines.push("Failure Snapshot Report");
  lines.push(`Transfer: ${transferId || "-"}`);
  lines.push(`Visible events: ${visibleEvents.length}`);
  lines.push(`Failed events: ${failedEvents.length}`);
  lines.push(formatFailureRateLabel(failedEvents.length, visibleEvents.length));
  lines.push(`Filters: ${filterQuery ? `?${filterQuery}` : "(none)"}`);
  lines.push("");
  lines.push("Failed Event IDs");
  lines.push(failedEventIds.length ? failedEventIds.join(", ") : "-");
  lines.push("");
  lines.push("Failed Event Timeline");

  if (!failedEvents.length) {
    lines.push("-");
  } else {
    for (const [index, event] of failedEvents.entries()) {
      const transition = event.from_status && event.to_status
        ? `${event.from_status}->${event.to_status}`
        : event.to_status || "-";
      const reason = event.failure_reason ? ` reason=${event.failure_reason}` : "";
      lines.push(`${index + 1}. ${event.created_at || "-"} ${event.event_type || "-"} ${transition}${reason}`);
    }
  }

  return lines.join("\n");
}
