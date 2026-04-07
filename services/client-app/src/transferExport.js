function escapeCsvValue(value) {
  const stringValue = value == null ? "" : String(value);
  if (!/[",\n]/.test(stringValue)) {
    return stringValue;
  }
  return `"${stringValue.replace(/"/g, '""')}"`;
}

export function buildTransfersCsv(transfers) {
  const header = [
    "transfer_id",
    "status",
    "sender_user_id",
    "recipient_phone_e164",
    "currency",
    "amount_minor",
    "note",
    "failure_reason",
    "connector_external_ref",
    "created_at",
    "updated_at",
  ];

  const rows = transfers.map((transfer) => [
    transfer.transfer_id,
    transfer.status,
    transfer.sender_user_id,
    transfer.recipient_phone_e164,
    transfer.currency,
    transfer.amount_minor,
    transfer.note,
    transfer.failure_reason,
    transfer.connector_external_ref,
    transfer.created_at,
    transfer.updated_at,
  ]);

  return [header, ...rows]
    .map((row) => row.map(escapeCsvValue).join(","))
    .join("\n");
}