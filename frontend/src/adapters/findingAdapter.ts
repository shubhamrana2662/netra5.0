import type { Finding } from "../data/types";

export interface BackendFinding {
  id: string;
  title: string;
  description: string;
  confidence: number;
  finding_type: string;
  risk_level: string;
  related_entities?: string[];
}

export function adaptFinding(f: BackendFinding, index = 0): Finding {
  const pct = Math.round((f.confidence > 1 ? f.confidence : f.confidence * 100));
  return {
    id: f.id || `fnd-${index}`,
    title: f.title || "Autonomous Correlation Finding",
    when: "Automated analysis",
    confidence: `${pct}% CONFIDENCE · ${f.risk_level || "MEDIUM"} RISK`,
    body: f.description || "Topological and behavioral correlation detected across indexed evidence records.",
    evidenceIds: f.related_entities || [],
    scope: f.finding_type ? f.finding_type.replace(/_/g, " ") : "Analytical Finding",
  };
}
