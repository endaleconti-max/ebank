/**
 * Deep-link helpers for transfer selection.
 *
 * ?transfer=<transfer_id> encodes the currently selected transfer so
 * the URL can be shared and re-opened directly.
 */

export function getDeepLinkTransferId(search = window.location.search) {
  return new URLSearchParams(search).get("transfer") || null;
}

export function buildDeepLinkUrl(href, transferId) {
  const url = new URL(href);
  if (transferId) {
    url.searchParams.set("transfer", transferId);
  } else {
    url.searchParams.delete("transfer");
  }
  return url.toString();
}
