/**
 * CyberDrishti AI — Cognitive Forensic Intelligence API Client
 *
 * Frontend API layer for all 11 cognitive engine endpoints.
 * Uses the same authenticated apiClient pattern as the rest of the app.
 */
import { apiClient } from "./client";

/* ── Response Types ─────────────────────────────────────────────────────── */

export interface LedgerFinding {
  kind: string;
  row_index: number;
  expected_balance: number;
  reported_balance: number;
  discrepancy: number;
  explanation: string;
  epistemic_status: string;
}

export interface TravelFinding {
  kind: string;
  entity: string;
  location_a: string;
  location_b: string;
  distance_km: number;
  time_gap_s: number;
  velocity_kmh: number;
  explanation: string;
  epistemic_status: string;
}

export interface ContradictionsResponse {
  case_id: string;
  ledger_audit: {
    input_rows: number;
    findings: LedgerFinding[];
  };
  impossible_travel: {
    input_events: number;
    findings: TravelFinding[];
  };
}

export interface HypothesisResult {
  label: string;
  posterior: number;
  classification: string;
}

export interface HypothesesResponse {
  case_id: string;
  target_entity: string | null;
  assessment_type: string;
  ranked_labels: string[];
  display_label: string;
  hypotheses: HypothesisResult[];
  evidence_matrix: Record<string, Record<string, number>>;
  unobserved_indicators: string[];
}

export interface RankedAction {
  action: string;
  category: string;
  urgency_score: number;
  urgency_factor: number;
  time_window: string;
  instructions: string;
}

export interface NextBestActionsResponse {
  case_id: string;
  elapsed_hours: number;
  golden_hours: number;
  urgency_factor: number;
  ranked_actions: RankedAction[];
}

export interface MOMatch {
  playbook: string;
  source: string;
  similarity: number;
  alignment: Array<{
    stage: string;
    in_playbook: boolean;
    observed_position: number;
    playbook_position: number | null;
  }>;
  epistemic_status: string;
}

export interface MOFingerprintResponse {
  case_id: string;
  verdict: string;
  observed_sequence: string[];
  matches: MOMatch[];
  best_match: MOMatch | null;
  trace_evidence: Array<Record<string, unknown>>;
  note: string;
}

export interface CounterfactualResponse {
  case_id: string;
  intervention: Record<string, unknown>;
  preserved_total: number;
  assessment_type: string;
  blocked_debits: number;
  stopped_credits: number;
  completed_transfers: number;
  blocked_out_events: Array<Record<string, unknown>>;
  stopped_in_events: Array<Record<string, unknown>>;
}

export interface ReplayFrame {
  t_start: string;
  t_end: string;
  nodes: string[];
  edges: Array<{ u: string; v: string; w: number; event_type: string }>;
  summary: Record<string, unknown>;
}

export interface NetworkReplayResponse {
  case_id: string;
  total_events: number;
  total_frames: number;
  frames: ReplayFrame[];
}

export interface CrossCaseCollision {
  entity_type: string;
  blind_token: string;
  cases: string[];
  degree_sum: number;
}

export interface CrossCaseResponse {
  total_entities_indexed: number;
  total_collisions: number;
  collisions: CrossCaseCollision[];
  note: string;
}

export interface VerificationFlag {
  check: string;
  severity: string;
  message: string;
}

export interface VerifyDraftResponse {
  passed: boolean;
  flags: VerificationFlag[];
  checked_items: number;
  summary: string;
}

export interface BenchmarkCase {
  case_id: string;
  db_case_id?: string;
  typology: string;
  entities_count: number;
  flow_edges_count: number;
  hidden_links_count: number;
  artifacts: Record<string, string>;
  ground_truth: Record<string, unknown>;
}

/* ── API Functions ─────────────────────────────────────────────────────── */

export const cognitiveApi = {
  /** Feature 02: Contradictions — ledger audit + impossible travel */
  contradictions: (caseId: string) =>
    apiClient.get<ContradictionsResponse>(`/cognitive/cases/${caseId}/contradictions`),

  /** Feature 04+05: Hypotheses — ACH suspect role classification */
  hypotheses: (caseId: string, targetEntity?: string) => {
    const q = targetEntity ? `?target_entity=${encodeURIComponent(targetEntity)}` : "";
    return apiClient.get<HypothesesResponse>(`/cognitive/cases/${caseId}/hypotheses${q}`);
  },

  /** Feature 06: Next-Best Actions — Golden-Hours VoI urgency */
  nextBestActions: (caseId: string) =>
    apiClient.get<NextBestActionsResponse>(`/cognitive/cases/${caseId}/next-best-actions`),

  /** Feature 07: MO Fingerprint — crime script playbook matching */
  moFingerprint: (caseId: string) =>
    apiClient.get<MOFingerprintResponse>(`/cognitive/cases/${caseId}/mo-fingerprint`),

  /** Feature 08: Counterfactual Freeze — what-if simulation */
  counterfactualFreeze: (caseId: string, freezeAccount: string, freezeTime: string) =>
    apiClient.post<CounterfactualResponse>(`/cognitive/cases/${caseId}/counterfactual-freeze`, {
      freeze_account: freezeAccount,
      freeze_time: freezeTime,
    }),

  /** Feature 10: Network Replay — CTDG animation frames */
  networkReplay: (caseId: string, stepSeconds = 300, tauSeconds = 1800) =>
    apiClient.get<NetworkReplayResponse>(
      `/cognitive/cases/${caseId}/network-replay?step_seconds=${stepSeconds}&tau_seconds=${tauSeconds}`
    ),

  /** Feature 03: Cross-Case Collisions — zero-knowledge blind index */
  crossCaseCollisions: () =>
    apiClient.get<CrossCaseResponse>(`/cognitive/cross-case/collisions`),

  /** Feature 09: Verify Draft — deterministic output verifier */
  verifyDraft: (draftText: string, caseId?: string) =>
    apiClient.post<VerifyDraftResponse>(`/cognitive/verify-draft`, {
      draft_text: draftText,
      case_id: caseId,
    }),

  /** Feature 11: Benchmark Generator — synthetic test case */
  generateBenchmark: (typology = "DIGITAL_ARREST", seed = 42) =>
    apiClient.post<BenchmarkCase>(`/cognitive/benchmark/generate`, { typology, seed }),
};
