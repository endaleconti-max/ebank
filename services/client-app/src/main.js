import {
  bindAlias,
  cancelTransfer,
  checkGateway,
  createTransfer,
  createUser,
  getApiBase,
  getTransfer,
  getTransferEvents,
  getUserStatus,
  listTransfers,
  resolveAlias,
  submitKyc,
  verifyPhone,
} from "./api.js";

// ── DOM refs ─────────────────────────────────────────
const gatewayStatusEl   = document.getElementById("gatewayStatus");
const transferForm      = document.getElementById("transferForm");
const sendBtn           = document.getElementById("sendBtn");
const formFeedback      = document.getElementById("formFeedback");
const toastEl           = document.getElementById("toast");

const authPanelEl       = document.getElementById("authPanel");
const authForm          = document.getElementById("authForm");
const authUserIdEl      = document.getElementById("authUserId");
const signOutBtn        = document.getElementById("signOutBtn");
const summaryPanelEl    = document.getElementById("summaryPanel");
const sendPanelEl       = document.getElementById("sendPanel");
const listPanelEl       = document.getElementById("listPanel");
const detailPanelEl     = document.getElementById("detailPanel");
const senderIdLabel     = document.getElementById("senderIdLabel");

const tabSignIn         = document.getElementById("tabSignIn");
const tabRegister       = document.getElementById("tabRegister");
const panelSignIn       = document.getElementById("panelSignIn");
const panelRegister     = document.getElementById("panelRegister");
const registerForm      = document.getElementById("registerForm");
const registerFeedback  = document.getElementById("registerFeedback");

const kycActionEl       = document.getElementById("kycAction");
const kycActionForm     = document.getElementById("kycActionForm");
const kycCaseIdEl       = document.getElementById("kycCaseId");
const kycActionFeedback = document.getElementById("kycActionFeedback");
const kycSubmitBtnEl    = document.getElementById("kycSubmitBtn");

const phoneLinkPanelEl   = document.getElementById("phoneLinkPanel");
const phoneLinkStep1El   = document.getElementById("phoneLinkStep1");
const phoneLinkStep2El   = document.getElementById("phoneLinkStep2");
const phoneLinkFormEl    = document.getElementById("phoneLinkForm");
const phoneLinkInputEl   = document.getElementById("phoneLinkInput");
const phoneLinkFeedback  = document.getElementById("phoneLinkFeedback");
const phoneLinkConfirmedMsgEl = document.getElementById("phoneLinkConfirmedMsg");
const phoneLinkBindBtnEl = document.getElementById("phoneLinkBindBtn");
const phoneLinkCancelBtnEl = document.getElementById("phoneLinkCancelBtn");
const phoneLinkBindFeedback = document.getElementById("phoneLinkBindFeedback");

const loadMoreRowEl     = document.getElementById("loadMoreRow");
const loadMoreBtnEl     = document.getElementById("loadMoreBtn");

const welcomeTitleEl    = document.getElementById("welcomeTitle");
const statsCountEl      = document.getElementById("statsCount");
const statsTotalEl      = document.getElementById("statsTotal");
const statsStatusEl     = document.getElementById("statsStatus");
const statsKycEl        = document.getElementById("statsKyc");

const transferListEl    = document.getElementById("transferList");
const transferDetailsEl = document.getElementById("transferDetails");
const eventsListEl      = document.getElementById("eventsList");

const refreshListBtn    = document.getElementById("refreshListBtn");
const applyFiltersBtn   = document.getElementById("applyFiltersBtn");
const reloadDetailsBtn  = document.getElementById("reloadDetailsBtn");
const cancelTransferBtn = document.getElementById("cancelTransferBtn");

const filterSenderEl    = document.getElementById("filterSender");
const filterStatusEl    = document.getElementById("filterStatus");
const senderUserIdEl    = document.getElementById("senderUserId");
const recipientPhoneEl  = document.getElementById("recipientPhone");
const aliasHintEl       = document.getElementById("aliasHint");

