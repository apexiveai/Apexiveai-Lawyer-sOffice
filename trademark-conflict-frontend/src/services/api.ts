export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

import { getAccessToken } from "./auth";

export async function apiFetch(
  input: RequestInfo | URL,
  init: RequestInit = {},
): Promise<Response> {
  const token = await getAccessToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(input, { ...init, headers });
}

export type AnalysisSummary = {

  job_id: string;

  left_file_type?: "pdf" | "xlsx";

  right_file_type?: "pdf" | "xlsx";

  pdf_pages: number;

  client_records: number;

  pdf_logos: number;

  xlsx_logos: number;

  application_matches: number;

  logo_matches: number;

  matches: MatchRecord[];

};

export type MatchRecord = Record<string, unknown>;

export type AnalysisJobStatus = {
  job_id: string;
  status: "UPLOADED" | "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED";
  progress: number;
  message: string;
  attempts: number;
  error?: string | null;
};

export async function getAnalysisStatus(
  jobId: string,
): Promise<AnalysisJobStatus> {
  const response = await apiFetch(
    `${API_BASE_URL}/api/analysis/${encodeURIComponent(jobId)}/status`,
  );
  if (!response.ok) {
    throw new Error(`Analysis status failed (${response.status}): ${await response.text()}`);
  }
  return response.json();
}

export async function waitForAnalysis(
  jobId: string,
  onProgress?: (status: AnalysisJobStatus) => void,
): Promise<AnalysisSummary> {
  const deadline = Date.now() + 60 * 60 * 1000;
  while (Date.now() < deadline) {
    const status = await getAnalysisStatus(jobId);
    onProgress?.(status);
    if (status.status === "COMPLETED") return getResults(jobId);
    if (status.status === "FAILED") {
      throw new Error(status.error || status.message || "Analysis failed.");
    }
    await new Promise((resolve) => window.setTimeout(resolve, 1000));
  }
  throw new Error("Analysis timed out while waiting for the worker.");
}

export async function uploadTwoFiles(

  pdfFile: File,

  clientFile: File,
  metadata: {
    jurisdiction?: string;
    niceClasses?: string;
    leftJurisdiction?: string;
    rightJurisdiction?: string;
    leftNiceClasses?: string;
    rightNiceClasses?: string;
    leftGoodsServices?: string;
    rightGoodsServices?: string;
    sourceName?: string;
    sourceUrl?: string;
    sourceRetrievedAt?: string;
  } = {},

): Promise<{ job_id: string; pdf: string; xlsx?: string; client_pdf?: string; status: string }> {

  const formData = new FormData();

  const firstIsXlsx = pdfFile.name.toLowerCase().endsWith(".xlsx");
  formData.append(firstIsXlsx ? "left_xlsx" : "pdf", pdfFile);

  formData.append(
    firstIsXlsx
      ? "right_xlsx"
      : clientFile.name.toLowerCase().endsWith(".pdf")
      ? "client_pdf"
      : "xlsx",
    clientFile
  );
  if (metadata.jurisdiction) formData.append("jurisdiction", metadata.jurisdiction);
  if (metadata.niceClasses) formData.append("nice_classes", metadata.niceClasses);
  if (metadata.leftJurisdiction) {
    formData.append("left_jurisdiction", metadata.leftJurisdiction);
  }
  if (metadata.rightJurisdiction) {
    formData.append("right_jurisdiction", metadata.rightJurisdiction);
  }
  if (metadata.leftNiceClasses) {
    formData.append("left_nice_classes", metadata.leftNiceClasses);
  }
  if (metadata.rightNiceClasses) {
    formData.append("right_nice_classes", metadata.rightNiceClasses);
  }
  if (metadata.leftGoodsServices) {
    formData.append("left_goods_services", metadata.leftGoodsServices);
  }
  if (metadata.rightGoodsServices) {
    formData.append("right_goods_services", metadata.rightGoodsServices);
  }
  if (metadata.sourceName) formData.append("source_name", metadata.sourceName);
  if (metadata.sourceUrl) formData.append("source_url", metadata.sourceUrl);
  if (metadata.sourceRetrievedAt) {
    formData.append("source_retrieved_at", metadata.sourceRetrievedAt);
  }

  const response = await apiFetch(

    `${API_BASE_URL}/api/upload/two-files`,

    {

      method: "POST",

      body: formData,

    }

  );

  if (!response.ok) {

    const text = await response.text();

    throw new Error(

      `Upload failed (${response.status}): ${text}`

    );

  }

  return response.json();

}

