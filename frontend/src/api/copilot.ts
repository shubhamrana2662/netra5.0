import { apiClient } from "./client";

export interface Citation {
  rank: number;
  file: string;
  line: string;
  page: string;
  text: string;
  verified: boolean;
}

export interface RetrievedSnippet {
  id: string;
  rank: number;
  text: string;
  file: string;
  line: string;
  score: number;
}

export interface CopilotResponse {
  answer: string;
  citations: Citation[];
  retrieved_snippets?: RetrievedSnippet[];
  model_used: string;
  is_generated?: boolean;
  abstained?: boolean;
  warning?: string | null;
}

export const copilotApi = {
  ask: (caseId: string, question: string, topK = 5): Promise<CopilotResponse> =>
    apiClient.post<CopilotResponse>(`/copilot/${caseId}`, { question, top_k: topK }),

  status: () => apiClient.get<{ ollama_online: boolean; model_used: string }>("/copilot/status"),
};
