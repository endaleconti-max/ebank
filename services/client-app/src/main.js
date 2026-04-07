import {
  bindAlias,
  cancelTransfer,
  checkGateway,
  createTransfer,
  createUser,
  getApiBase,
  getTransferEventSummary,
  getTransfer,
  getTransferEvents,
  getUserStatus,
  listTransfers,
  resolveAlias,
  submitKyc,
  updateTransferNote,
  verifyPhone,
} from "./api.js";
import { appendUniqueEvents, didEventFiltersChange } from "./eventFeedState.js";
import { buildDeepLinkUrl, getDeepLinkTransferId } from "./deepLink.js";
import { findFilterPreset, removeFilterPreset, upsertFilterPreset } from "./filterPresets.js";
import { buildEventEmptyStateMessage, buildTransferEmptyStateMessage } from "./emptyStateGuidance.js";
import { buildTransferDetailActionPayload } from "./transferDetailActions.js";
import { getShortcutAction } from "./keyboardShortcuts.js";
import { filterEventsBySearch } from "./timelineSearch.js";
import { buildTransferSearchContext } from "./transferSearchHighlight.js";
import { buildTransfersCsv } from "./transferExport.js";
import { buildTransferEventsCsv, buildTransferEventsJson } from "./eventExport.js";
import { buildTransferEventsDigest } from "./eventDigest.js";
import { buildFailedEventsDigest, getFailureEvents } from "./eventFailureDigest.js";
import { buildFailedEventIdsText, formatFailureRateLabel, getFailedEventIds } from "./eventFailureInsights.js";
import { buildFailureSnapshotText } from "./eventFailureSnapshot.js";
import { buildFailureSnapshotReport } from "./eventFailureReport.js";
import { buildFailureMarkdownSummary } from "./eventFailureMarkdown.js";
import { buildTimelineRows } from "./eventTimelineLayout.js";
import { buildRollingDateRange } from "./eventDateShortcuts.js";
import { readStoredEventFilters, writeStoredEventFilters } from "./eventFilterState.js";
import { buildActiveEventFilterChips, buildEventFilterQueryString } from "./eventFilterShare.js";
import { isFailedOnlyEnabled, toggleFailedOnlyStatus } from "./eventFilterModes.js";
import { buildUrlWithEventFilters, readEventFiltersFromSearch } from "./eventFilterUrlState.js";
import { buildEventRowDetailHtml, buildEventRowCopyText, buildExpandedEventCopyText } from "./eventRowDetail.js";
import { getAdjacentEventId, getAdjacentFailureEventId, getBoundaryEventId, getBoundaryFailureEventId, isFailureEvent } from "./eventRowNavigation.js";

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

const loadMoreRowEl      = document.getElementById("loadMoreRow");
const loadMoreBtnEl      = document.getElementById("loadMoreBtn");
const exportTransfersBtnEl = document.getElementById("exportTransfersBtn");
const transferPresetSelectEl = document.getElementById("transferPresetSelect");
const saveTransferPresetBtnEl = document.getElementById("saveTransferPresetBtn");
const applyTransferPresetBtnEl = document.getElementById("applyTransferPresetBtn");
const deleteTransferPresetBtnEl = document.getElementById("deleteTransferPresetBtn");
const transferShortcutFailedReviewBtnEl = document.getElementById("transferShortcutFailedReview");
const transferShortcutNotesBtnEl = document.getElementById("transferShortcutNotes");
const transferShortcutTodayBtnEl = document.getElementById("transferShortcutToday");
const eventLoadMoreRowEl = document.getElementById("eventLoadMoreRow");
const eventLoadMoreBtnEl = document.getElementById("eventLoadMoreBtn");

const welcomeTitleEl    = document.getElementById("welcomeTitle");
const statsCountEl      = document.getElementById("statsCount");
const statsTotalEl      = document.getElementById("statsTotal");
const statsStatusEl     = document.getElementById("statsStatus");
const statsKycEl        = document.getElementById("statsKyc");

const transferListEl     = document.getElementById("transferList");
const transferDetailsEl  = document.getElementById("transferDetails");
const transferShareActionsEl = document.getElementById("transferShareActions");
const copyTransferIdBtnEl = document.getElementById("copyTransferIdBtn");
const copyTransferRecipientBtnEl = document.getElementById("copyTransferRecipientBtn");
const copyTransferLinkBtnEl = document.getElementById("copyTransferLinkBtn");
const shareTransferLinkBtnEl = document.getElementById("shareTransferLinkBtn");
const transferNoteEditorEl = document.getElementById("transferNoteEditor");
const transferNoteInputEl = document.getElementById("transferNoteInput");
const saveTransferNoteBtnEl = document.getElementById("saveTransferNoteBtn");
const transferNoteFeedbackEl = document.getElementById("transferNoteFeedback");
const eventsListEl       = document.getElementById("eventsList");
const eventSummaryChipsEl = document.getElementById("eventSummaryChips");
const eventVisibleCountEl = document.getElementById("eventVisibleCount");
const eventFailedCountEl = document.getElementById("eventFailedCount");
const eventFailureRateEl = document.getElementById("eventFailureRate");
const eventTypeFilterEl   = document.getElementById("eventTypeFilter");
const eventStatusFilterEl = document.getElementById("eventStatusFilter");
const eventDateFromEl     = document.getElementById("eventDateFrom");
const eventDateToEl       = document.getElementById("eventDateTo");
const eventActiveFiltersEl = document.getElementById("eventActiveFilters");
const eventSearchFilterEl = document.getElementById("eventSearchFilter");
const applyEventFiltersBtnEl = document.getElementById("applyEventFiltersBtn");
const clearEventFiltersBtnEl = document.getElementById("clearEventFiltersBtn");
const eventPresetSelectEl = document.getElementById("eventPresetSelect");
const saveEventPresetBtnEl = document.getElementById("saveEventPresetBtn");
const applyEventPresetBtnEl = document.getElementById("applyEventPresetBtn");
const deleteEventPresetBtnEl = document.getElementById("deleteEventPresetBtn");
const eventShortcutFailuresBtnEl = document.getElementById("eventShortcutFailures");
const eventShortcutSettlementBtnEl = document.getElementById("eventShortcutSettlement");
const eventShortcutLast24hBtnEl = document.getElementById("eventShortcutLast24h");
const eventShortcutLast7dBtnEl = document.getElementById("eventShortcutLast7d");
const eventShortcutLast30dBtnEl = document.getElementById("eventShortcutLast30d");
const eventDensityComfortableBtnEl = document.getElementById("eventDensityComfortableBtn");
const eventDensityCompactBtnEl = document.getElementById("eventDensityCompactBtn");
const eventSortOldestBtnEl = document.getElementById("eventSortOldestBtn");
const eventSortNewestBtnEl = document.getElementById("eventSortNewestBtn");
const eventExpandPrevBtnEl = document.getElementById("eventExpandPrevBtn");
const eventExpandNextBtnEl = document.getElementById("eventExpandNextBtn");
const eventExpandFirstBtnEl = document.getElementById("eventExpandFirstBtn");
const eventExpandLastBtnEl = document.getElementById("eventExpandLastBtn");
const failureExpandFirstBtnEl = document.getElementById("failureExpandFirstBtn");
const failureExpandLastBtnEl = document.getElementById("failureExpandLastBtn");
const collapseExpandedEventBtnEl = document.getElementById("collapseExpandedEventBtn");
const eventFailurePrevBtnEl = document.getElementById("eventFailurePrevBtn");
const eventFailureNextBtnEl = document.getElementById("eventFailureNextBtn");
const copyExpandedEventBtnEl = document.getElementById("copyExpandedEventBtn");
const eventFailedOnlyToggleBtnEl = document.getElementById("eventFailedOnlyToggleBtn");
const eventAutoApplyBtnEl = document.getElementById("eventAutoApplyBtn");
const copyEventFiltersBtnEl = document.getElementById("copyEventFiltersBtn");
const exportEventsCsvBtnEl = document.getElementById("exportEventsCsvBtn");
const exportEventsJsonBtnEl = document.getElementById("exportEventsJsonBtn");
const copyEventsDigestBtnEl = document.getElementById("copyEventsDigestBtn");
const copyFailedEventsDigestBtnEl = document.getElementById("copyFailedEventsDigestBtn");
const copyFailedEventIdsBtnEl = document.getElementById("copyFailedEventIdsBtn");
const copyFailureSnapshotBtnEl = document.getElementById("copyFailureSnapshotBtn");
const downloadFailureReportBtnEl = document.getElementById("downloadFailureReportBtn");
const copyFailureMarkdownBtnEl = document.getElementById("copyFailureMarkdownBtn");

