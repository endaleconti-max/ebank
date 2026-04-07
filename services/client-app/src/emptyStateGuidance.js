export function buildTransferEmptyStateMessage(hasActiveFilters) {
  if (hasActiveFilters) {
    return "No transfers matched these filters. Try clearing the search or use a sample shortcut like Failed review.";
  }
  return "No transfers yet. Create one above or try a sample shortcut to explore common operator views.";
}

export function buildEventEmptyStateMessage(hasActiveFilters) {
  if (hasActiveFilters) {
    return "No events matched the current filters. Try clearing the search or use a sample event shortcut.";
  }
  return "No events yet. Select a transfer and use the sample event shortcuts to inspect common timelines.";
}