import { buildDeepLinkUrl } from "./deepLink.js";

export function buildTransferDetailActionPayload(transfer, currentHref) {
  const shareUrl = buildDeepLinkUrl(currentHref, transfer.transfer_id);
  return {
    transferIdText: transfer.transfer_id,
    recipientText: transfer.recipient_phone_e164,
    shareUrl,
    shareTitle: `Transfer ${transfer.transfer_id}`,
    shareText: `${transfer.sender_user_id} -> ${transfer.recipient_phone_e164} • ${transfer.status}`,
  };
}