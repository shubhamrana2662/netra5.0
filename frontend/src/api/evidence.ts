import { apiClient } from "./client";

export interface BackendEvidenceFile {
  id: string;
  case_id: string;
  original_name: string;
  file_type?: string;
  source_type?: string;
  sha256_hash: string;
  upload_status: "pending" | "processing" | "processed" | "failed";
  storage_path?: string;
  file_size?: number;
  uploaded_at: string;
  processed_at?: string;
  parse_error?: string;
  metadata?: Record<string, unknown>;
}

export interface EvidenceListResponse {
  case_id: string;
  count: number;
  files: BackendEvidenceFile[];
}

export interface EvidenceUploadResponse {
  message: string;
  uploaded: Array<{
    id: string;
    filename: string;
    sha256_hash: string;
    status: string;
  }>;
  duplicates?: Array<{
    id: string;
    filename: string;
    sha256_hash: string;
  }>;
}

export const evidenceApi = {
  list: async (caseId: string): Promise<BackendEvidenceFile[]> => {
    const res = await apiClient.get<EvidenceListResponse | BackendEvidenceFile[]>(`/evidence/${caseId}`);
    if (Array.isArray(res)) return res;
    return res.files || [];
  },

  upload: async (caseId: string, files: File[], sourceType = "unknown"): Promise<EvidenceUploadResponse> => {
    const fd = new FormData();
    fd.append("case_id", caseId);
    fd.append("source_type", sourceType);
    files.forEach((f) => fd.append("files", f));
    return apiClient.postForm<EvidenceUploadResponse>("/evidence/upload", fd);
  },
};
