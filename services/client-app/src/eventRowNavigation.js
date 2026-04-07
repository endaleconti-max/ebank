/**
 * Returns the adjacent event ID to expand in the current visible ordering.
 * Wraps around at list boundaries.
 *
 * @param {string[]} eventIds
 * @param {string|null} currentEventId
 * @param {"next"|"previous"} direction
 * @returns {string|null}
 */
export function getAdjacentEventId(eventIds, currentEventId, direction) {
  const ids = normalizeEventIds(eventIds);
  if (!ids.length) return null;

  const goNext = direction !== "previous";
  const index = currentEventId ? ids.indexOf(String(currentEventId)) : -1;

  if (index === -1) {
    return goNext ? ids[0] : ids[ids.length - 1];
  }

  if (goNext) {
    return ids[(index + 1) % ids.length];
  }

  return ids[(index - 1 + ids.length) % ids.length];
}

/**
 * Checks whether an event is failure-related for investigation stepping.
 * @param {object} event
 * @returns {boolean}
 */
export function isFailureEvent(event) {
  const toStatus = String(event?.to_status || "").toUpperCase();
  const eventType = String(event?.event_type || "").toUpperCase();
  return toStatus === "FAILED" || eventType.includes("FAILED") || Boolean(event?.failure_reason);
}

/**
 * Returns adjacent failure event ID based on currently visible ordered events.
 * @param {Array<object>} events
 * @param {string|null} currentEventId
 * @param {"next"|"previous"} direction
 * @returns {string|null}
 */
export function getAdjacentFailureEventId(events, currentEventId, direction) {
  const failureIds = Array.isArray(events)
    ? events.filter((event) => isFailureEvent(event)).map((event) => event?.event_id)
    : [];
  return getAdjacentEventId(failureIds, currentEventId, direction);
}

function normalizeEventIds(eventIds) {
  return Array.isArray(eventIds) ? eventIds.filter(Boolean).map((id) => String(id)) : [];
}
