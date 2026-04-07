function dayKeyFromTimestamp(value) {
  const text = String(value || "");
  if (/^\d{4}-\d{2}-\d{2}/.test(text)) {
    return text.slice(0, 10);
  }
  const parsed = new Date(text);
  if (Number.isNaN(parsed.getTime())) {
    return "Unknown date";
  }
  return parsed.toISOString().slice(0, 10);
}

export function buildTimelineRows(events) {
  const rows = [];
  let previousDayKey = null;

  for (const event of events || []) {
    const dayKey = dayKeyFromTimestamp(event.created_at);
    if (dayKey !== previousDayKey) {
      rows.push({ kind: "day", dayKey });
      previousDayKey = dayKey;
    }
    rows.push({ kind: "event", event });
  }

  return rows;
}
