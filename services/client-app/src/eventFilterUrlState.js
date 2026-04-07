function normalizeFilterValue(value) {
  return String(value || "").trim();
}

export function buildUrlWithEventFilters(href, filters) {
  const url = new URL(href);

  const mappings = [
    ["evType", normalizeFilterValue(filters.eventType)],
    ["evStatus", normalizeFilterValue(filters.toStatus)],
    ["evFrom", normalizeFilterValue(filters.createdAtFrom)],
    ["evTo", normalizeFilterValue(filters.createdAtTo)],
    ["evQ", normalizeFilterValue(filters.searchText)],
  ];

  for (const [key, value] of mappings) {
    if (value) {
      url.searchParams.set(key, value);
    } else {
      url.searchParams.delete(key);
    }
  }

  return url.toString();
}

export function readEventFiltersFromSearch(search) {
  const params = new URLSearchParams(search);

  const filters = {
    eventType: normalizeFilterValue(params.get("evType")),
    toStatus: normalizeFilterValue(params.get("evStatus")),
    createdAtFrom: normalizeFilterValue(params.get("evFrom")),
    createdAtTo: normalizeFilterValue(params.get("evTo")),
    searchText: normalizeFilterValue(params.get("evQ")),
  };

  const hasUrlFilters = Boolean(
    filters.eventType ||
    filters.toStatus ||
    filters.createdAtFrom ||
    filters.createdAtTo ||
    filters.searchText
  );

  return { filters, hasUrlFilters };
}