const SESSION_KEY       = "ebank.client.user";
const POLL_INTERVAL_MS  = 5_000;
const TERMINAL_STATUSES = new Set(["SETTLED", "FAILED"]);

// ── App state ─────────────────────────────────────────
const state = {
  transfers: [],
  selectedTransferId: null,
  loadingList: false,
  loadingDetails: false,
  signedInUserId: null,
  pollTimer: null,
  kycStatus: null,
  nextCursor: null,
  phoneLinkVerificationId: null,
  phoneLinkPhone: null,
};

// ── Currency helpers ─────────────────────────────────
const ZERO_DECIMAL = new Set(["JPY", "KRW", "CLP", "VND"]);

function decimalsFor(currency) {
  return ZERO_DECIMAL.has(currency) ? 0 : 2;
}

function amountToMinor(amountInput, currency) {
  const normalized = amountInput.trim().replace(",", ".");
  const amount = Number.parseFloat(normalized);
  if (!Number.isFinite(amount) || amount <= 0) {
    throw new Error("Amount must be a positive number");
  }
  return Math.round(amount * Math.pow(10, decimalsFor(currency)));
}

function moneyLabel(transfer) {
  const { currency, amount_minor } = transfer;
  const dec = decimalsFor(currency);
  const value = amount_minor / Math.pow(10, dec);
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(value);
  } catch {
    return `${currency} ${value.toFixed(dec)}`;
  }
}

function formatMinor(minor, currency = "USD") {
  const dec = decimalsFor(currency);
  const value = minor / Math.pow(10, dec);
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(value);
  } catch {
    return `${currency} ${value.toFixed(dec)}`;
  }
}

function formatDateTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

// ── Status badge ─────────────────────────────────────
const STATUS_CLASS = {
  CREATED:           "badge-created",
  VALIDATED:         "badge-validated",
  RESERVED:          "badge-reserved",
  SUBMITTED_TO_RAIL: "badge-submitted",
  SETTLED:           "badge-settled",
  FAILED:            "badge-failed",
};

function statusBadge(status) {
  const cls = STATUS_CLASS[status] || "badge-default";
  return `<span class="badge ${cls}">${status}</span>`;
}

// ── Toast ────────────────────────────────────────────
let toastTimer = null;

function showToast(message, isError = false) {
  clearTimeout(toastTimer);
  toastEl.textContent = message;
  toastEl.className = `toast${isError ? " toast-error" : ""}`;
  // Force reflow so transition fires even on rapid re-calls
  void toastEl.offsetWidth;
  toastEl.classList.add("show");
  toastTimer = setTimeout(() => toastEl.classList.remove("show"), 3500);
}

// ── Feedback (form-level, stays visible) ─────────────
function setFeedback(message, kind = "") {
  formFeedback.textContent = message || "";
  formFeedback.className = `feedback ${kind}`.trim();
}

// ── Gateway status pill ──────────────────────────────
function setGatewayStatus(text, isHealthy = false) {
  gatewayStatusEl.textContent = `${text} (${getApiBase()})`;
  gatewayStatusEl.style.color = isHealthy ? "#0b7e5a" : "#6b3a10";
}

// ── Detail auto-poll ─────────────────────────────────
function startPolling(transferId) {
  stopPolling();
  const dot = reloadDetailsBtn.querySelector(".polling-dot") || document.createElement("span");
  dot.className = "polling-dot";
  reloadDetailsBtn.appendChild(dot);

  state.pollTimer = setInterval(async () => {
    const current = state.transfers.find((t) => t.transfer_id === transferId);
    if (current && TERMINAL_STATUSES.has(current.status)) {
      stopPolling();
      return;
    }
    await Promise.allSettled([loadTransferDetails(transferId), loadTransfers()]);
  }, POLL_INTERVAL_MS);
}

