import {
  cancelTransfer,
  checkGateway,
  createTransfer,
  getApiBase,
  getTransfer,
  getTransferEvents,
  listTransfers,
} from "./api.js";

const gatewayStatusEl = document.getElementById("gatewayStatus");
const transferForm = document.getElementById("transferForm");
const sendBtn = document.getElementById("sendBtn");
const formFeedback = document.getElementById("formFeedback");

const authPanelEl = document.getElementById("authPanel");
const authForm = document.getElementById("authForm");
const authUserIdEl = document.getElementById("authUserId");
const signOutBtn = document.getElementById("signOutBtn");
const summaryPanelEl = document.getElementById("summaryPanel");
const sendPanelEl = document.getElementById("sendPanel");
const listPanelEl = document.getElementById("listPanel");
const detailPanelEl = document.getElementById("detailPanel");

const welcomeTitleEl = document.getElementById("welcomeTitle");
const statsCountEl = document.getElementById("statsCount");
const statsTotalEl = document.getElementById("statsTotal");
const statsStatusEl = document.getElementById("statsStatus");

const transferListEl = document.getElementById("transferList");
const transferDetailsEl = document.getElementById("transferDetails");
const eventsListEl = document.getElementById("eventsList");

const refreshListBtn = document.getElementById("refreshListBtn");
const applyFiltersBtn = document.getElementById("applyFiltersBtn");
const reloadDetailsBtn = document.getElementById("reloadDetailsBtn");
const cancelTransferBtn = document.getElementById("cancelTransferBtn");

const filterSenderEl = document.getElementById("filterSender");
const filterStatusEl = document.getElementById("filterStatus");
const senderUserIdEl = document.getElementById("senderUserId");

const SESSION_KEY = "ebank.client.user";

const state = {
  transfers: [],
  selectedTransferId: null,
  loadingList: false,
  loadingDetails: false,
  signedInUserId: null,
};

const currencyDecimals = {
  JPY: 0,
  KRW: 0,
};

function setGatewayStatus(text, isHealthy = false) {
  gatewayStatusEl.textContent = `${text} (${getApiBase()})`;
  gatewayStatusEl.style.color = isHealthy ? "#0b7e5a" : "#6b3a10";
}

function setFeedback(message, kind = "") {
  formFeedback.textContent = message || "";
  formFeedback.className = `feedback ${kind}`.trim();
}

function amountToMinor(amountInput, currency) {
  const normalized = amountInput.trim().replace(",", ".");
  const amount = Number.parseFloat(normalized);
  if (!Number.isFinite(amount) || amount <= 0) {
    throw new Error("Amount must be a positive number");
  }

  const decimals = currencyDecimals[currency] ?? 2;
  return Math.round(amount * Math.pow(10, decimals));
}

function moneyLabel(transfer) {
  const currency = transfer.currency;
  const decimals = currencyDecimals[currency] ?? 2;
  const value = transfer.amount_minor / Math.pow(10, decimals);
  return `${currency} ${value.toFixed(decimals)}`;
}

function formatMinor(minor, currency = "USD") {
  const decimals = currencyDecimals[currency] ?? 2;
  const value = minor / Math.pow(10, decimals);
  return `${currency} ${value.toFixed(decimals)}`;
}

function formatDateTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function applyAuthState() {
  const isSignedIn = Boolean(state.signedInUserId);

  authPanelEl.classList.toggle("hidden", isSignedIn);
  summaryPanelEl.classList.toggle("hidden", !isSignedIn);
  sendPanelEl.classList.toggle("hidden", !isSignedIn);
  listPanelEl.classList.toggle("hidden", !isSignedIn);
  detailPanelEl.classList.toggle("hidden", !isSignedIn);
  signOutBtn.classList.toggle("hidden", !isSignedIn);

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
  }
  applyAuthState();
}

function setSummaryStats() {
  const myTransfers = state.signedInUserId
    ? state.transfers.filter((transfer) => transfer.sender_user_id === state.signedInUserId)
    : [];

  const totalMinor = myTransfers.reduce((sum, transfer) => sum + transfer.amount_minor, 0);
  const latest = myTransfers[0];

  statsCountEl.textContent = String(myTransfers.length);
  statsTotalEl.textContent = formatMinor(totalMinor, latest?.currency || "USD");
  statsStatusEl.textContent = latest?.status || "-";
}

function renderTransferList() {
  transferListEl.innerHTML = "";

  if (!state.transfers.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No transfers found.";
    transferListEl.appendChild(empty);
    return;
  }

  for (const transfer of state.transfers) {
    const card = document.createElement("article");
    card.className = "transfer-card";
    if (transfer.transfer_id === state.selectedTransferId) {
      card.classList.add("active");
    }

    card.innerHTML = `
      <div class="transfer-meta">
        <strong>${moneyLabel(transfer)}</strong>
        <span>${transfer.status}</span>
      </div>
      <div class="transfer-meta">
        <span>${transfer.sender_user_id} -> ${transfer.recipient_phone_e164}</span>
        <span>${new Date(transfer.created_at).toLocaleDateString()}</span>
      </div>
      <div class="transfer-id">${transfer.transfer_id}</div>
    `;

    card.addEventListener("click", () => {
      state.selectedTransferId = transfer.transfer_id;
      renderTransferList();
      void loadTransferDetails(transfer.transfer_id);
    });

    transferListEl.appendChild(card);
  }
}

