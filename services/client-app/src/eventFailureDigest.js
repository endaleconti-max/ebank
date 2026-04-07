import { isFailureEvent } from "./eventRowNavigation.js";

export function getFailureEvents(events) {
  return (events || []).filter((event) => isFailureEvent(event));
}

export function buildFailedEventsDigest(events, transferId) {
  const failedEvents = getFailureEvents(events);
  const lines = [];
  lines.push(`Transfer: ${transferId || "-"}`);
  lines.push(`Failed events: ${failedEvents.length}`);

  for (const [index, event] of failedEvents.entries()) {
    const transition = event.from_status && event.to_status
      ? `${event.from_status}->${event.to_status}`
      : event.to_status || "-";
    const reason = event.failure_reason ? ` reason=${event.failure_reason}` : "";
    lines.push(`${index + 1}. ${event.created_at || "-"} ${event.event_type || "-"} ${transition}${reason}`);
  }

  return lines.join("\n");
}