const refreshListBtn    = document.getElementById("refreshListBtn");
const applyFiltersBtn   = document.getElementById("applyFiltersBtn");
const filterSearchEl    = document.getElementById("filterSearch");
const filterDateFromEl  = document.getElementById("filterDateFrom");
const filterDateToEl    = document.getElementById("filterDateTo");
const reloadDetailsBtn  = document.getElementById("reloadDetailsBtn");
const cancelTransferBtn = document.getElementById("cancelTransferBtn");

const filterSenderEl    = document.getElementById("filterSender");
const filterStatusEl    = document.getElementById("filterStatus");
const senderUserIdEl    = document.getElementById("senderUserId");
const recipientPhoneEl  = document.getElementById("recipientPhone");
const aliasHintEl       = document.getElementById("aliasHint");

const SESSION_KEY       = "ebank.client.user";
const TRANSFER_PRESETS_KEY = "ebank.client.transfer-presets";
const EVENT_PRESETS_KEY = "ebank.client.event-presets";
const EVENT_FILTERS_KEY = "ebank.client.event-filters";
const EVENT_DENSITY_KEY = "ebank.client.event-density";
const EVENT_SORT_KEY = "ebank.client.event-sort";
const EVENT_AUTO_APPLY_KEY = "ebank.client.event-auto-apply";
const POLL_INTERVAL_MS  = 5_000;
const EVENTS_PAGE_SIZE  = 25;
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
  currentTransfer: null,
  transferEvents: [],
  eventNextCursor: null,
  loadingMoreEvents: false,
  savingTransferNote: false,
  transferFilterPresets: [],
  eventFilterPresets: [],
  phoneLinkVerificationId: null,
  phoneLinkPhone: null,
  eventFilters: {
    eventType: "",
    toStatus: "",
    createdAtFrom: "",
    createdAtTo: "",
    searchText: "",
  },
  eventDensity: "comfortable",
  eventSortOrder: "oldest",
  eventAutoApply: false,
  expandedEventId: null,
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
let eventAutoApplyTimer = null;

function clearEventAutoApplyTimer() {
  if (eventAutoApplyTimer !== null) {
    clearTimeout(eventAutoApplyTimer);
    eventAutoApplyTimer = null;
  }
}

window.addEventListener("pagehide", clearEventAutoApplyTimer);
window.addEventListener("beforeunload", clearEventAutoApplyTimer);
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
  if (!gatewayStatusEl) return;
  gatewayStatusEl.textContent = `${text} (${getApiBase()})`;
  gatewayStatusEl.style.color = isHealthy ? "#0b7e5a" : "#6b3a10";
}

function syncExportButton() {
  if (!exportTransfersBtnEl) return;
  exportTransfersBtnEl.disabled = state.loadingList || state.transfers.length === 0;
}

function syncEventDensityButtons() {
  if (!eventDensityComfortableBtnEl || !eventDensityCompactBtnEl) return;

  const isCompact = state.eventDensity === "compact";
  eventDensityComfortableBtnEl.classList.toggle("active", !isCompact);
  eventDensityCompactBtnEl.classList.toggle("active", isCompact);
  eventDensityComfortableBtnEl.setAttribute("aria-pressed", String(!isCompact));
  eventDensityCompactBtnEl.setAttribute("aria-pressed", String(isCompact));
}

function syncEventSortButtons() {
  if (!eventSortOldestBtnEl || !eventSortNewestBtnEl) return;

  const newestFirst = state.eventSortOrder === "newest";
  eventSortOldestBtnEl.classList.toggle("active", !newestFirst);
  eventSortNewestBtnEl.classList.toggle("active", newestFirst);
  eventSortOldestBtnEl.setAttribute("aria-pressed", String(!newestFirst));
  eventSortNewestBtnEl.setAttribute("aria-pressed", String(newestFirst));
}

function getFilteredTransferEvents(events = state.transferEvents) {
  return filterEventsBySearch(events || [], state.eventFilters.searchText);
}

function getVisibleTransferEvents(events = state.transferEvents) {
  const filteredEvents = getFilteredTransferEvents(events);
  const sortedEvents = [...filteredEvents].sort((left, right) => {
    const leftTime = new Date(left.created_at || 0).getTime();
    const rightTime = new Date(right.created_at || 0).getTime();
    if (leftTime === rightTime) {
      const leftId = String(left.event_id || "");
      const rightId = String(right.event_id || "");
      return leftId.localeCompare(rightId);
    }
    return leftTime - rightTime;
  });

  return state.eventSortOrder === "newest" ? sortedEvents.reverse() : sortedEvents;
}

function syncEventExportButtons() {
  if (!exportEventsCsvBtnEl || !exportEventsJsonBtnEl) return;
  const visibleEvents = getVisibleTransferEvents();
  const hasEvents = visibleEvents.length > 0;
  const hasFailureEvents = visibleEvents.some((event) => isFailureEvent(event));
  const disabled = !state.selectedTransferId || !hasEvents;
  exportEventsCsvBtnEl.disabled = disabled;
  exportEventsJsonBtnEl.disabled = disabled;
  if (copyEventsDigestBtnEl) copyEventsDigestBtnEl.disabled = disabled;
  if (copyFailedEventsDigestBtnEl) copyFailedEventsDigestBtnEl.disabled = !state.selectedTransferId || !hasFailureEvents;
  if (copyFailedEventIdsBtnEl) copyFailedEventIdsBtnEl.disabled = !state.selectedTransferId || !hasFailureEvents;
  if (copyFailureSnapshotBtnEl) copyFailureSnapshotBtnEl.disabled = !state.selectedTransferId || !hasFailureEvents;
  if (downloadFailureReportBtnEl) downloadFailureReportBtnEl.disabled = !state.selectedTransferId || !hasFailureEvents;
  if (copyFailureMarkdownBtnEl) copyFailureMarkdownBtnEl.disabled = !state.selectedTransferId || !hasFailureEvents;
}

function syncEventRowNavigationButtons() {
  const visibleEvents = getVisibleTransferEvents();
  const visibleEventIds = visibleEvents.map((event) => String(event.event_id || "")).filter(Boolean);
  const failedVisibleEventIds = visibleEvents
    .filter((event) => String(event.to_status || "").toUpperCase() === "FAILED" || String(event.event_type || "").toUpperCase().includes("FAILED") || Boolean(event.failure_reason))
    .map((event) => String(event.event_id || ""))
    .filter(Boolean);
  const disabled = !state.selectedTransferId || visibleEventIds.length === 0;
  const failedDisabled = !state.selectedTransferId || failedVisibleEventIds.length === 0;
  const collapseDisabled = !state.selectedTransferId || !state.expandedEventId || !visibleEventIds.includes(String(state.expandedEventId));
  const expandedDisabled = !state.selectedTransferId || !state.expandedEventId || !visibleEventIds.includes(String(state.expandedEventId));
  if (eventExpandPrevBtnEl) eventExpandPrevBtnEl.disabled = disabled;
  if (eventExpandNextBtnEl) eventExpandNextBtnEl.disabled = disabled;
  if (eventExpandFirstBtnEl) eventExpandFirstBtnEl.disabled = disabled;
  if (eventExpandLastBtnEl) eventExpandLastBtnEl.disabled = disabled;
  if (eventFailurePrevBtnEl) eventFailurePrevBtnEl.disabled = failedDisabled;
  if (eventFailureNextBtnEl) eventFailureNextBtnEl.disabled = failedDisabled;
  if (failureExpandFirstBtnEl) failureExpandFirstBtnEl.disabled = failedDisabled;
  if (failureExpandLastBtnEl) failureExpandLastBtnEl.disabled = failedDisabled;
  if (collapseExpandedEventBtnEl) collapseExpandedEventBtnEl.disabled = collapseDisabled;
  if (copyExpandedEventBtnEl) copyExpandedEventBtnEl.disabled = expandedDisabled;
}