export async function analyzeJob(

  jobId: string

): Promise<AnalysisJobStatus> {

  const response = await apiFetch(

    `${API_BASE_URL}/api/analysis/${encodeURIComponent(jobId)}`,

    {

      method: "POST",

    }

  );

  if (!response.ok) {

    const text = await response.text();

    throw new Error(

      `Analysis failed (${response.status}): ${text}`

    );

  }

  return response.json();

}

export async function getResults(

  jobId: string

): Promise<AnalysisSummary> {

  const response = await apiFetch(

    `${API_BASE_URL}/api/results/${encodeURIComponent(jobId)}`
  );

  if (!response.ok) {

    const text = await response.text();

    throw new Error(

      `Results request failed (${response.status}): ${text}`

    );

  }

  return response.json();

}

export type ReviewStatus =

  | "PENDING"

  | "CONFIRMED"

  | "REJECTED";

export type ReviewRecord = {

  id: number;

  job_id: string;

  conflict_id: string;

  status: ReviewStatus;

  comment: string;

  reviewer: string;

  reviewed_at: string;

  created_at: string;

};

export async function saveReview(

  jobId: string,

  conflictId: string,

  status: ReviewStatus,

  comment: string,

  reviewer = "Admin"

): Promise<ReviewRecord> {

  const response = await apiFetch(

    `${API_BASE_URL}/api/reviews`,

    {

      method: "POST",

      headers: {

        "Content-Type": "application/json",

      },

      body: JSON.stringify({

        job_id: jobId,

        conflict_id: conflictId,

        status,

        comment,

        reviewer,

      }),

    }

  );

  if (!response.ok) {

    const text = await response.text();

    throw new Error(

      `Review save failed (${response.status}): ${text}`

    );

  }

  return response.json();

}

export async function getReviews(

  jobId: string

): Promise<ReviewRecord[]> {

  const response = await apiFetch(

    `${API_BASE_URL}/api/reviews/${encodeURIComponent(jobId)}`

  );

  if (!response.ok) {

    const text = await response.text();

    throw new Error(

      `Reviews request failed (${response.status}): ${text}`

    );

  }

  return response.json();

}

export type ReportResponse = {

  status: string;

  job_id: string;

  filename: string;

  download_url: string;

};

export async function generateConflictReport(

  jobId: string

): Promise<ReportResponse> {

  const response = await apiFetch(

    `${API_BASE_URL}/api/reports/${encodeURIComponent(jobId)}`,

    {

      method: "POST",

    }

  );

  if (!response.ok) {

    const text = await response.text();

    throw new Error(

      `Report generation failed (${response.status}): ${text}`

    );

  }

  return response.json();

}

export function getConflictReportUrl(

  jobId: string

): string {

  return (

    `${API_BASE_URL}/api/reports/` +

    `${encodeURIComponent(jobId)}/download`

  );

}

export async function downloadConflictReport(jobId: string): Promise<void> {
  const response = await apiFetch(getConflictReportUrl(jobId));
  if (!response.ok) {
    throw new Error(`Report download failed (${response.status}): ${await response.text()}`);
  }
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = `Trademark_Conflict_${jobId}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

export type ReportHistoryRecord = {

  id: number;

  job_id: string;

  filename: string;

  report_type: string;

  created_at: string;

  download_url: string;

};

export async function getReportHistory(

  jobId: string

): Promise<ReportHistoryRecord[]> {

  const response = await apiFetch(

    `${API_BASE_URL}/api/reports/` +

      `${encodeURIComponent(jobId)}/history`

  );

  if (!response.ok) {

    const text = await response.text();

    throw new Error(

      `Report history request failed (${response.status}): ${text}`

    );

  }

  return response.json();

}