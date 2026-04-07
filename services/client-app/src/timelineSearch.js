export function filterEventsBySearch(events, searchText) {
  const normalizedSearch = String(searchText || "").trim().toLowerCase();
  if (!normalizedSearch) {
    return events;
  }

  return events.filter((event) => {
    const haystacks = [
      event.event_type,
      event.failure_reason,
      event.from_status,
      event.to_status,
    ];
    return haystacks.some((value) => String(value || "").toLowerCase().includes(normalizedSearch));
  });
}