function renderEventVisibleCount(visibleCount, totalCount) {
  if (!eventVisibleCountEl) return;
  if (!totalCount) {
    eventVisibleCountEl.textContent = "0 shown";
    return;
  }
  eventVisibleCountEl.textContent = `${visibleCount} shown of ${totalCount}`;
}

function renderFailedVisibleCount(failedVisibleCount, totalVisibleCount) {
  if (!eventFailedCountEl) return;
  if (!totalVisibleCount) {
    eventFailedCountEl.textContent = "0 failed";
    return;
  }
  eventFailedCountEl.textContent = `${failedVisibleCount} failed shown`;
}

function renderFailureRateLabel(failedVisibleCount, totalVisibleCount) {
  if (!eventFailureRateEl) return;
  eventFailureRateEl.textContent = formatFailureRateLabel(failedVisibleCount, totalVisibleCount);
}

function applyEventDensity(density) {
  state.eventDensity = density === "compact" ? "compact" : "comfortable";
  eventsListEl.classList.toggle("events-compact", state.eventDensity === "compact");
  window.localStorage.setItem(EVENT_DENSITY_KEY, state.eventDensity);
  syncEventDensityButtons();
}

function applyEventSortOrder(order) {
  state.eventSortOrder = order === "newest" ? "newest" : "oldest";
  window.localStorage.setItem(EVENT_SORT_KEY, state.eventSortOrder);
  syncEventSortButtons();
}

function setTransferNoteFeedback(message, kind = "") {
  if (!transferNoteFeedbackEl) return;
  transferNoteFeedbackEl.textContent = message || "";
  transferNoteFeedbackEl.className = `feedback ${kind}`.trim();
}

function toStartOfDay(dateValue) {
  return dateValue ? `${dateValue}T00:00:00Z` : "";
}

function toEndOfDay(dateValue) {
  return dateValue ? `${dateValue}T23:59:59Z` : "";
}

function readStoredPresets(storageKey) {
  try {
    const raw = window.localStorage.getItem(storageKey);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((preset) => preset && typeof preset.name === "string") : [];
  } catch {
    return [];
  }
}

function writeStoredPresets(storageKey, presets) {
  window.localStorage.setItem(storageKey, JSON.stringify(presets));
}

function renderPresetSelect(selectEl, presets, placeholder) {
  if (!selectEl) return;
  const previousValue = selectEl.value;
  selectEl.innerHTML = "";
  const placeholderOption = document.createElement("option");
  placeholderOption.value = "";
  placeholderOption.textContent = placeholder;
  selectEl.appendChild(placeholderOption);

  for (const preset of presets) {
    const option = document.createElement("option");
    option.value = preset.name;
    option.textContent = preset.name;
    selectEl.appendChild(option);
  }

  selectEl.value = presets.some((preset) => preset.name === previousValue) ? previousValue : "";
}

function renderTransferPresetOptions() {
  renderPresetSelect(transferPresetSelectEl, state.transferFilterPresets, "Saved transfer presets");
}

function renderEventPresetOptions() {
  renderPresetSelect(eventPresetSelectEl, state.eventFilterPresets, "Saved event presets");
}

function getCurrentTransferFilters() {
  return {
    senderUserId: filterSenderEl.value.trim(),
    status: filterStatusEl.value,
    q: filterSearchEl ? filterSearchEl.value.trim() : "",
    createdAtFrom: filterDateFromEl ? filterDateFromEl.value : "",
    createdAtTo: filterDateToEl ? filterDateToEl.value : "",
  };
}

function applyTransferFilterValues(filters) {
  filterSenderEl.value = filters.senderUserId || state.signedInUserId || "";
  filterStatusEl.value = filters.status || "";
  if (filterSearchEl) filterSearchEl.value = filters.q || "";
  if (filterDateFromEl) filterDateFromEl.value = filters.createdAtFrom || "";
  if (filterDateToEl) filterDateToEl.value = filters.createdAtTo || "";
}

function getCurrentEventFilters() {
  return {
    eventType: eventTypeFilterEl.value,
    toStatus: eventStatusFilterEl.value,
    searchText: eventSearchFilterEl ? eventSearchFilterEl.value.trim() : "",
    createdAtFrom: eventDateFromEl ? eventDateFromEl.value : "",
    createdAtTo: eventDateToEl ? eventDateToEl.value : "",
  };
}

function applyEventFilterValues(filters) {
  eventTypeFilterEl.value = filters.eventType || "";
  eventStatusFilterEl.value = filters.toStatus || "";
  if (eventSearchFilterEl) eventSearchFilterEl.value = filters.searchText || "";
  if (eventDateFromEl) eventDateFromEl.value = filters.createdAtFrom || "";
  if (eventDateToEl) eventDateToEl.value = filters.createdAtTo || "";
  renderActiveEventFilterChips();
  syncEventQuickActionButtons();
}

function syncEventQuickActionButtons() {
  if (eventFailedOnlyToggleBtnEl) {
    const failedOnly = isFailedOnlyEnabled(state.eventFilters);
    eventFailedOnlyToggleBtnEl.classList.toggle("active", failedOnly);
    eventFailedOnlyToggleBtnEl.setAttribute("aria-pressed", String(failedOnly));
  }

  if (eventAutoApplyBtnEl) {
    eventAutoApplyBtnEl.classList.toggle("active", state.eventAutoApply);
    eventAutoApplyBtnEl.setAttribute("aria-pressed", String(state.eventAutoApply));
    eventAutoApplyBtnEl.textContent = `Auto apply: ${state.eventAutoApply ? "On" : "Off"}`;
  }
}

function applyEventAutoApply(enabled) {
  state.eventAutoApply = Boolean(enabled);
  window.localStorage.setItem(EVENT_AUTO_APPLY_KEY, state.eventAutoApply ? "true" : "false");
  syncEventQuickActionButtons();
}

function scheduleAutoApplyEventFilters() {
  if (!state.eventAutoApply) return;
  clearTimeout(eventAutoApplyTimer);
  eventAutoApplyTimer = setTimeout(() => {
    applyEventFilters(getCurrentEventFilters());
  }, 240);
}

function clearAllEventFilters() {
  applyEventFilters({ eventType: "", toStatus: "", createdAtFrom: "", createdAtTo: "", searchText: "" });
}

function renderActiveEventFilterChips() {
  if (!eventActiveFiltersEl) return;
  eventActiveFiltersEl.innerHTML = "";
  const chips = buildActiveEventFilterChips(state.eventFilters);
  eventActiveFiltersEl.classList.toggle("hidden", chips.length === 0);

  for (const chip of chips) {
    const chipButton = document.createElement("button");
    chipButton.type = "button";
    chipButton.className = "event-active-filter-chip";
    chipButton.textContent = `${chip.label}: ${chip.value} x`;
    chipButton.title = `Remove ${chip.label} filter`;
    chipButton.addEventListener("click", () => {
      applyEventFilters({
        ...state.eventFilters,
        [chip.key]: "",
      });
    });
    eventActiveFiltersEl.appendChild(chipButton);
  }

  if (chips.length > 1) {
    const clearAllButton = document.createElement("button");
    clearAllButton.type = "button";
    clearAllButton.className = "event-active-filter-chip event-active-filter-chip-clear";
    clearAllButton.textContent = "Clear all x";
    clearAllButton.title = "Clear all event filters";
    clearAllButton.addEventListener("click", () => {
      clearAllEventFilters();
    });
    eventActiveFiltersEl.appendChild(clearAllButton);
  }
}

