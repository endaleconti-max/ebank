import { isFailureEvent } from "./eventRowNavigation.js";

export function getFailedEventIds(events) {
  return (events || [])
    .filter((event) => isFailureEvent(event))
    .map((event) => String(event.event_id || ""))
    .filter(Boolean);
}

export function formatFailureRateLabel(failedCount, totalCount) {
  if (!totalCount) return "Failure rate 0%";
  const rate = Math.round((failedCount / totalCount) * 100);
  return `Failure rate ${rate}%`;
}

export function buildFailedEventIdsText(events, transferId) {
  const ids = getFailedEventIds(events);
  return [
    `Transfer: ${transferId || "-"}`,
    `Failed event IDs: ${ids.length}`,
    ids.join(", "),
  ].join("\n");
}
