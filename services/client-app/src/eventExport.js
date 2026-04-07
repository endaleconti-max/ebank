function escapeCsvValue(value) {
  const stringValue = value == null ? "" : String(value);
  if (!/[",\n]/.test(stringValue)) {
    return stringValue;
  }
  return `"${stringValue.replace(/"/g, '""')}"`;
}

export function buildTransferEventsCsv(events) {
  const header = [
    "transfer_id",
    "event_type",
    "from_status",
    "to_status",
    "failure_reason",
    "created_at",
  ];

  const rows = (events || []).map((event) => [
    event.transfer_id,
    event.event_type,
    event.from_status,
    event.to_status,
    event.failure_reason,
    event.created_at,
  ]);

  return [header, ...rows]
    .map((row) => row.map(escapeCsvValue).join(","))
    .join("\n");
}

export function buildTransferEventsJson(events, metadata = {}) {
  const exportEvents = events || [];
  const payload = {
    transfer_id: metadata.transferId || null,
    generated_at: metadata.generatedAt || new Date().toISOString(),
    applied_filters: metadata.filters || {},
    event_count: exportEvents.length,
    events: exportEvents,
  };
  return JSON.stringify(payload, null, 2);
}
