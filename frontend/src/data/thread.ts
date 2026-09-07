/**
 * Amendment A — the landing thread IS Case CYB-2026-042.
 * 09:42:13 is the anchor event (first communication). Device A83F is an
 * artifact of that event. The ₹45,000 transfer occurs 14 minutes later.
 */
export const ANCHOR_TIMESTAMP = "09:42:13";

export const landingThread = {
  caseId: "CYB-2026-042",
  anchorEventId: "evt-094213",
  deviceId: "ent-device-a83f",
  transactionEvidenceId: "evd-txn-45000",
} as const;
