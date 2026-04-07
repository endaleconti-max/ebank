export function buildActiveEventFilterChips(filters) {
  const chips = [];

  if (filters.eventType) {
    chips.push({ key: "eventType", label: "Type", value: filters.eventType });
  }
  if (filters.toStatus) {
    chips.push({ key: "toStatus", label: "Status", value: filters.toStatus });
  }
  if (filters.createdAtFrom) {
    chips.push({ key: "createdAtFrom", label: "From", value: filters.createdAtFrom });
  }
  if (filters.createdAtTo) {
    chips.push({ key: "createdAtTo", label: "To", value: filters.createdAtTo });
  }
  if (filters.searchText) {
    chips.push({ key: "searchText", label: "Search", value: filters.searchText });
  }

  return chips;
}

export function buildEventFilterQueryString(filters) {
  const query = new URLSearchParams();
  if (filters.eventType) query.set("event_type", filters.eventType);
  if (filters.toStatus) query.set("to_status", filters.toStatus);
  if (filters.createdAtFrom) query.set("created_at_from", filters.createdAtFrom);
  if (filters.createdAtTo) query.set("created_at_to", filters.createdAtTo);
  if (filters.searchText) query.set("search_text", filters.searchText);
  return query.toString();
}
