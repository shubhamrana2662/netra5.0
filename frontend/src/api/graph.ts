import { apiClient } from "./client";

export interface BackendGraphNode {
  id: string;
  entity_type: string;
  label: string;
  mention_count: number;
  degree_centrality: number;
  community_id?: number | null;
  bridge_score: number;
  is_prominent?: boolean;
  evidence_sources?: Array<{
    event_type: string;
    text_content: string;
    source_line?: number | null;
    source_page?: number | null;
    event_metadata?: Record<string, unknown>;
  }>;
}

export interface BackendGraphEdge {
  source: string;
  target: string;
  edge_type: string;
  weight: number;
  score?: number;
  component_scores?: Record<string, number>;
}

export interface BackendGraphData {
  nodes: BackendGraphNode[];
  edges: BackendGraphEdge[];
  hidden_edges?: BackendGraphEdge[];
}

export interface BackendTimelineEvent {
  id: string;
  timestamp: string | null;
  event_type: string;
  text: string;
  text_content?: string;
  source_doc?: string | null;
  source_line?: number | null;
  source_page?: number | null;
  metadata?: Record<string, unknown>;
}

export interface TimelineResponse {
  events: BackendTimelineEvent[];
}

export const graphApi = {
  get: (caseId: string, twoHop = false): Promise<BackendGraphData> =>
    apiClient.get<BackendGraphData>(`/graph/${caseId}${twoHop ? "?two_hop=true" : ""}`),

  timeline: async (caseId: string): Promise<BackendTimelineEvent[]> => {
    const res = await apiClient.get<TimelineResponse | BackendTimelineEvent[]>(`/timeline/${caseId}`);
    if (Array.isArray(res)) return res;
    return res.events || [];
  },

  query: (caseId: string, question: string) =>
    apiClient.post(`/query/${caseId}`, { question }),
};
