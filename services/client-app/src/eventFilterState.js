const DEFAULT_EVENT_FILTERS = {
  eventType: "",
  toStatus: "",
  createdAtFrom: "",
  createdAtTo: "",
  searchText: "",
};

export function normalizeEventFilters(value) {
  const next = value && typeof value === "object" ? value : {};
  return {
    eventType: String(next.eventType || ""),
    toStatus: String(next.toStatus || ""),
    createdAtFrom: String(next.createdAtFrom || ""),
    createdAtTo: String(next.createdAtTo || ""),
    searchText: String(next.searchText || "").trim(),
  };
}

export function readStoredEventFilters(storageKey, storage = window.localStorage) {
  try {
    const raw = storage.getItem(storageKey);
    if (!raw) return { ...DEFAULT_EVENT_FILTERS };
    return normalizeEventFilters(JSON.parse(raw));
  } catch {
    return { ...DEFAULT_EVENT_FILTERS };
  }
}

export function writeStoredEventFilters(storageKey, filters, storage = window.localStorage) {
  storage.setItem(storageKey, JSON.stringify(normalizeEventFilters(filters)));
}