async function copyTextToClipboard(value) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }

  const textArea = document.createElement("textarea");
  textArea.value = value;
  textArea.setAttribute("readonly", "true");
  textArea.style.position = "absolute";
  textArea.style.left = "-9999px";
  document.body.appendChild(textArea);
  textArea.select();
  document.execCommand("copy");
  textArea.remove();
}

async function copyTransferValue(kind) {
  if (!state.currentTransfer) return;

  const payload = buildTransferDetailActionPayload(state.currentTransfer, window.location.href);
  const values = {
    transfer_id: { value: payload.transferIdText, message: "Transfer ID copied." },
    recipient: { value: payload.recipientText, message: "Recipient copied." },
    link: { value: payload.shareUrl, message: "Transfer link copied." },
  };

  try {
    await copyTextToClipboard(values[kind].value);
    showToast(values[kind].message);
  } catch {
    showToast("Copy failed.", true);
  }
}

async function shareSelectedTransferLink() {
  if (!state.currentTransfer) return;
  const payload = buildTransferDetailActionPayload(state.currentTransfer, window.location.href);

  if (navigator.share) {
    try {
      await navigator.share({
        title: payload.shareTitle,
        text: payload.shareText,
        url: payload.shareUrl,
      });
      return;
    } catch {
      // Fall back to copying the link.
    }
  }

  await copyTransferValue("link");
}

function applySelectedPresetShortcut() {
  if (state.selectedTransferId && eventPresetSelectEl?.value) {
    applyPreset("event");
    return;
  }
  if (transferPresetSelectEl?.value) {
    applyPreset("transfer");
  }
}

function getTodayDateValue() {
  return new Date().toISOString().slice(0, 10);
}

function resetSelectedTransferView() {
  state.selectedTransferId = null;
  state.currentTransfer = null;
  history.replaceState(null, "", buildDeepLinkUrl(window.location.href, null));
  stopPolling();
  renderTransferDetails(null);
}

async function savePreset(kind) {
  const name = window.prompt(`Save ${kind} preset as:`);
  if (name == null) return;

  const nextPreset = {
    name,
    filters: kind === "transfer" ? getCurrentTransferFilters() : getCurrentEventFilters(),
  };

  try {
    if (kind === "transfer") {
      state.transferFilterPresets = upsertFilterPreset(state.transferFilterPresets, nextPreset);
      writeStoredPresets(TRANSFER_PRESETS_KEY, state.transferFilterPresets);
      renderTransferPresetOptions();
      transferPresetSelectEl.value = state.transferFilterPresets.find((preset) => preset.name.toLowerCase() === String(name).trim().toLowerCase())?.name || "";
    } else {
      state.eventFilterPresets = upsertFilterPreset(state.eventFilterPresets, nextPreset);
      writeStoredPresets(EVENT_PRESETS_KEY, state.eventFilterPresets);
      renderEventPresetOptions();
      eventPresetSelectEl.value = state.eventFilterPresets.find((preset) => preset.name.toLowerCase() === String(name).trim().toLowerCase())?.name || "";
    }
    showToast(`Preset saved.`);
  } catch (error) {
    showToast(error.message, true);
  }
}

function deletePreset(kind) {
  const selectEl = kind === "transfer" ? transferPresetSelectEl : eventPresetSelectEl;
  const presetName = selectEl.value;
  if (!presetName) return;

  if (kind === "transfer") {
    state.transferFilterPresets = removeFilterPreset(state.transferFilterPresets, presetName);
    writeStoredPresets(TRANSFER_PRESETS_KEY, state.transferFilterPresets);
    renderTransferPresetOptions();
  } else {
    state.eventFilterPresets = removeFilterPreset(state.eventFilterPresets, presetName);
    writeStoredPresets(EVENT_PRESETS_KEY, state.eventFilterPresets);
    renderEventPresetOptions();
  }
  showToast("Preset deleted.");
}

function applyEventFilters(nextFilters) {
  const normalizedFilters = {
    eventType: nextFilters.eventType || "",
    toStatus: nextFilters.toStatus || "",
    createdAtFrom: nextFilters.createdAtFrom || "",
    createdAtTo: nextFilters.createdAtTo || "",
    searchText: (nextFilters.searchText || "").trim(),
  };
  if (didEventFiltersChange(state.eventFilters, normalizedFilters)) {
    resetEventFeed();
  }
  state.eventFilters = normalizedFilters;
  writeStoredEventFilters(EVENT_FILTERS_KEY, normalizedFilters);
  history.replaceState(null, "", buildUrlWithEventFilters(window.location.href, normalizedFilters));
  applyEventFilterValues(normalizedFilters);
  void loadTransferDetails();
}

function applyPreset(kind) {
  const selectEl = kind === "transfer" ? transferPresetSelectEl : eventPresetSelectEl;
  const presetName = selectEl.value;
  if (!presetName) return;

  const preset = kind === "transfer"
    ? findFilterPreset(state.transferFilterPresets, presetName)
    : findFilterPreset(state.eventFilterPresets, presetName);
  if (!preset) return;

  if (kind === "transfer") {
    applyTransferFilterValues(preset.filters);
    state.nextCursor = null;
    resetSelectedTransferView();
    void loadTransfers();
  } else {
    applyEventFilters({
      eventType: preset.filters.eventType || "",
      toStatus: preset.filters.toStatus || "",
      createdAtFrom: preset.filters.createdAtFrom || "",
      createdAtTo: preset.filters.createdAtTo || "",
      searchText: preset.filters.searchText || "",
    });
  }
}

function applyTransferShortcut(shortcutName) {
  if (shortcutName === "failed-review") {
    applyTransferFilterValues({
      senderUserId: state.signedInUserId || "",
      status: "FAILED",
      q: "fail",
      createdAtFrom: "",
      createdAtTo: "",
    });
  } else if (shortcutName === "has-note") {
    applyTransferFilterValues({
      senderUserId: state.signedInUserId || "",
      status: "",
      q: "refund",
      createdAtFrom: "",
      createdAtTo: "",
    });
  } else if (shortcutName === "today") {
    const today = getTodayDateValue();
    applyTransferFilterValues({
      senderUserId: state.signedInUserId || "",
      status: "",
      q: "",
      createdAtFrom: today,
      createdAtTo: today,
    });
  }

  state.nextCursor = null;
  resetSelectedTransferView();
  void loadTransfers();
}

function applyEventShortcut(shortcutName) {
  if (shortcutName === "failures") {
    applyEventFilters({
      eventType: "",
      toStatus: "FAILED",
      createdAtFrom: "",
      createdAtTo: "",
      searchText: "fail",
    });
  } else if (shortcutName === "settlement") {
    applyEventFilters({
      eventType: "TRANSFER_STATUS_TRANSITIONED",
      toStatus: "SETTLED",
      createdAtFrom: "",
      createdAtTo: "",
      searchText: "settled",
    });
  }
}

function applyEventDateShortcut(shortcutName) {
  let nextRange = { fromDate: "", toDate: "" };
  if (shortcutName === "last-24h") {
    nextRange = buildRollingDateRange({ hours: 24 });
  } else if (shortcutName === "last-7d") {
    nextRange = buildRollingDateRange({ days: 7 });
  } else if (shortcutName === "last-30d") {
    nextRange = buildRollingDateRange({ days: 30 });
  }

  const currentFilters = getCurrentEventFilters();
  applyEventFilters({
    ...currentFilters,
    createdAtFrom: nextRange.fromDate,
    createdAtTo: nextRange.toDate,
  });
}

function toggleFailedOnlyEvents() {
  applyEventFilters(toggleFailedOnlyStatus(state.eventFilters));
}

