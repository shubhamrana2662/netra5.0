import { apiClient } from "./client";

export interface SystemHealth {
  status: string;
  version: string;
  environment: string;
  dependencies: {
    postgresql: string;
    chromadb: string;
    disk_free_gb: number;
    models: Record<string, boolean>;
  };
}

export interface AuditVerification {
  valid: boolean;
  total_entries: number;
  genesis_hash?: string;
  last_hash?: string;
  verified_at?: string;
  details?: Record<string, unknown>;
}

export interface Officer {
  id: string;
  username: string;
  email: string;
  full_name?: string | null;
  rank?: string | null;
  unit?: string | null;
  role: string;
  is_active: boolean;
}

export interface OfficerCreatePayload {
  username: string;
  email: string;
  password: string;
  full_name?: string;
  rank?: string;
  unit?: string;
  role?: string;
}

export const systemApi = {
  health: () => apiClient.get<SystemHealth>("/health"),
  verifyAudit: () => apiClient.get<AuditVerification>("/audit/verify"),
};

export const officersApi = {
  list: () => apiClient.get<Officer[]>("/officers"),
  create: (body: OfficerCreatePayload) => apiClient.post<Officer>("/officers", body),
};