function renderTransferDetails(transfer) {
  if (!transfer) {
    transferDetailsEl.className = "details-empty";
    transferDetailsEl.textContent = "Select a transfer to view details.";
    cancelTransferBtn.disabled = true;
    return;
  }

  cancelTransferBtn.disabled = transfer.status !== "CREATED" && transfer.status !== "VALIDATED";

  transferDetailsEl.className = "details-grid";
  transferDetailsEl.innerHTML = `
    <div><span>Transfer ID</span>${transfer.transfer_id}</div>
    <div><span>Status</span>${transfer.status}</div>
    <div><span>Amount</span>${moneyLabel(transfer)}</div>
    <div><span>Sender</span>${transfer.sender_user_id}</div>
    <div><span>Recipient</span>${transfer.recipient_phone_e164}</div>
    <div><span>Created</span>${formatDateTime(transfer.created_at)}</div>
    <div><span>Updated</span>${formatDateTime(transfer.updated_at)}</div>
    <div><span>External Ref</span>${transfer.connector_external_ref || "-"}</div>
    <div><span>Failure Reason</span>${transfer.failure_reason || "-"}</div>
  `;
}

function renderEvents(events) {
  eventsListEl.innerHTML = "";

  if (!events || !events.length) {
    const empty = document.createElement("li");
    empty.className = "empty";
    empty.textContent = "No events yet.";
    eventsListEl.appendChild(empty);
    return;
  }

  for (const event of events) {
    const item = document.createElement("li");
    const transition = event.from_status && event.to_status ? `${event.from_status} -> ${event.to_status}` : event.event_type;
    item.innerHTML = `
      <strong>${transition}</strong>
      <small>${formatDateTime(event.created_at)}</small>
      ${event.failure_reason ? `<small>${event.failure_reason}</small>` : ""}
    `;
    eventsListEl.appendChild(item);
  }
}

async function loadGatewayStatus() {
  try {
    const healthy = await checkGateway();
    setGatewayStatus(healthy ? "Gateway online" : "Gateway responded unexpectedly", healthy);
  } catch {
    setGatewayStatus("Gateway unavailable", false);
  }
}

async function loadTransfers() {
  if (!state.signedInUserId || state.loadingList) return;
  state.loadingList = true;
  refreshListBtn.disabled = true;
  applyFiltersBtn.disabled = true;

  try {
    const data = await listTransfers({
      senderUserId: filterSenderEl.value.trim() || state.signedInUserId,
      status: filterStatusEl.value,
      limit: 30,
    });

    state.transfers = data.transfers || [];

    if (state.selectedTransferId && !state.transfers.some((t) => t.transfer_id === state.selectedTransferId)) {
      state.selectedTransferId = null;
      renderTransferDetails(null);
      renderEvents([]);
    }

    renderTransferList();
    setSummaryStats();
  } catch (error) {
    transferListEl.innerHTML = `<div class="empty">${error.message}</div>`;
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
  } catch (error) {
    transferDetailsEl.className = "details-empty";
    transferDetailsEl.textContent = error.message;
    renderEvents([]);
  } finally {
    state.loadingDetails = false;
    reloadDetailsBtn.disabled = false;
  }
}

authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const userId = authUserIdEl.value.trim();
  if (!userId) return;

  setSignedInUser(userId);
  state.selectedTransferId = null;
  renderTransferDetails(null);
  renderEvents([]);
  await loadTransfers();
});

signOutBtn.addEventListener("click", () => {
  setSignedInUser(null);
});

transferForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setFeedback("");
  sendBtn.disabled = true;

  const formData = new FormData(transferForm);
  const sender_user_id = state.signedInUserId || String(formData.get("senderUserId") || "").trim();
  const recipient_phone_e164 = String(formData.get("recipientPhone") || "").trim();
  const currency = String(formData.get("currency") || "USD").trim().toUpperCase();
  const noteValue = String(formData.get("note") || "").trim();
  const note = noteValue || null;

  try {
    const amount_minor = amountToMinor(String(formData.get("amount") || ""), currency);

    const transfer = await createTransfer({
      sender_user_id,
      recipient_phone_e164,
      currency,
      amount_minor,
      note,
    });

    setFeedback(`Transfer created: ${transfer.transfer_id}`, "success");
    transferForm.reset();
    document.getElementById("currency").value = currency;
    senderUserIdEl.value = sender_user_id;

    state.selectedTransferId = transfer.transfer_id;
    await loadTransfers();
    await loadTransferDetails(transfer.transfer_id);
  } catch (error) {
    setFeedback(error.message, "error");
  } finally {
    sendBtn.disabled = false;
  }
});

refreshListBtn.addEventListener("click", () => {
  void loadTransfers();
});

applyFiltersBtn.addEventListener("click", () => {
  state.selectedTransferId = null;
  renderTransferDetails(null);
  renderEvents([]);
  void loadTransfers();
});

reloadDetailsBtn.addEventListener("click", () => {
  void loadTransferDetails();
});

cancelTransferBtn.addEventListener("click", async () => {
  if (!state.selectedTransferId) return;
  cancelTransferBtn.disabled = true;

  try {
    await cancelTransfer(state.selectedTransferId);
    await loadTransfers();
    await loadTransferDetails(state.selectedTransferId);
  } catch (error) {
    transferDetailsEl.className = "details-empty";
    transferDetailsEl.textContent = error.message;
  } finally {
    cancelTransferBtn.disabled = false;
  }
});

const persistedUser = window.localStorage.getItem(SESSION_KEY);
if (persistedUser) {
  setSignedInUser(persistedUser);
  void loadTransfers();
} else {
  applyAuthState();
}

void loadGatewayStatus();
