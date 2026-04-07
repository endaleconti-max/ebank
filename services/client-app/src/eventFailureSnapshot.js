import { getFailedEventIds } from "./eventFailureInsights.js";
import { getFailureEvents } from "./eventFailureDigest.js";
import { formatFailureRateLabel } from "./eventFailureInsights.js";

export function buildFailureSnapshotText({ transferId, events, filterQuery }) {
  const visibleEvents = events || [];
  const failedEvents = getFailureEvents(visibleEvents);
  const failedIds = getFailedEventIds(visibleEvents);

  const lines = [];
  lines.push(`Transfer: ${transferId || "-"}`);
  lines.push(`Visible events: ${visibleEvents.length}`);
  lines.push(`Failed events: ${failedEvents.length}`);
  lines.push(formatFailureRateLabel(failedEvents.length, visibleEvents.length));
  lines.push(`Failed IDs: ${failedIds.length ? failedIds.join(", ") : "-"}`);
  lines.push(`Filters: ${filterQuery ? `?${filterQuery}` : "(none)"}`);
  return lines.join("\n");
}
