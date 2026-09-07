import type { Finding } from "./types";
import { ANCHOR_TIMESTAMP } from "./thread";

export const findings: Finding[] = [
  {
    id: "fnd-01",
    title: "Cross-network correlation",
    when: "Yesterday",
    confidence: "94%",
    body: `A recurring relationship exists between three financial accounts and two communication devices. The sequence begins with the ${ANCHOR_TIMESTAMP} communication from Device A83F; a ₹45,000 transfer through Account ••4821 follows within fourteen minutes.`,
    evidenceIds: ["evd-txn-45000", "evd-cdr-18", "evd-dev-meta-29"],
    scope: "CYB-2026-042 · Operation Shadowlink",
  },
  {
    id: "fnd-02",
    title: "Financial anomaly detection",
    when: "2 days ago",
    confidence: "81%",
    body: "Two transaction clusters share timing signatures across otherwise unrelated accounts. Both initiate within three minutes of device check-ins registered to the same base station.",
    evidenceIds: ["evd-txn-45000", "evd-bank-stmt"],
    scope: "Cross-investigation financial cluster",
  },
  {
    id: "fnd-03",
    title: "Communication cluster analysis",
    when: "4 days ago",
    confidence: "76%",
    body: "Communication activity resolves into two clusters. Cluster B correlates with transaction timestamps at a rate that excludes coincidence.",
    evidenceIds: ["evd-cdr-18", "evd-cdr-04"],
    scope: "Cell tower telemetry analysis",
  },
];