function syncEventLoadMore() {
  if (!eventLoadMoreRowEl || !eventLoadMoreBtnEl) return;
  eventLoadMoreRowEl.classList.toggle("hidden", !state.eventNextCursor);
  eventLoadMoreBtnEl.disabled = state.loadingMoreEvents;
}

function resetEventFeed() {
  state.transferEvents = [];
  state.eventNextCursor = null;
  state.loadingMoreEvents = false;
  state.expandedEventId = null;
  renderEvents([]);
  renderEventSummary(null);
  renderEventVisibleCount(0, 0);
  syncEventLoadMore();
  syncEventExportButtons();
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
    resetEventFeed();
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
    state.currentTransfer = null;
    state.transferEvents = [];
    state.eventNextCursor = null;
    state.loadingMoreEvents = false;
    state.eventFilters = { eventType: "", toStatus: "", createdAtFrom: "", createdAtTo: "", searchText: "" };
    if (statsKycEl) statsKycEl.textContent = "-";
    if (kycActionEl) kycActionEl.classList.add("hidden");
    if (eventTypeFilterEl) eventTypeFilterEl.value = "";
    if (eventStatusFilterEl) eventStatusFilterEl.value = "";
    if (eventDateFromEl) eventDateFromEl.value = "";
    if (eventDateToEl) eventDateToEl.value = "";
    if (eventSearchFilterEl) eventSearchFilterEl.value = "";
    if (filterSearchEl) filterSearchEl.value = "";
    if (filterDateFromEl) filterDateFromEl.value = "";
    if (filterDateToEl) filterDateToEl.value = "";
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
  syncExportButton();

  if (!state.transfers.length) {
    transferListEl.innerHTML = `<div class="empty">${buildTransferEmptyStateMessage(Boolean(filterSenderEl.value || filterStatusEl.value || filterSearchEl?.value || filterDateFromEl?.value || filterDateToEl?.value))}</div>`;
    return;
  }

  for (const transfer of state.transfers) {
    const card = document.createElement("article");
    card.className = "transfer-card";
    if (transfer.transfer_id === state.selectedTransferId) card.classList.add("active");

    const searchContexts = buildTransferSearchContext(transfer, filterSearchEl?.value || "");
    const contextMarkup = searchContexts
      .map((context) => `<div class="transfer-match"><span>${context.label}</span>${context.html}</div>`)
      .join("");

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
      ${contextMarkup}
      <div class="transfer-id">${transfer.transfer_id}</div>
    `;

    card.addEventListener("click", () => {
      state.selectedTransferId = transfer.transfer_id;
      history.replaceState(null, "", buildDeepLinkUrl(window.location.href, transfer.transfer_id));
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
    state.currentTransfer = null;
    transferDetailsEl.className = "details-empty";
    transferDetailsEl.textContent = "Select a transfer to view details.";
    cancelTransferBtn.disabled = true;
    if (transferShareActionsEl) transferShareActionsEl.classList.add("hidden");
    if (transferNoteEditorEl) transferNoteEditorEl.classList.add("hidden");
    if (transferNoteInputEl) transferNoteInputEl.value = "";
    setTransferNoteFeedback("");
    resetEventFeed();
    return;
  }

  const cancellable = transfer.status === "CREATED" || transfer.status === "VALIDATED";
  state.currentTransfer = transfer;
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

  if (transferShareActionsEl) transferShareActionsEl.classList.remove("hidden");
  if (transferNoteEditorEl) transferNoteEditorEl.classList.remove("hidden");
  if (transferNoteInputEl) transferNoteInputEl.value = transfer.note || "";
  if (saveTransferNoteBtnEl) saveTransferNoteBtnEl.disabled = state.savingTransferNote;
  setTransferNoteFeedback("");
}

// ── Render: events ────────────────────────────────────
function renderEvents(events) {
  eventsListEl.innerHTML = "";
  eventsListEl.classList.toggle("events-compact", state.eventDensity === "compact");
  syncEventDensityButtons();

  const filteredEvents = getVisibleTransferEvents(events);
  const visibleEventIds = filteredEvents.map((event) => String(event.event_id || "")).filter(Boolean);
  if (state.expandedEventId && !visibleEventIds.includes(String(state.expandedEventId))) {
    state.expandedEventId = null;
  }
  syncEventExportButtons();
  syncEventRowNavigationButtons();
  renderEventVisibleCount(filteredEvents.length, (events || []).length);
  const failedCount = getFailureEvents(filteredEvents).length;
  renderFailedVisibleCount(failedCount, filteredEvents.length);
  renderFailureRateLabel(failedCount, filteredEvents.length);

  if (!filteredEvents.length) {
    const hasFilters = Boolean(
      state.eventFilters.eventType ||
      state.eventFilters.toStatus ||
      state.eventFilters.createdAtFrom ||
      state.eventFilters.createdAtTo ||
      state.eventFilters.searchText
    );
    eventsListEl.innerHTML = `<li class="empty">${buildEventEmptyStateMessage(hasFilters)}</li>`;
    return;
  }

  const timelineRows = buildTimelineRows(filteredEvents);
  for (const row of timelineRows) {
    if (row.kind === "day") {
      const dayBreak = document.createElement("li");
      dayBreak.className = "events-day-break";
      dayBreak.textContent = row.dayKey;
      eventsListEl.appendChild(dayBreak);
      continue;
    }

    const event = row.event;
    const item = document.createElement("li");
    item.dataset.eventId = event.event_id || "";
    const isExpanded = state.expandedEventId === event.event_id;
    if (isExpanded) item.classList.add("event-row-expanded");
    const transition =
      event.from_status && event.to_status
        ? `${statusBadge(event.from_status)} &rarr; ${statusBadge(event.to_status)}`
        : event.event_type;
    item.innerHTML = `
      <div class="event-row-summary">
        <span class="event-row-summary-content">
          ${transition}
          <small>${event.event_type}</small>
          <small>${formatDateTime(event.created_at)}</small>
          ${event.failure_reason ? `<small style="color:#b72d2d">${event.failure_reason}</small>` : ""}
        </span>
        <button class="event-row-copy-btn" title="Copy event" aria-label="Copy event">&#x2398;</button>
      </div>
      ${isExpanded ? buildEventRowDetailHtml(event) : ""}
    `;
    item.querySelector(".event-row-summary-content").addEventListener("click", () => {
      state.expandedEventId = (state.expandedEventId === event.event_id) ? null : event.event_id;
      renderEvents(state.transferEvents);
    });
    item.querySelector(".event-row-copy-btn").addEventListener("click", (e) => {
      e.stopPropagation();
      navigator.clipboard.writeText(buildEventRowCopyText(event)).catch(() => {});
      showToast("Event copied");
    });
    eventsListEl.appendChild(item);
  }
}

function navigateExpandedEvent(direction) {
  const visibleEventIds = getVisibleTransferEvents()
    .map((event) => String(event.event_id || ""))
    .filter(Boolean);
  const nextEventId = getAdjacentEventId(visibleEventIds, state.expandedEventId, direction);
  if (!nextEventId) {
    showToast("No visible events to navigate.", true);
    return;
  }

  state.expandedEventId = nextEventId;
  renderEvents(state.transferEvents);

  const rowEl = eventsListEl.querySelector(`li[data-event-id="${nextEventId}"]`);
  if (rowEl) {
    rowEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

function navigateFailureEvent(direction) {
  const visibleEvents = getVisibleTransferEvents();
  const nextEventId = getAdjacentFailureEventId(visibleEvents, state.expandedEventId, direction);
  if (!nextEventId) {
    showToast("No failed events in current view.", true);
    return;
  }

  state.expandedEventId = nextEventId;
  renderEvents(state.transferEvents);

  const rowEl = eventsListEl.querySelector(`li[data-event-id="${nextEventId}"]`);
  if (rowEl) {
    rowEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

function navigateToBoundaryEvent(edge) {
  const visibleEventIds = getVisibleTransferEvents()
    .map((event) => String(event.event_id || ""))
    .filter(Boolean);
  const targetEventId = getBoundaryEventId(visibleEventIds, edge);
  if (!targetEventId) {
    showToast("No visible events to navigate.", true);
    return;
  }

  state.expandedEventId = targetEventId;
  renderEvents(state.transferEvents);

  const rowEl = eventsListEl.querySelector(`li[data-event-id="${targetEventId}"]`);
  if (rowEl) {
    rowEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

function navigateToBoundaryFailureEvent(edge) {
  const visibleEvents = getVisibleTransferEvents();
  const targetEventId = getBoundaryFailureEventId(visibleEvents, edge);
  if (!targetEventId) {
    showToast("No failed events in current view.", true);
    return;
  }

  state.expandedEventId = targetEventId;
  renderEvents(state.transferEvents);

  const rowEl = eventsListEl.querySelector(`li[data-event-id="${targetEventId}"]`);
  if (rowEl) {
    rowEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

function renderEventSummary(summary) {
  if (!eventSummaryChipsEl) return;
  eventSummaryChipsEl.innerHTML = "";

  if (!summary || !summary.total_events) {
    eventSummaryChipsEl.innerHTML = '<span class="event-summary-chip">No events</span>';
    return;
  }

  const chips = [];
  chips.push(`Total ${summary.total_events}`);

  const failedCount = summary.by_to_status?.FAILED || 0;
  if (failedCount > 0) chips.push(`FAILED ${failedCount}`);

  const settledCount = summary.by_to_status?.SETTLED || 0;
  if (settledCount > 0) chips.push(`SETTLED ${settledCount}`);

  const ledgerPostFail = summary.by_event_type?.TRANSFER_LEDGER_POSTING_FAILED || 0;
  if (ledgerPostFail > 0) chips.push(`Ledger submit fail ${ledgerPostFail}`);

  const ledgerRevFail = summary.by_event_type?.TRANSFER_LEDGER_REVERSAL_POSTING_FAILED || 0;
  if (ledgerRevFail > 0) chips.push(`Ledger reversal fail ${ledgerRevFail}`);

  for (const label of chips) {
    const chip = document.createElement("span");
    chip.className = "event-summary-chip";
    chip.textContent = label;
    eventSummaryChipsEl.appendChild(chip);
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
      q: filterSearchEl ? filterSearchEl.value.trim() : "",
      createdAtFrom: filterDateFromEl ? toStartOfDay(filterDateFromEl.value) : "",
      createdAtTo: filterDateToEl ? toEndOfDay(filterDateToEl.value) : "",
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
      resetSelectedTransferView();
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
    syncExportButton();
  }
}

async function loadTransferDetails(transferId = state.selectedTransferId) {
  if (!transferId || state.loadingDetails) return;
  state.loadingDetails = true;
  reloadDetailsBtn.disabled = true;
  cancelTransferBtn.disabled = true;
  state.loadingMoreEvents = false;
  syncEventLoadMore();

  try {
    const [transfer, eventsResult, summary] = await Promise.all([
      getTransfer(transferId),
      getTransferEvents(transferId, {
        eventType: state.eventFilters.eventType,
        toStatus: state.eventFilters.toStatus,
        createdAtFrom: toStartOfDay(state.eventFilters.createdAtFrom),
        createdAtTo: toEndOfDay(state.eventFilters.createdAtTo),
        limit: EVENTS_PAGE_SIZE,
      }),
      getTransferEventSummary(transferId),
    ]);

    renderTransferDetails(transfer);
    state.transferEvents = eventsResult.events;
    state.eventNextCursor = eventsResult.nextCursor;
    renderEvents(state.transferEvents);
    renderEventSummary(summary);
    syncEventLoadMore();

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
    resetEventFeed();
  } finally {
    state.loadingDetails = false;
    reloadDetailsBtn.disabled = false;
  }
}

async function loadMoreEvents() {
  if (!state.selectedTransferId || !state.eventNextCursor || state.loadingMoreEvents) return;
  state.loadingMoreEvents = true;
  syncEventLoadMore();

  try {
    const eventsResult = await getTransferEvents(state.selectedTransferId, {
      eventType: state.eventFilters.eventType,
      toStatus: state.eventFilters.toStatus,
      createdAtFrom: toStartOfDay(state.eventFilters.createdAtFrom),
      createdAtTo: toEndOfDay(state.eventFilters.createdAtTo),
      limit: EVENTS_PAGE_SIZE,
      cursor: state.eventNextCursor,
    });
    state.transferEvents = appendUniqueEvents(state.transferEvents, eventsResult.events);
    state.eventNextCursor = eventsResult.nextCursor;
    renderEvents(state.transferEvents);
  } catch (error) {
    showToast(error.message, true);
  } finally {
    state.loadingMoreEvents = false;
    syncEventLoadMore();
  }
}

async function saveSelectedTransferNote() {
  if (!state.selectedTransferId || !transferNoteInputEl || state.savingTransferNote) return;

  state.savingTransferNote = true;
  saveTransferNoteBtnEl.disabled = true;
  setTransferNoteFeedback("");

  try {
    const updatedTransfer = await updateTransferNote(state.selectedTransferId, transferNoteInputEl.value);
    const idx = state.transfers.findIndex((transfer) => transfer.transfer_id === updatedTransfer.transfer_id);
    if (idx !== -1) {
      state.transfers[idx] = updatedTransfer;
      renderTransferList();
      setSummaryStats();
    }
    state.currentTransfer = updatedTransfer;
    renderTransferDetails(updatedTransfer);
    showToast("Transfer note updated.");
    setTransferNoteFeedback("Transfer note saved.", "success");
  } catch (error) {
    setTransferNoteFeedback(error.message, "error");
    showToast(error.message, true);
  } finally {
    state.savingTransferNote = false;
    saveTransferNoteBtnEl.disabled = false;
  }
}

function downloadBlob(content, mimeType, filename) {
  const blob = new Blob([content], { type: mimeType });
  const blobUrl = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(blobUrl);
}

function exportVisibleTransfersCsv() {
  if (!state.transfers.length) {
    showToast("No visible transfers to export.", true);
    return;
  }

  const csv = buildTransfersCsv(state.transfers);
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const blobUrl = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = `transfers-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(blobUrl);
}

function exportFilteredTransferEvents(format) {
  if (!state.selectedTransferId) {
    showToast("Select a transfer before exporting events.", true);
    return;
  }

  const filteredEvents = getVisibleTransferEvents();
  if (!filteredEvents.length) {
    showToast("No filtered events to export.", true);
    return;
  }

  const dateStamp = new Date().toISOString().slice(0, 10);
  const filePrefix = `transfer-events-${state.selectedTransferId}-${dateStamp}`;

  if (format === "csv") {
    const csv = buildTransferEventsCsv(filteredEvents);
    downloadBlob(csv, "text/csv;charset=utf-8", `${filePrefix}.csv`);
    showToast("Filtered events exported as CSV.");
    return;
  }

  const json = buildTransferEventsJson(filteredEvents, {
    transferId: state.selectedTransferId,
    generatedAt: new Date().toISOString(),
    filters: { ...state.eventFilters },
  });
  downloadBlob(json, "application/json;charset=utf-8", `${filePrefix}.json`);
  showToast("Filtered events exported as JSON.");
}

async function copyFilteredTransferEventsDigest() {
  if (!state.selectedTransferId) {
    showToast("Select a transfer before copying the digest.", true);
    return;
  }

  const visibleEvents = getVisibleTransferEvents();
  if (!visibleEvents.length) {
    showToast("No filtered events to copy.", true);
    return;
  }

  try {
    const digest = buildTransferEventsDigest(visibleEvents, state.selectedTransferId);
    await copyTextToClipboard(digest);
    showToast("Filtered event digest copied.");
  } catch {
    showToast("Failed to copy event digest.", true);
  }
}

async function copyFailedTransferEventsDigest() {
  if (!state.selectedTransferId) {
    showToast("Select a transfer before copying failed digest.", true);
    return;
  }

  const visibleEvents = getVisibleTransferEvents();
  const failedEvents = getFailureEvents(visibleEvents);
  if (!failedEvents.length) {
    showToast("No failed events to copy.", true);
    return;
  }

  try {
    const digest = buildFailedEventsDigest(visibleEvents, state.selectedTransferId);
    await copyTextToClipboard(digest);
    showToast("Failed-event digest copied.");
  } catch {
    showToast("Failed to copy failed-event digest.", true);
  }
}

async function copyFailedEventIds() {
  if (!state.selectedTransferId) {
    showToast("Select a transfer before copying failed IDs.", true);
    return;
  }

  const visibleEvents = getVisibleTransferEvents();
  const failedIds = getFailedEventIds(visibleEvents);
  if (!failedIds.length) {
    showToast("No failed event IDs to copy.", true);
    return;
  }

  try {
    const text = buildFailedEventIdsText(visibleEvents, state.selectedTransferId);
    await copyTextToClipboard(text);
    showToast("Failed event IDs copied.");
  } catch {
    showToast("Failed to copy failed event IDs.", true);
  }
}

async function copyFailureSnapshot() {
  if (!state.selectedTransferId) {
    showToast("Select a transfer before copying failure snapshot.", true);
    return;
  }

  const visibleEvents = getVisibleTransferEvents();
  const failedIds = getFailedEventIds(visibleEvents);
  if (!failedIds.length) {
    showToast("No failed events in current view.", true);
    return;
  }

  try {
    const text = buildFailureSnapshotText({
      transferId: state.selectedTransferId,
      events: visibleEvents,
      filterQuery: buildEventFilterQueryString(state.eventFilters),
    });
    await copyTextToClipboard(text);
    showToast("Failure snapshot copied.");
  } catch {
    showToast("Failed to copy failure snapshot.", true);
  }
}

function downloadFailureReport() {
  if (!state.selectedTransferId) {
    showToast("Select a transfer before downloading failure report.", true);
    return;
  }

  const visibleEvents = getVisibleTransferEvents();
  const failedIds = getFailedEventIds(visibleEvents);
  if (!failedIds.length) {
    showToast("No failed events in current view.", true);
    return;
  }

  const report = buildFailureSnapshotReport({
    transferId: state.selectedTransferId,
    events: visibleEvents,
    filterQuery: buildEventFilterQueryString(state.eventFilters),
  });
  const dateStamp = new Date().toISOString().slice(0, 10);
  downloadBlob(report, "text/plain;charset=utf-8", `failure-snapshot-${state.selectedTransferId}-${dateStamp}.txt`);
  showToast("Failure report downloaded.");
}

async function copyFailureMarkdownSummary() {
  if (!state.selectedTransferId) {
    showToast("Select a transfer before copying failure markdown.", true);
    return;
  }

  const visibleEvents = getVisibleTransferEvents();
  const failedIds = getFailedEventIds(visibleEvents);
  if (!failedIds.length) {
    showToast("No failed events in current view.", true);
    return;
  }

  try {
    const markdown = buildFailureMarkdownSummary({
      transferId: state.selectedTransferId,
      events: visibleEvents,
      filterQuery: buildEventFilterQueryString(state.eventFilters),
    });
    await copyTextToClipboard(markdown);
    showToast("Failure markdown copied.");
  } catch {
    showToast("Failed to copy failure markdown.", true);
  }
}

async function copyExpandedEvent() {
  if (!state.selectedTransferId) {
    showToast("Select a transfer before copying event details.", true);
    return;
  }
  if (!state.expandedEventId) {
    showToast("Expand an event row first.", true);
    return;
  }

  const text = buildExpandedEventCopyText(getVisibleTransferEvents(), state.expandedEventId);
  if (!text) {
    showToast("Expanded event is not visible in current filters.", true);
    return;
  }

  try {
    await copyTextToClipboard(text);
    showToast("Expanded event copied.");
  } catch {
    showToast("Failed to copy expanded event.", true);
  }
}

function collapseExpandedEvent() {
  if (!state.selectedTransferId) {
    showToast("Select a transfer before collapsing event details.", true);
    return;
  }
  if (!state.expandedEventId) {
    showToast("No expanded event to collapse.", true);
    return;
  }

  state.expandedEventId = null;
  renderEvents(state.transferEvents);
  showToast("Expanded event collapsed.");
}

async function copyEventFiltersQuery() {
  const query = buildEventFilterQueryString(state.eventFilters);
  if (!query) {
    showToast("No active event filters to copy.", true);
    return;
  }

  try {
    await copyTextToClipboard(`?${query}`);
    showToast("Event filter query copied.");
  } catch {
    showToast("Failed to copy event filters.", true);
  }
}

// ── Event listeners ───────────────────────────────────
authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const userId = authUserIdEl.value.trim();
  if (!userId) return;
  setSignedInUser(userId);
  resetSelectedTransferView();
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
  const emailBase   = fullName.toLowerCase().replace(/[^a-z0-9]+/g, ".").replace(/^\.+|\.+$/g, "") || "user";
  const email       = `${emailBase}.${Date.now()}@client.ebank.local`;

  try {
    const user = await createUser({ full_name: fullName, country_code: countryCode, email });
    registerFeedback.textContent = `Account created — your ID is ${user.user_id}`;
    registerFeedback.className = "feedback success";
    showToast(`Welcome, ${fullName}! Your ID: ${user.user_id}`);
    // Auto sign in with new user
    authUserIdEl.value = user.user_id;
    setSignedInUser(user.user_id);
    resetSelectedTransferView();
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
  history.replaceState(null, "", buildDeepLinkUrl(window.location.href, null));
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
    history.replaceState(null, "", buildDeepLinkUrl(window.location.href, transfer.transfer_id));
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
  state.nextCursor = null;
  resetSelectedTransferView();
  void loadTransfers();
});

