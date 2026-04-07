export function buildTransferEventsDigest(events, transferId) {
  const lines = [];
  lines.push(`Transfer: ${transferId || "-"}`);
  lines.push(`Events: ${(events || []).length}`);

  for (const [index, event] of (events || []).entries()) {
    const transition = event.from_status && event.to_status
      ? `${event.from_status}->${event.to_status}`
      : event.to_status || "-";
    const reason = event.failure_reason ? ` reason=${event.failure_reason}` : "";
    lines.push(`${index + 1}. ${event.created_at || "-"} ${event.event_type || "-"} ${transition}${reason}`);
  }

  return lines.join("\n");
}