function stopPolling() {
  if (state.pollTimer) {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
  const dot = reloadDetailsBtn.querySelector(".polling-dot");
  if (dot) dot.remove();
}

// ── KYC badge ───────────────────────────────────────
const KYC_CLASS = {
  PENDING:   "badge-created",
  SUBMITTED: "badge-validated",
  APPROVED:  "badge-settled",
  REJECTED:  "badge-failed",
};

function kycBadge(status) {
  if (!status) return "-";
  const cls = KYC_CLASS[status] || "badge-default";
  return `<span class="badge ${cls}">${status}</span>`;
}

async function loadKycStatus() {
  if (!state.signedInUserId) return;
  try {
    const data = await getUserStatus(state.signedInUserId);
    state.kycStatus = data.kyc_status;
    statsKycEl.innerHTML = kycBadge(data.kyc_status);
    if (kycActionEl) kycActionEl.classList.toggle("hidden", data.kyc_status !== "PENDING");
  } catch {
    statsKycEl.textContent = "-";
    if (kycActionEl) kycActionEl.classList.add("hidden");
  }
}

// ── Auth tabs ───────────────────────────────────────
function switchTab(tab) {
  const isSignIn = tab === "signin";
  tabSignIn.classList.toggle("active", isSignIn);
  tabRegister.classList.toggle("active", !isSignIn);
  panelSignIn.classList.toggle("hidden", !isSignIn);
  panelRegister.classList.toggle("hidden", isSignIn);
}

tabSignIn.addEventListener("click", () => switchTab("signin"));
tabRegister.addEventListener("click", () => switchTab("register"));

// ── Alias hint ──────────────────────────────────────
let aliasDebounce = null;

recipientPhoneEl.addEventListener("input", () => {
  clearTimeout(aliasDebounce);
  const phone = recipientPhoneEl.value.trim();
  aliasHintEl.textContent = "";
  aliasHintEl.className = "alias-hint";

  if (!/^\+[1-9]\d{7,14}$/.test(phone)) return;

  aliasDebounce = setTimeout(async () => {
    try {
      const data = await resolveAlias(phone);
      if (data.found && data.alias) {
        aliasHintEl.textContent = `✓ Registered — user ${data.alias.user_id}`;
        aliasHintEl.className = "alias-hint";
      } else {
        aliasHintEl.textContent = "Not registered on eBank";
        aliasHintEl.className = "alias-hint not-found";
      }
    } catch {
      aliasHintEl.textContent = "";
    }
  }, 450);
});

// ── Auth ─────────────────────────────────────────────
function applyAuthState() {
  const isSignedIn = Boolean(state.signedInUserId);

  authPanelEl.classList.toggle("hidden", isSignedIn);
  summaryPanelEl.classList.toggle("hidden", !isSignedIn);
  phoneLinkPanelEl.classList.toggle("hidden", !isSignedIn);
  sendPanelEl.classList.toggle("hidden", !isSignedIn);
  listPanelEl.classList.toggle("hidden", !isSignedIn);
  detailPanelEl.classList.toggle("hidden", !isSignedIn);
  signOutBtn.classList.toggle("hidden", !isSignedIn);

  // Hide the sender-id field; the signed-in user is already the sender
  if (senderIdLabel) senderIdLabel.classList.toggle("hidden", isSignedIn);

  if (isSignedIn) {
    welcomeTitleEl.textContent = `Hello, ${state.signedInUserId}`;
    senderUserIdEl.value = state.signedInUserId;
    senderUserIdEl.readOnly = true;
    filterSenderEl.value = state.signedInUserId;
  } else {
    welcomeTitleEl.textContent = "Hello";
    senderUserIdEl.readOnly = false;
    state.transfers = [];
    state.selectedTransferId = null;
    state.nextCursor = null;
    state.phoneLinkVerificationId = null;
    state.phoneLinkPhone = null;
    // Reset phone link panel to step 1
    if (phoneLinkStep1El) phoneLinkStep1El.classList.remove("hidden");
    if (phoneLinkStep2El) phoneLinkStep2El.classList.add("hidden");
    if (phoneLinkInputEl) phoneLinkInputEl.value = "";
    if (phoneLinkFeedback) phoneLinkFeedback.textContent = "";
    stopPolling();
    renderTransferList();
    renderTransferDetails(null);
    renderEvents([]);
    setSummaryStats();
  }
}

function setSignedInUser(userId) {
  state.signedInUserId = userId;
  if (userId) {
    window.localStorage.setItem(SESSION_KEY, userId);
  } else {
    window.localStorage.removeItem(SESSION_KEY);
    state.kycStatus = null;
    if (statsKycEl) statsKycEl.textContent = "-";
    if (kycActionEl) kycActionEl.classList.add("hidden");
  }
  applyAuthState();
}

// ── Summary stats ─────────────────────────────────────
function setSummaryStats() {
  const mine = state.signedInUserId
    ? state.transfers.filter((t) => t.sender_user_id === state.signedInUserId)
    : [];

  const totalMinor = mine.reduce((n, t) => n + t.amount_minor, 0);
  const latest = mine[0];

  statsCountEl.textContent = String(mine.length);
  statsTotalEl.textContent = formatMinor(totalMinor, latest?.currency || "USD");
  statsStatusEl.innerHTML  = latest ? statusBadge(latest.status) : "-";
}

// ── Skeleton helpers ─────────────────────────────────
function skeletonCards(count = 3) {
  return Array.from({ length: count }, () => `
    <div class="skeleton-card">
      <div class="skeleton" style="width:55%"></div>
      <div class="skeleton" style="width:80%"></div>
      <div class="skeleton" style="width:40%"></div>
    </div>
  `).join("");
}

// ── Render: transfer list ────────────────────────────
function renderTransferList() {
  transferListEl.innerHTML = "";

  if (!state.transfers.length) {
    transferListEl.innerHTML = `<div class="empty">No transfers found.</div>`;
    return;
  }

  for (const transfer of state.transfers) {
    const card = document.createElement("article");
    card.className = "transfer-card";
    if (transfer.transfer_id === state.selectedTransferId) card.classList.add("active");

    card.innerHTML = `
      <div class="transfer-meta">
        <strong>${moneyLabel(transfer)}</strong>
        ${statusBadge(transfer.status)}
      </div>
      <div class="transfer-meta">
        <span>${transfer.sender_user_id} &rarr; ${transfer.recipient_phone_e164}</span>
        <span>${new Date(transfer.created_at).toLocaleDateString()}</span>
      </div>
      ${transfer.note ? `<div class="transfer-note"><span>${transfer.note}</span></div>` : ""}
      <div class="transfer-id">${transfer.transfer_id}</div>
    `;

    card.addEventListener("click", () => {
      state.selectedTransferId = transfer.transfer_id;
      renderTransferList();
      void loadTransferDetails(transfer.transfer_id);
      startPolling(transfer.transfer_id);
    });

    transferListEl.appendChild(card);
  }
}

// ── Render: detail ────────────────────────────────────
function renderTransferDetails(transfer) {
  if (!transfer) {
    transferDetailsEl.className = "details-empty";
    transferDetailsEl.textContent = "Select a transfer to view details.";
    cancelTransferBtn.disabled = true;
    return;
  }

  const cancellable = transfer.status === "CREATED" || transfer.status === "VALIDATED";
  cancelTransferBtn.disabled = !cancellable;

  transferDetailsEl.className = "details-grid";
  transferDetailsEl.innerHTML = `
    <div><span>Transfer ID</span>${transfer.transfer_id}</div>
    <div><span>Status</span>${statusBadge(transfer.status)}</div>
    <div><span>Amount</span>${moneyLabel(transfer)}</div>
    <div><span>Sender</span>${transfer.sender_user_id}</div>
    <div><span>Recipient</span>${transfer.recipient_phone_e164}</div>
    ${transfer.note ? `<div class="span-2"><span>Note</span>${transfer.note}</div>` : ""}
    <div><span>Created</span>${formatDateTime(transfer.created_at)}</div>
    <div><span>Updated</span>${formatDateTime(transfer.updated_at)}</div>
    <div><span>External Ref</span>${transfer.connector_external_ref || "-"}</div>
    <div><span>Failure Reason</span>${transfer.failure_reason || "-"}</div>
  `;
}

// ── Render: events ────────────────────────────────────
function renderEvents(events) {
  eventsListEl.innerHTML = "";

  if (!events || !events.length) {
    eventsListEl.innerHTML = `<li class="empty">No events yet.</li>`;
    return;
  }

  for (const event of events) {
    const item = document.createElement("li");
    const transition =
      event.from_status && event.to_status
        ? `${statusBadge(event.from_status)} &rarr; ${statusBadge(event.to_status)}`
        : event.event_type;
    item.innerHTML = `
      ${transition}
      <small>${formatDateTime(event.created_at)}</small>
      ${event.failure_reason ? `<small style="color:#b72d2d">${event.failure_reason}</small>` : ""}
    `;
    eventsListEl.appendChild(item);
  }
}

// ── Data loaders ──────────────────────────────────────
async function loadGatewayStatus() {
  try {
    const healthy = await checkGateway();
    setGatewayStatus(healthy ? "Gateway online" : "Gateway responded unexpectedly", healthy);
  } catch {
    setGatewayStatus("Gateway unavailable", false);
  }
}

async function loadTransfers(append = false) {
  if (!state.signedInUserId || state.loadingList) return;
  state.loadingList = true;
  refreshListBtn.disabled = true;
  applyFiltersBtn.disabled = true;
  if (!append) transferListEl.innerHTML = skeletonCards();

  try {
    const data = await listTransfers({
      senderUserId: filterSenderEl.value.trim() || state.signedInUserId,
      status: filterStatusEl.value,
      limit: 20,
      cursor: append ? (state.nextCursor || "") : "",
    });

    const incoming = data.transfers || [];
    state.nextCursor = data.next_cursor || null;
    loadMoreRowEl.classList.toggle("hidden", !state.nextCursor);

    if (append) {
      const existingIds = new Set(state.transfers.map((t) => t.transfer_id));
      state.transfers = state.transfers.concat(incoming.filter((t) => !existingIds.has(t.transfer_id)));
    } else {
      state.transfers = incoming;
    }

    if (
      state.selectedTransferId &&
      !state.transfers.some((t) => t.transfer_id === state.selectedTransferId)
    ) {
      state.selectedTransferId = null;
      stopPolling();
      renderTransferDetails(null);
      renderEvents([]);
    }

    renderTransferList();
    setSummaryStats();
  } catch (error) {
    transferListEl.innerHTML = `<div class="empty">${error.message}</div>`;
    loadMoreRowEl.classList.add("hidden");
  } finally {
    state.loadingList = false;
    refreshListBtn.disabled = false;
    applyFiltersBtn.disabled = false;
  }
}

async function loadTransferDetails(transferId = state.selectedTransferId) {
  if (!transferId || state.loadingDetails) return;
  state.loadingDetails = true;
  reloadDetailsBtn.disabled = true;
  cancelTransferBtn.disabled = true;

  try {
    const [transfer, events] = await Promise.all([
      getTransfer(transferId),
      getTransferEvents(transferId),
    ]);

    renderTransferDetails(transfer);
    renderEvents(events);

    // Update the cached entry so summary stats stay current
    const idx = state.transfers.findIndex((t) => t.transfer_id === transferId);
    if (idx !== -1) {
      state.transfers[idx] = transfer;
      setSummaryStats();
      renderTransferList();
    }

    if (TERMINAL_STATUSES.has(transfer.status)) stopPolling();
  } catch (error) {
    transferDetailsEl.className = "details-empty";
    transferDetailsEl.textContent = error.message;
    renderEvents([]);
  } finally {
    state.loadingDetails = false;
    reloadDetailsBtn.disabled = false;
  }
}

// ── Event listeners ───────────────────────────────────
authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const userId = authUserIdEl.value.trim();
  if (!userId) return;
  setSignedInUser(userId);
  state.selectedTransferId = null;
  renderTransferDetails(null);
  renderEvents([]);
  await Promise.allSettled([loadTransfers(), loadKycStatus()]);
});

registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const btn = /** @type {HTMLButtonElement} */ (document.getElementById("registerBtn"));
  btn.disabled = true;
  registerFeedback.textContent = "";
  registerFeedback.className = "feedback";

  const fullName    = String(document.getElementById("regFullName").value).trim();
  const countryCode = String(document.getElementById("regCountry").value).trim().toUpperCase();
  const email       = String(document.getElementById("regEmail").value).trim();

  try {
    const user = await createUser({ full_name: fullName, country_code: countryCode, email });
    registerFeedback.textContent = `Account created — your ID is ${user.user_id}`;
    registerFeedback.className = "feedback success";
    showToast(`Welcome, ${fullName}! Your ID: ${user.user_id}`);
    // Auto sign in with new user
    authUserIdEl.value = user.user_id;
    switchTab("signin");
    setSignedInUser(user.user_id);
    state.selectedTransferId = null;
    renderTransferDetails(null);
    renderEvents([]);
    await Promise.allSettled([loadTransfers(), loadKycStatus()]);
  } catch (error) {
    registerFeedback.textContent = error.message;
    registerFeedback.className = "feedback error";
  } finally {
    btn.disabled = false;
  }
});

signOutBtn.addEventListener("click", () => {
  stopPolling();
  setSignedInUser(null);
});

transferForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setFeedback("");
  sendBtn.disabled = true;

  const formData = new FormData(transferForm);
  const sender_user_id       = state.signedInUserId || String(formData.get("senderUserId") || "").trim();
  const recipient_phone_e164 = String(formData.get("recipientPhone") || "").trim();
  const currency             = String(formData.get("currency") || "USD").trim().toUpperCase();
  const noteValue            = String(formData.get("note") || "").trim();
  const note                 = noteValue || null;

  try {
    const amount_minor = amountToMinor(String(formData.get("amount") || ""), currency);

    const transfer = await createTransfer({
      sender_user_id,
      recipient_phone_e164,
      currency,
      amount_minor,
      note,
    });

    transferForm.reset();
    document.getElementById("currency").value = currency;
    senderUserIdEl.value = sender_user_id;
    showToast(`Transfer created — ${moneyLabel(transfer)} to ${recipient_phone_e164}`);

    state.selectedTransferId = transfer.transfer_id;
    await loadTransfers();
    await loadTransferDetails(transfer.transfer_id);
    startPolling(transfer.transfer_id);
  } catch (error) {
    setFeedback(error.message, "error");
    showToast(error.message, true);
  } finally {
    sendBtn.disabled = false;
  }
});

refreshListBtn.addEventListener("click", () => { void loadTransfers(); });

