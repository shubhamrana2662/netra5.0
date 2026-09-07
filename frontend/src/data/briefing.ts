import type { Case } from "./types";
import { cases } from "./cases";
import { connections, findings } from "./corpus";
import { landingThread, ANCHOR_TIMESTAMP } from "./thread";

export interface BriefStat { value: number; label: string; }
export const briefingStats: BriefStat[] = [
  { value: findings.length, label: "New signals" },
  { value: connections.filter(c => c.confidence >= 90).length, label: "Priority escalation" },
  { value: cases.reduce((n, c) => n + c.evidence, 0), label: "Evidence indexed" },
];

export interface PriorityBlock {
  caseId: string; name: string; summary: string; updated: string; priority: Case["priority"];
}
export function priorityBlocks(): PriorityBlock[] {
  return cases.map(c => ({
    caseId: c.id,
    name: c.name,
    summary: c.id === landingThread.caseId
      ? `New connection in the ${ANCHOR_TIMESTAMP} chain — Entity #04 linked to Account #72.`
      : c.latest || "No developments recorded yet.",
    updated: c.updated,
    priority: c.priority,
  }));
}

export interface FeedEntry { id: string; time: string; text: string; to: string; }
export function intelligenceFeed(): FeedEntry[] {
  return [
    { id: "fd-01", time: "09:56", text: "New connection detected between Device A83F-29 and Account ••4821", to: `/investigations/${landingThread.caseId}/overview` },
    { id: "fd-02", time: "09:42", text: "First communication recorded on Device A83F-29", to: `/investigations/${landingThread.caseId}/evidence` },
    { id: "fd-03", time: "Yesterday", text: "Cross-network correlation completed · 94% confidence", to: "/intelligence" },
    { id: "fd-04", time: "2 days ago", text: "Bank transaction cluster updated", to: "/investigations/CYB-2026-018/overview" },
  ];
}