applyEventFiltersBtnEl.addEventListener("click", () => {
  applyEventFilters({
    eventType: eventTypeFilterEl.value,
    toStatus: eventStatusFilterEl.value,
    createdAtFrom: eventDateFromEl ? eventDateFromEl.value : "",
    createdAtTo: eventDateToEl ? eventDateToEl.value : "",
    searchText: eventSearchFilterEl ? eventSearchFilterEl.value.trim() : "",
  });
});

clearEventFiltersBtnEl.addEventListener("click", () => {
  clearAllEventFilters();
});

reloadDetailsBtn.addEventListener("click", () => { void loadTransferDetails(); });
saveTransferNoteBtnEl.addEventListener("click", () => { void saveSelectedTransferNote(); });
exportTransfersBtnEl.addEventListener("click", exportVisibleTransfersCsv);
copyTransferIdBtnEl.addEventListener("click", () => { void copyTransferValue("transfer_id"); });
copyTransferRecipientBtnEl.addEventListener("click", () => { void copyTransferValue("recipient"); });
copyTransferLinkBtnEl.addEventListener("click", () => { void copyTransferValue("link"); });
shareTransferLinkBtnEl.addEventListener("click", () => { void shareSelectedTransferLink(); });
saveTransferPresetBtnEl.addEventListener("click", () => { void savePreset("transfer"); });
applyTransferPresetBtnEl.addEventListener("click", () => { applyPreset("transfer"); });
deleteTransferPresetBtnEl.addEventListener("click", () => { deletePreset("transfer"); });
saveEventPresetBtnEl.addEventListener("click", () => { void savePreset("event"); });
applyEventPresetBtnEl.addEventListener("click", () => { applyPreset("event"); });
deleteEventPresetBtnEl.addEventListener("click", () => { deletePreset("event"); });
transferShortcutFailedReviewBtnEl.addEventListener("click", () => { applyTransferShortcut("failed-review"); });
transferShortcutNotesBtnEl.addEventListener("click", () => { applyTransferShortcut("has-note"); });
transferShortcutTodayBtnEl.addEventListener("click", () => { applyTransferShortcut("today"); });
eventShortcutFailuresBtnEl.addEventListener("click", () => { applyEventShortcut("failures"); });
eventShortcutSettlementBtnEl.addEventListener("click", () => { applyEventShortcut("settlement"); });
eventShortcutLast24hBtnEl.addEventListener("click", () => { applyEventDateShortcut("last-24h"); });
eventShortcutLast7dBtnEl.addEventListener("click", () => { applyEventDateShortcut("last-7d"); });
eventShortcutLast30dBtnEl.addEventListener("click", () => { applyEventDateShortcut("last-30d"); });
eventDensityComfortableBtnEl.addEventListener("click", () => { applyEventDensity("comfortable"); });
eventDensityCompactBtnEl.addEventListener("click", () => { applyEventDensity("compact"); });
eventSortOldestBtnEl.addEventListener("click", () => {
  applyEventSortOrder("oldest");
  renderEvents(state.transferEvents);
});
eventSortNewestBtnEl.addEventListener("click", () => {
  applyEventSortOrder("newest");
  renderEvents(state.transferEvents);
});
eventExpandPrevBtnEl.addEventListener("click", () => { navigateExpandedEvent("previous"); });
eventExpandNextBtnEl.addEventListener("click", () => { navigateExpandedEvent("next"); });
eventExpandFirstBtnEl.addEventListener("click", () => { navigateToBoundaryEvent("first"); });
eventExpandLastBtnEl.addEventListener("click", () => { navigateToBoundaryEvent("last"); });
if (failureExpandFirstBtnEl) failureExpandFirstBtnEl.addEventListener("click", () => { navigateToBoundaryFailureEvent("first"); });
if (failureExpandLastBtnEl) failureExpandLastBtnEl.addEventListener("click", () => { navigateToBoundaryFailureEvent("last"); });
collapseExpandedEventBtnEl.addEventListener("click", collapseExpandedEvent);
eventFailurePrevBtnEl.addEventListener("click", () => { navigateFailureEvent("previous"); });
eventFailureNextBtnEl.addEventListener("click", () => { navigateFailureEvent("next"); });
copyExpandedEventBtnEl.addEventListener("click", () => { void copyExpandedEvent(); });
eventFailedOnlyToggleBtnEl.addEventListener("click", () => { toggleFailedOnlyEvents(); });
eventAutoApplyBtnEl.addEventListener("click", () => { applyEventAutoApply(!state.eventAutoApply); });
copyEventFiltersBtnEl.addEventListener("click", () => { void copyEventFiltersQuery(); });
exportEventsCsvBtnEl.addEventListener("click", () => { exportFilteredTransferEvents("csv"); });
exportEventsJsonBtnEl.addEventListener("click", () => { exportFilteredTransferEvents("json"); });
copyEventsDigestBtnEl.addEventListener("click", () => { void copyFilteredTransferEventsDigest(); });
copyFailedEventsDigestBtnEl.addEventListener("click", () => { void copyFailedTransferEventsDigest(); });
copyFailedEventIdsBtnEl.addEventListener("click", () => { void copyFailedEventIds(); });
copyFailureSnapshotBtnEl.addEventListener("click", () => { void copyFailureSnapshot(); });
downloadFailureReportBtnEl.addEventListener("click", downloadFailureReport);
copyFailureMarkdownBtnEl.addEventListener("click", () => { void copyFailureMarkdownSummary(); });

