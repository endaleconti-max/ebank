export function appendUniqueEvents(existingEvents, incomingEvents) {
  const seen = new Set(existingEvents.map((event) => event.event_id));
  const merged = [...existingEvents];

  for (const event of incomingEvents) {
    if (!seen.has(event.event_id)) {
      seen.add(event.event_id);
      merged.push(event);
    }
  }

  return merged;
}

export function didEventFiltersChange(previousFilters, nextFilters) {
  return (
    previousFilters.eventType !== nextFilters.eventType ||
    previousFilters.toStatus !== nextFilters.toStatus ||
    (previousFilters.createdAtFrom ?? "") !== (nextFilters.createdAtFrom ?? "") ||
    (previousFilters.createdAtTo ?? "") !== (nextFilters.createdAtTo ?? "") ||
    (previousFilters.searchText ?? "") !== (nextFilters.searchText ?? "")
  );
}
