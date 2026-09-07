/**
 * CyberDrishti AI — Threat constellation dataset
 * Maps the static knowledge graph into spatial evidence nodes shared by the
 * 3D world (SceneRoot) and the forensic inspector UI.
 */

import { KNOWLEDGE_NODES, KNOWLEDGE_EDGES, type Severity } from "@/data/intel";
import type { EvidenceNode, EvidenceEdge } from "@/state/scene";

const severityMap: Record<Severity, EvidenceNode["severity"]> = {
  critical: "critical",
  high: "suspicious",
  medium: "suspicious",
  low: "info",
  info: "info",
};

export const THREAT_NODES: EvidenceNode[] = KNOWLEDGE_NODES.map((n, i) => ({
  id: n.id,
  kind: n.kind,
  label: n.label,
  severity: severityMap[n.severity],
  score:
    n.severity === "critical"
      ? 86 + ((i * 7) % 12)
      : n.severity === "high"
        ? 68 + ((i * 5) % 14)
        : n.severity === "medium"
          ? 44 + ((i * 11) % 16)
          : 12 + ((i * 3) % 18),
  firstSeen: 0,
  related: 3 + (i % 5),
  detail:
    n.kind === "actor"
      ? "Tracked threat actor cluster"
      : n.kind === "malware"
        ? "Known malware family signature"
        : n.kind === "campaign"
          ? "Coordinated intrusion campaign"
          : n.kind === "cve"
            ? "Exploited vulnerability chain"
            : "Monitored sector target",
}));

const severityOf = (id: string) =>
  severityMap[KNOWLEDGE_NODES.find((n) => n.id === id)?.severity ?? "info"];

export const THREAT_EDGES: EvidenceEdge[] = KNOWLEDGE_EDGES.map(([a, b]) => ({
  source: a,
  target: b,
  weight: 1,
  suspicious: severityOf(a) === "critical" || severityOf(b) === "critical",
}));