[eventTypeFilterEl, eventStatusFilterEl, eventDateFromEl, eventDateToEl].forEach((el) => {
  el.addEventListener("change", () => {
    scheduleAutoApplyEventFilters();
  });
});

if (eventSearchFilterEl) {
  eventSearchFilterEl.addEventListener("input", () => {
    scheduleAutoApplyEventFilters();
  });
}

window.addEventListener("keydown", (event) => {
  const action = getShortcutAction(event);
  if (!action) return;

  event.preventDefault();
  if (action === "copy-transfer-id") {
    void copyTransferValue("transfer_id");
    return;
  }
  if (action === "copy-transfer-link") {
    void copyTransferValue("link");
    return;
  }
  if (action === "reload-transfer-details") {
    void loadTransferDetails();
    return;
  }
  if (action === "apply-selected-preset") {
    applySelectedPresetShortcut();
    return;
  }
  if (action === "copy-event-filters") {
    void copyEventFiltersQuery();
    return;
  }
  if (action === "copy-event-digest") {
    void copyFilteredTransferEventsDigest();
    return;
  }
  if (action === "copy-failed-event-digest") {
    void copyFailedTransferEventsDigest();
    return;
  }
  if (action === "copy-failed-event-ids") {
    void copyFailedEventIds();
    return;
  }
  if (action === "copy-failure-snapshot") {
    void copyFailureSnapshot();
    return;
  }
  if (action === "download-failure-report") {
    downloadFailureReport();
    return;
  }
  if (action === "copy-failure-markdown") {
    void copyFailureMarkdownSummary();
    return;
  }
  if (action === "sort-events-newest") {
    applyEventSortOrder("newest");
    renderEvents(state.transferEvents);
    return;
  }
  if (action === "sort-events-oldest") {
    applyEventSortOrder("oldest");
    renderEvents(state.transferEvents);
    return;
  }
  if (action === "clear-event-filters") {
    clearAllEventFilters();
    return;
  }
  if (action === "toggle-event-failed-only") {
    toggleFailedOnlyEvents();
    return;
  }
  if (action === "copy-expanded-event") {
    void copyExpandedEvent();
    return;
  }
  if (action === "collapse-expanded-event") {
    collapseExpandedEvent();
    return;
  }
  if (action === "event-expand-previous") {
    navigateExpandedEvent("previous");
    return;
  }
  if (action === "event-expand-next") {
    navigateExpandedEvent("next");
    return;
  }
  if (action === "event-expand-first") {
    navigateToBoundaryEvent("first");
    return;
  }
  if (action === "event-expand-last") {
    navigateToBoundaryEvent("last");
    return;
  }
  if (action === "failure-expand-first") {
    navigateToBoundaryFailureEvent("first");
    return;
  }
  if (action === "failure-expand-last") {
    navigateToBoundaryFailureEvent("last");
    return;
  }
  if (action === "event-failure-previous") {
    navigateFailureEvent("previous");
    return;
  }
  if (action === "event-failure-next") {
    navigateFailureEvent("next");
  }
});

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
eventLoadMoreBtnEl.addEventListener("click", () => { void loadMoreEvents(); });