applyFiltersBtn.addEventListener("click", () => {
  state.selectedTransferId = null;
  state.nextCursor = null;
  stopPolling();
  renderTransferDetails(null);
  renderEvents([]);
  void loadTransfers();
});

reloadDetailsBtn.addEventListener("click", () => { void loadTransferDetails(); });

cancelTransferBtn.addEventListener("click", async () => {
  if (!state.selectedTransferId) return;
  cancelTransferBtn.disabled = true;

  try {
    await cancelTransfer(state.selectedTransferId);
    showToast("Transfer cancelled.");
    stopPolling();
    await loadTransfers();
    await loadTransferDetails(state.selectedTransferId);
  } catch (error) {
    showToast(error.message, true);
    cancelTransferBtn.disabled = false;
  }
});

// ── Boot ──────────────────────────────────────────────
// ── KYC submission ───────────────────────────────────
kycActionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  kycSubmitBtnEl.disabled = true;
  kycActionFeedback.textContent = "";
  kycActionFeedback.className = "feedback";

  const caseId = kycCaseIdEl.value.trim();
  try {
    await submitKyc(state.signedInUserId, caseId);
    showToast("KYC submitted — verification in progress.");
    kycActionFeedback.textContent = "KYC submission received.";
    kycActionFeedback.className = "feedback success";
    kycCaseIdEl.value = "";
    await loadKycStatus();
  } catch (error) {
    kycActionFeedback.textContent = error.message;
    kycActionFeedback.className = "feedback error";
  } finally {
    kycSubmitBtnEl.disabled = false;
  }
});

