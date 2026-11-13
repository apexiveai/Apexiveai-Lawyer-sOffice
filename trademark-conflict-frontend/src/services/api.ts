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

  left_file_type?: UploadedFileType;

  right_file_type?: UploadedFileType;

  pdf_pages: number;

  client_records: number;

  pdf_logos: number;

  xlsx_logos: number;

  application_matches: number;

  logo_matches: number;

  matches: MatchRecord[];

};

export type UploadedFileType =
  | "pdf"
  | "xlsx"
  | "svg"
  | "jpg"
  | "jpeg"
  | "png"
  | "webp"
  | "bmp"
  | "tif"
  | "tiff"
  | "gif";

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

  firstFile: File,

  secondFile: File,
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

): Promise<{
  job_id: string;
<<<<<<< HEAD
  pdf: string | null;
  xlsx: string | null;
  client_pdf: string | null;
  left_xlsx: string | null;
  right_xlsx: string | null;
=======
  left_file?: string;
  right_file?: string;
>>>>>>> f850024 (final deployment commit-v1)
  status: string;
}> {

  const formData = new FormData();

<<<<<<< HEAD
  const fileType = (file: File): "pdf" | "xlsx" => {
    const extension = file.name.toLowerCase().split(".").pop();
    if (extension === "pdf" || extension === "xlsx") return extension;
    throw new Error(`Unsupported file type: ${file.name}. Choose a PDF or XLSX file.`);
  };
  const firstType = fileType(firstFile);
  const secondType = fileType(secondFile);
  const reverseMixedPair = firstType === "xlsx" && secondType === "pdf";

  if (firstType === "xlsx" && secondType === "xlsx") {
    formData.append("left_xlsx", firstFile);
    formData.append("right_xlsx", secondFile);
  } else if (reverseMixedPair) {
    formData.append("pdf", secondFile);
    formData.append("xlsx", firstFile);
  } else {
    formData.append("pdf", firstFile);
    formData.append(
      secondType === "pdf" ? "client_pdf" : "xlsx",
      secondFile,
    );
=======
  formData.append("left_file", pdfFile);
  formData.append("right_file", clientFile);
  if (metadata.jurisdiction) formData.append("jurisdiction", metadata.jurisdiction);
  if (metadata.niceClasses) formData.append("nice_classes", metadata.niceClasses);
  if (metadata.leftJurisdiction) {
    formData.append("left_jurisdiction", metadata.leftJurisdiction);
>>>>>>> f850024 (final deployment commit-v1)
  }

  const analysisMetadata = reverseMixedPair
    ? {
        ...metadata,
        leftJurisdiction: metadata.rightJurisdiction,
        rightJurisdiction: metadata.leftJurisdiction,
        leftNiceClasses: metadata.rightNiceClasses,
        rightNiceClasses: metadata.leftNiceClasses,
        leftGoodsServices: metadata.rightGoodsServices,
        rightGoodsServices: metadata.leftGoodsServices,
      }
    : metadata;

  if (analysisMetadata.jurisdiction) {
    formData.append("jurisdiction", analysisMetadata.jurisdiction);
  }
  if (analysisMetadata.niceClasses) {
    formData.append("nice_classes", analysisMetadata.niceClasses);
  }
  if (analysisMetadata.leftJurisdiction) {
    formData.append("left_jurisdiction", analysisMetadata.leftJurisdiction);
  }
  if (analysisMetadata.rightJurisdiction) {
    formData.append("right_jurisdiction", analysisMetadata.rightJurisdiction);
  }
  if (analysisMetadata.leftNiceClasses) {
    formData.append("left_nice_classes", analysisMetadata.leftNiceClasses);
  }
  if (analysisMetadata.rightNiceClasses) {
    formData.append("right_nice_classes", analysisMetadata.rightNiceClasses);
  }
  if (analysisMetadata.leftGoodsServices) {
    formData.append("left_goods_services", analysisMetadata.leftGoodsServices);
  }
  if (analysisMetadata.rightGoodsServices) {
    formData.append("right_goods_services", analysisMetadata.rightGoodsServices);
  }
  if (analysisMetadata.sourceName) {
    formData.append("source_name", analysisMetadata.sourceName);
  }
  if (analysisMetadata.sourceUrl) {
    formData.append("source_url", analysisMetadata.sourceUrl);
  }
  if (analysisMetadata.sourceRetrievedAt) {
    formData.append("source_retrieved_at", analysisMetadata.sourceRetrievedAt);
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