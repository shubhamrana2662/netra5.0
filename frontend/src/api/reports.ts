import { apiClient } from "./client";

export const reportsApi = {
  downloadPdf: async (caseId: string, caseNumber = "case"): Promise<void> => {
    const blob = await apiClient.getBlob(`/report/${caseId}`);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `65B_Certificate_${caseNumber}.pdf`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },
};
