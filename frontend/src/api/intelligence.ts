import { apiClient } from "./client";

export interface CrossMatchItem {
  case_id: string;
  case_number: string;
  case_title: string;
  crime_type: string | null;
  priority: string;
  status: string;
  entity_value: string;
  entity_type: string;
  first_seen: string | null;
  last_seen: string | null;
  mention_count: number;
}

export interface CrossMatchResponse {
  query: string;
  normalized_query: string;
  total_matches: number;
  matches: CrossMatchItem[];
}

export interface SyndicateCaseItem {
  case_id: string;
  case_number: string;
  case_title: string;
  crime_type: string | null;
  priority: string;
  status: string;
}

export interface SyndicateEntity {
  canonical_value: string;
  entity_type: string;
  case_count: number;
  cases: SyndicateCaseItem[];
}

export interface SyndicateListResponse {
  total_syndicates: number;
  syndicates: SyndicateEntity[];
}

export const intelApi = {
  crossMatch: (query?: string): Promise<CrossMatchResponse> => {
    const q = query ? `?query=${encodeURIComponent(query)}` : "";
    return apiClient.get<CrossMatchResponse>(`/intel/cross-match${q}`);
  },

  syndicates: (limit = 50): Promise<SyndicateListResponse> =>
    apiClient.get<SyndicateListResponse>(`/intel/syndicates?limit=${limit}`),

  events: () => apiClient.get<unknown[]>("/events"),

  correlations: (caseId: string) => apiClient.get<unknown>(`/correlations/${caseId}`),
};
