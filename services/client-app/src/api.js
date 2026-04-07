const DEFAULT_API_BASE = "http://localhost:8000";

export function getApiBase() {
  const url = new URL(window.location.href);
  return (url.searchParams.get("apiBase") || DEFAULT_API_BASE).replace(/\/$/, "");
}

function requestId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.floor(Math.random() * 10_000)}`;
}

function normalizeErrorMessage(payload, fallback) {
  if (!payload) return fallback;
  if (typeof payload.detail === "string") return payload.detail;
  if (Array.isArray(payload.detail) && payload.detail.length > 0) {
    const first = payload.detail[0];
    if (typeof first?.msg === "string") return first.msg;
  }
  return fallback;
}

async function parseJsonSafe(response) {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

async function request(path, options = {}) {
  const base = getApiBase();
  const headers = {
    "Content-Type": "application/json",
    "X-Request-Id": requestId(),
    ...(options.headers || {}),
  };

  const response = await fetch(`${base}${path}`, {
    ...options,
    headers,
  });

  const payload = await parseJsonSafe(response);
  if (!response.ok) {
    const fallback = `Request failed (${response.status})`;
    throw new Error(normalizeErrorMessage(payload, fallback));
  }
  return payload;
}

export async function checkGateway() {
  const base = getApiBase();
  const response = await fetch(`${base}/v1/healthz`);
  return response.status === 204;
}

export async function createTransfer(input) {
  return request("/v1/transfers", {
    method: "POST",
    headers: {
      "Idempotency-Key": requestId(),
    },
    body: JSON.stringify(input),
  });
}

export async function listTransfers({ senderUserId = "", status = "", limit = 20, cursor = "", createdAtFrom = "", createdAtTo = "", q = "" } = {}) {
  const query = new URLSearchParams();
  query.set("limit", String(limit));
  if (senderUserId) query.set("sender_user_id", senderUserId);
  if (status) query.set("status", status);
  if (cursor) query.set("cursor", cursor);
  if (createdAtFrom) query.set("created_at_from", createdAtFrom);
  if (createdAtTo) query.set("created_at_to", createdAtTo);
  if (q) query.set("q", q);

  return request(`/v1/transfers?${query.toString()}`);
}

export async function getTransfer(transferId) {
  return request(`/v1/transfers/${encodeURIComponent(transferId)}`);
}

export async function updateTransferNote(transferId, note) {
  return request(`/v1/transfers/${encodeURIComponent(transferId)}/note`, {
    method: "PATCH",
    body: JSON.stringify({ note: note ? note.trim() : null }),
  });
}

export async function getTransferEvents(
  transferId,
  { eventType = "", toStatus = "", limit = 25, cursor = "", createdAtFrom = "", createdAtTo = "" } = {},
) {
  const query = new URLSearchParams();
  if (eventType) query.set("event_type", eventType);
  if (toStatus) query.set("to_status", toStatus);
  if (limit) query.set("limit", String(limit));
  if (cursor) query.set("cursor", cursor);
  if (createdAtFrom) query.set("created_at_from", createdAtFrom);
  if (createdAtTo) query.set("created_at_to", createdAtTo);

  const base = getApiBase();
  const response = await fetch(
    `${base}/v1/transfers/${encodeURIComponent(transferId)}/events?${query.toString()}`,
    {
      headers: {
        "Content-Type": "application/json",
        "X-Request-Id": requestId(),
      },
    },
  );

  const payload = await parseJsonSafe(response);
  if (!response.ok) {
    const fallback = `Request failed (${response.status})`;
    throw new Error(normalizeErrorMessage(payload, fallback));
  }

  return {
    events: Array.isArray(payload) ? payload : [],
    nextCursor: response.headers.get("X-Next-Cursor") || null,
  };
}

export async function getTransferEventSummary(transferId) {
  return request(`/v1/transfers/${encodeURIComponent(transferId)}/events/summary`);
}

export async function cancelTransfer(transferId) {
  return request(`/v1/transfers/${encodeURIComponent(transferId)}/cancel`, {
    method: "POST",
  });
}

// ── Identity ──────────────────────────────────────────

export async function createUser(input) {
  return request("/v1/users", {
    method: "POST",
    headers: { "Idempotency-Key": requestId() },
    body: JSON.stringify(input),
  });
}

export async function getUser(userId) {
  return request(`/v1/users/${encodeURIComponent(userId)}`);
}

export async function getUserStatus(userId) {
  return request(`/v1/users/${encodeURIComponent(userId)}/status`);
}

// ── Alias ─────────────────────────────────────────────

export async function resolveAlias(phoneE164) {
  const q = new URLSearchParams({ phone_e164: phoneE164 });
  return request(`/v1/aliases/resolve?${q.toString()}`);
}

export async function submitKyc(userId, providerCaseId) {
  return request(`/v1/users/${encodeURIComponent(userId)}/kyc/submit`, {
    method: "POST",
    body: JSON.stringify({ provider_case_id: providerCaseId }),
  });
}

export async function verifyPhone(phoneE164) {
  return request("/v1/aliases/verify-phone", {
    method: "POST",
    body: JSON.stringify({ phone_e164: phoneE164 }),
  });
}

export async function bindAlias(verificationId, userId) {
  return request("/v1/aliases/bind", {
    method: "POST",
    body: JSON.stringify({ verification_id: verificationId, user_id: userId }),
  });
}
