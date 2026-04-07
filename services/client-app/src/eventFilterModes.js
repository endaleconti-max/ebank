export function isFailedOnlyEnabled(filters) {
  return String(filters?.toStatus || "") === "FAILED";
}

export function toggleFailedOnlyStatus(filters) {
  const currentlyEnabled = isFailedOnlyEnabled(filters);
  return {
    ...filters,
    toStatus: currentlyEnabled ? "" : "FAILED",
  };
}