// ── Phone link — step 1: verify ──────────────────────
phoneLinkFormEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const verifyBtn = document.getElementById("phoneLinkVerifyBtn");
  verifyBtn.disabled = true;
  phoneLinkFeedback.textContent = "";
  phoneLinkFeedback.className = "feedback";

  const phone = phoneLinkInputEl.value.trim();
  try {
    const data = await verifyPhone(phone);
    state.phoneLinkVerificationId = data.verification_id;
    state.phoneLinkPhone = data.phone_e164;
    phoneLinkConfirmedMsgEl.textContent = `\u2713 ${data.phone_e164} verified \u2014 click Bind to link it to your account.`;
    phoneLinkStep1El.classList.add("hidden");
    phoneLinkStep2El.classList.remove("hidden");
    phoneLinkBindFeedback.textContent = "";
    phoneLinkBindFeedback.className = "feedback";
  } catch (error) {
    phoneLinkFeedback.textContent = error.message;
    phoneLinkFeedback.className = "feedback error";
  } finally {
    verifyBtn.disabled = false;
  }
});

// ── Phone link — step 2: bind ────────────────────────
phoneLinkBindBtnEl.addEventListener("click", async () => {
  phoneLinkBindBtnEl.disabled = true;
  phoneLinkBindFeedback.textContent = "";
  phoneLinkBindFeedback.className = "feedback";

  try {
    const alias = await bindAlias(state.phoneLinkVerificationId, state.signedInUserId);
    showToast(`Phone ${alias.phone_e164} linked to your account!`);
    phoneLinkBindFeedback.textContent = `${alias.phone_e164} is now linked.`;
    phoneLinkBindFeedback.className = "feedback success";
    state.phoneLinkVerificationId = null;
    state.phoneLinkPhone = null;
    setTimeout(() => {
      phoneLinkStep1El.classList.remove("hidden");
      phoneLinkStep2El.classList.add("hidden");
      phoneLinkInputEl.value = "";
      phoneLinkFeedback.textContent = "";
    }, 2500);
  } catch (error) {
    phoneLinkBindFeedback.textContent = error.message;
    phoneLinkBindFeedback.className = "feedback error";
  } finally {
    phoneLinkBindBtnEl.disabled = false;
  }
});

phoneLinkCancelBtnEl.addEventListener("click", () => {
  state.phoneLinkVerificationId = null;
  state.phoneLinkPhone = null;
  phoneLinkStep1El.classList.remove("hidden");
  phoneLinkStep2El.classList.add("hidden");
  phoneLinkInputEl.value = "";
  phoneLinkFeedback.textContent = "";
  phoneLinkFeedback.className = "feedback";
});

// ── Load more ────────────────────────────────────────
loadMoreBtnEl.addEventListener("click", () => { void loadTransfers(true); });

// ── Boot ──────────────────────────────────────────────
const persistedUser = window.localStorage.getItem(SESSION_KEY);
if (persistedUser) {
  setSignedInUser(persistedUser);
  void Promise.allSettled([loadTransfers(), loadKycStatus()]);
} else {
  applyAuthState();
}

void loadGatewayStatus();