// ── Boot ──────────────────────────────────────────────
state.transferFilterPresets = readStoredPresets(TRANSFER_PRESETS_KEY);
state.eventFilterPresets = readStoredPresets(EVENT_PRESETS_KEY);
state.eventFilters = readStoredEventFilters(EVENT_FILTERS_KEY);
const urlEventFilterState = readEventFiltersFromSearch(window.location.search);
if (urlEventFilterState.hasUrlFilters) {
  state.eventFilters = urlEventFilterState.filters;
}
renderTransferPresetOptions();
renderEventPresetOptions();
applyEventAutoApply(window.localStorage.getItem(EVENT_AUTO_APPLY_KEY) === "true");
applyEventFilterValues(state.eventFilters);
applyEventDensity(window.localStorage.getItem(EVENT_DENSITY_KEY) || "comfortable");
applyEventSortOrder(window.localStorage.getItem(EVENT_SORT_KEY) || "oldest");
history.replaceState(null, "", buildUrlWithEventFilters(window.location.href, state.eventFilters));
syncEventExportButtons();

const persistedUser = window.localStorage.getItem(SESSION_KEY);
if (persistedUser) {
  setSignedInUser(persistedUser);
  const deepLinkId = getDeepLinkTransferId(window.location.search);
  await Promise.allSettled([loadTransfers(), loadKycStatus()]);
  if (deepLinkId) {
    state.selectedTransferId = deepLinkId;
    renderTransferList();
    void loadTransferDetails(deepLinkId);
    startPolling(deepLinkId);
  }
} else {
  applyAuthState();
}

void loadGatewayStatus();

