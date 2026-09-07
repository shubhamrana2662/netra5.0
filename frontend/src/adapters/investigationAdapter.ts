import type { BackendCaseItem, BackendCaseSummary } from "../api/cases";
import type { Case, Priority, CaseStatus } from "../data/types";

function formatRelativeTime(dateStr: string): string {
  try {
    const diffMs = Date.now() - new Date(dateStr).getTime();
    if (diffMs < 0) return "Just now";
    const mins = Math.floor(diffMs / 60000);
    if (mins < 1) return "Just now";
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days === 1) return "Yesterday";
    if (days < 30) return `${days}d ago`;
    return new Date(dateStr).toLocaleDateString();
  } catch {
    return dateStr || "Recently";
  }
}

function normalizePriority(p?: string | null): Priority {
  if (!p) return null;
  const upper = p.toUpperCase();
  if (upper.includes("CRIT")) return "CRITICAL";
  if (upper.includes("HIGH")) return "HIGH";
  if (upper.includes("MED")) return "MEDIUM";
  return null;
}

function normalizeStatus(s?: string | null): CaseStatus {
  if (!s) return "ACTIVE";
  const lower = s.toLowerCase();
  if (lower === "archived" || lower === "closed" || lower === "resolved") return "ARCHIVED";
  if (lower === "new" || lower === "draft") return "NEW";
  return "ACTIVE";
}

export function adaptCaseItem(b: BackendCaseItem, summary?: BackendCaseSummary | null): Case {
  const counts = summary?.counts;
  const entities = counts?.entities ?? (b.tags && b.tags.length > 0 ? b.tags.length * 3 : 0);
  const evidence = counts?.evidence ?? 0;
  const leads = counts?.suspicious_findings ?? (counts?.connections ? Math.floor(counts.connections / 3) : 0);

  return {
    id: b.case_number || b.id,
    uuid: b.id,
    case_number: b.case_number,
    name: b.title || `Case ${b.case_number || b.id.slice(0, 8)}`,
    domain: b.crime_type || (b.fir_number ? `FIR ${b.fir_number}` : "Cyber Investigation"),
    entities,
    evidence,
    leads,
    priority: normalizePriority(b.priority),
    status: normalizeStatus(b.status),
    updated: formatRelativeTime(b.updated_at || b.created_at),
    brief: b.description || `Active investigation registered at ${b.police_station || "Cyber Crime Cell"}.`,
    latest: summary?.findings?.[0]?.description || (b.fir_number ? `Registered under FIR #${b.fir_number}` : "Under active evidence analysis"),
    user: false,
  };
}
