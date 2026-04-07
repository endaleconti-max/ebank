import { getFailureEvents } from "./eventFailureDigest.js";
import { getFailedEventIds, formatFailureRateLabel } from "./eventFailureInsights.js";

export function buildFailureMarkdownSummary({ transferId, events, filterQuery }) {
  const visibleEvents = events || [];
  const failedEvents = getFailureEvents(visibleEvents);
  const failedIds = getFailedEventIds(visibleEvents);

  const lines = [];
  lines.push("## Failure Summary");
  lines.push("");
  lines.push(`- Transfer: ${transferId || "-"}`);
  lines.push(`- Visible events: ${visibleEvents.length}`);
  lines.push(`- Failed events: ${failedEvents.length}`);
  lines.push(`- ${formatFailureRateLabel(failedEvents.length, visibleEvents.length)}`);
  lines.push(`- Filters: ${filterQuery ? `?${filterQuery}` : "(none)"}`);
  lines.push(`- Failed IDs: ${failedIds.length ? failedIds.join(", ") : "-"}`);
  lines.push("");
  lines.push("### Failed Timeline");

  if (!failedEvents.length) {
    lines.push("- None");
  } else {
    for (const event of failedEvents) {
      const transition = event.from_status && event.to_status
        ? `${event.from_status}->${event.to_status}`
        : event.to_status || "-";
      const reason = event.failure_reason ? ` reason=${event.failure_reason}` : "";
      lines.push(`- ${event.created_at || "-"} ${event.event_type || "-"} ${transition}${reason}`);
    }
  }

  return lines.join("\n");
}
