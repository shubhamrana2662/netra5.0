import type { CaseEvent } from "./types";
import { ANCHOR_TIMESTAMP, landingThread } from "./thread";

export const events: CaseEvent[] = [
  {
    id: landingThread.anchorEventId,
    date: "Sep 03",
    ts: ANCHOR_TIMESTAMP,
    kind: "COMMUNICATION",
    label: "First communication signal recorded from Device A83F-29",
    entityIds: [landingThread.deviceId],
    evidenceIds: ["evd-cdr-18"],
  },
  {
    id: "evt-094520",
    date: "Sep 03",
    ts: "09:45:20",
    kind: "LOCATION",
    label: "Base station tower check-in — Sector 4 Jamtara Tower 4471",
    entityIds: [landingThread.deviceId],
    evidenceIds: ["evd-dev-meta-29"],
  },
  {
    id: "evt-095613",
    date: "Sep 03",
    ts: "09:56:13",
    kind: "TRANSACTION",
    label: "₹45,000 transfer initiated through Account ••4821",
    entityIds: ["ent-account-4821"],
    evidenceIds: ["evd-txn-45000"],
  },
  {
    id: "evt-100200",
    date: "Sep 03",
    ts: "10:02:00",
    kind: "TRANSACTION",
    label: "Layering split: ₹24,000 diverted to Account #72 (Mule Alpha)",
    entityIds: ["ent-account-72"],
    evidenceIds: ["evd-bank-stmt"],
  },
  {
    id: "evt-101445",
    date: "Sep 03",
    ts: "10:14:45",
    kind: "COMMUNICATION",
    label: "Encrypted handshake with external C2 proxy sbi-rewardspay-update.in",
    entityIds: ["ent-org-c2"],
    evidenceIds: ["evd-annx-01"],
  },
  {
    id: "evt-103010",
    date: "Sep 03",
    ts: "10:30:10",
    kind: "TRANSACTION",
    label: "Crypto escrow off-ramp conversion to USDT WazirX Escrow #892104",
    entityIds: ["ent-account-crypto"],
    evidenceIds: ["evd-txn-45000"],
  },
];
