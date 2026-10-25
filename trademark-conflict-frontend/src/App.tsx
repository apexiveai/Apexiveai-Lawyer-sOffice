import LogoMatchCard from "./components/LogoMatchCard";
import {

  useEffect,

  useState,

  type DragEvent,

  type ReactNode,

} from "react";

import {

  Scale,

  Upload,

  FileText,

  FileSpreadsheet,

  ShieldCheck,

  Search,

  X,

  CheckCircle2,

  ChevronRight,

  Image as ImageIcon,

  AlertTriangle,

  RefreshCw,

} from "lucide-react";

import "./App.css";
import AIAssistant from "./components/AIAssistant";

import {

  uploadTwoFiles,

  analyzeJob,

  getResults,

  saveReview as saveReviewApi,
  getReviews,

  generateConflictReport,
  downloadConflictReport,
  getReportHistory,
  waitForAnalysis,
  type AnalysisJobStatus,

  type ReviewRecord,
  type ReviewStatus,
  type AnalysisSummary,
  type MatchRecord,
  type ReportHistoryRecord
} from "./services/api";
import {
  getCurrentUser,
  oidcEnabled,
  signIn,
  signOut,
} from "./services/auth";
import type { User } from "oidc-client-ts";

type FileBoxProps = {

  title: string;

  subtitle: string;

  accept: string;

  file: File | null;

  onFile: (file: File) => void;

  onRemove: () => void;

  icon: ReactNode;

};

function FileBox({

  title,

  subtitle,

  accept,

  file,

  onFile,

  onRemove,

  icon,

}: FileBoxProps) {

  const [dragging, setDragging] = useState(false);

  const handleDrop = (event: DragEvent<HTMLLabelElement>) => {

    event.preventDefault();

    setDragging(false);

    const droppedFile = event.dataTransfer.files?.[0];

    if (droppedFile) {

      onFile(droppedFile);

    }

  };

  return (

    <label

      className={`upload-box ${dragging ? "dragging" : ""} ${file ? "has-file" : ""

        }`}

      onDragOver={(event) => {

        event.preventDefault();

        setDragging(true);

      }}

      onDragLeave={() => setDragging(false)}

      onDrop={handleDrop}

    >

      <input

        type="file"

        accept={accept}

        hidden

        onChange={(event) => {

          const selected = event.target.files?.[0];

          if (selected) {

            onFile(selected);

          }

          event.target.value = "";

        }}

      />

      <div className="upload-icon">{icon}</div>

      {!file ? (

        <>

          <div className="upload-title">{title}</div>

          <div className="upload-subtitle">{subtitle}</div>

          <div className="upload-action">

            <Upload size={15} />

            Choose File

          </div>

          <div className="upload-format">{accept}</div>

        </>

      ) : (

        <div className="selected-file">

          <div className="selected-file-main">

            <div className="file-check">

              <CheckCircle2 size={18} />

            </div>

            <div className="file-info">

              <strong>{file.name}</strong>

              <span>{formatFileSize(file.size)}</span>

            </div>

          </div>

          <button

            type="button"

            className="remove-file"

            onClick={(event) => {

              event.preventDefault();

              event.stopPropagation();

              onRemove();

            }}

          >

            <X size={17} />

          </button>

        </div>

      )}

    </label>

  );

}

function formatFileSize(size: number) {

  if (size < 1024) {

    return `${size} B`;

  }

  if (size < 1024 * 1024) {

    return `${(size / 1024).toFixed(1)} KB`;

  }

  return `${(size / (1024 * 1024)).toFixed(1)} MB`;

}

function MetricCard({

  label,

  value,

  icon,

  accent = false,

}: {

  label: string;

  value: string | number;

  icon: ReactNode;

  accent?: boolean;

}) {

  return (

    <div className={`metric-card ${accent ? "accent" : ""}`}>

      <div className="metric-icon">{icon}</div>

      <div className="metric-content">

        <span>{label}</span>

        <strong>{value}</strong>

      </div>

    </div>

  );

}

type MatchReviewSaved = (conflictId: string, review: ReviewRecord) => void;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function getMatchValue(

  match: MatchRecord,

  keys: string[],

  fallback = "—"

): string {

  for (const key of keys) {

    const value = match[key];

    if (

      value !== undefined &&

      value !== null &&

      String(value).trim() !== ""

    ) {

      return String(value);

    }

  }

  return fallback;

}

function getMatchNumber(

  match: MatchRecord,

  keys: string[]

): number | null {

  for (const key of keys) {

    const value = match[key];

    if (typeof value === "number" && Number.isFinite(value)) {

      return value;

    }

    if (

      typeof value === "string" &&

      value.trim() !== "" &&

      Number.isFinite(Number(value))

    ) {
      return Number(value);

    }

  }

  return null;

}

function getEvidenceUrl(
  jobId: string | undefined,
  evidence: Record<string, unknown> | string | null | undefined
): string | null {
  if (!jobId || !evidence) {
    return null;
  }

  const rawPath =
    typeof evidence === "string"
      ? evidence
      : evidence.image_path ||
      evidence.path ||
      evidence.file_path ||
      evidence.filename ||
      evidence.url;

  if (!rawPath) {

    return null;

  }

  const normalized = String(rawPath).replace(/\\/g, "/");
  if (normalized.startsWith("/evidence/")) return normalized;
  if (/^https?:\/\//i.test(normalized)) return normalized;

  const filename = normalized.split("/").pop();
  if (!filename) {
    return null;
  }

  return `/evidence/${encodeURIComponent(
    jobId
  )}/${encodeURIComponent(filename)}`;

}

function EvidenceImage({

  src,

  title,

  subtitle,

  onOpen,

}: {

  src: string | null;

  title: string;

  subtitle: string;

  onOpen: (src: string, title: string) => void;

}) {

  if (!src) {

    return (

      <div className="evidence-panel">

        <div className="evidence-panel-header">

          <div>

            <span className="evidence-source">{title}</span>

            <strong>Evidence unavailable</strong>

          </div>

        </div>

        <div className="evidence-empty">

          <ImageIcon size={28} />

          <span>No evidence image available</span>

          <small>{subtitle}</small>

        </div>

      </div>

    );

  }

  return (

    <div className="evidence-panel">

      <div className="evidence-panel-header">

        <div>

          <span className="evidence-source">{title}</span>

          <strong>{subtitle}</strong>

        </div>

        <button

          type="button"

          className="evidence-open-button"

          onClick={() => onOpen(src, title)}

        >

          <Search size={15} />

          Preview

        </button>

      </div>

      <button

        type="button"

        className="evidence-image-button"

        onClick={() => onOpen(src, title)}

        aria-label={`Open ${title} evidence`}

      >

        <img

          src={src}

          alt={`${title} evidence`}

          className="evidence-image"

          loading="lazy"

        />

      </button>

    </div>

  );

}

function openEvidenceFile(

  evidence: unknown

) {

  const url = (
    typeof evidence === "string"
      ? evidence
      : isRecord(evidence)
        ? String(evidence.url || evidence.image_path || evidence.path || "")
        : ""
  ).trim();

  if (!url) {

    return;

  }

  window.open(

    url,

    "_blank",

    "noopener,noreferrer"

  );

}

function getReviewConflictId(

  match: MatchRecord

): string {

  const application =

    getMatchValue(match, [

      "application_no",

      "application_number",

      "application",

      "app_no",

      "number",

    ]) || "NO-APPLICATION";

  const page =

    getMatchValue(match, [

      "page",

      "pdf_page",

      "page_number",

    ]) || "NO-PAGE";

  const company =

    getMatchValue(match, [

      "company",

      "company_name",

      "applicant",

      "applicant_name",

      "owner",

      "client_owner",

    ]) || "NO-COMPANY";

  return [

    application,

    page,

    company,

  ]

    .map((value) =>

      String(value)

        .trim()

        .toUpperCase()

        .replace(/\\s+/g, " ")

    )

    .join("|");

}

function MatchCard({

  match,

  index,

  jobId,
  clientIsPdf,
  leftIsXlsx,
  onReviewSaved,
}: {

  match: MatchRecord;

  index: number;

  jobId?: string;
  clientIsPdf?: boolean;
  leftIsXlsx?: boolean;
  onReviewSaved: MatchReviewSaved;

}) {

  const [preview, setPreview] = useState<{

    src: string;

    title: string;

  } | null>(null);

  const [reviewStatus, setReviewStatus] = useState<

    "PENDING" | "CONFIRMED" | "REJECTED"

  >(

    match.review_status === "CONFIRMED"

      ? "CONFIRMED"

      : match.review_status === "REJECTED"

        ? "REJECTED"

        : "PENDING"

  );

  const [reviewComment, setReviewComment] =

    useState<string>(

      getMatchValue(match, ["review_comment"], "")

    );

  const [reviewSaved, setReviewSaved] =

    useState(false);

  const saveReview = async () => {

    if (!jobId) {

      return;

    }

    const conflictId =

      getReviewConflictId(match);

    try {

      const saved = await saveReviewApi(

        jobId,

        conflictId,

        reviewStatus as ReviewStatus,

        reviewComment,

        "Admin"

      );

      onReviewSaved(conflictId, saved);
      setReviewStatus(saved.status);
      setReviewComment(saved.comment);

      setReviewSaved(true);

    } catch (error) {

      console.error("Review save failed:", error);

      setReviewSaved(false);

      window.alert(

        error instanceof Error

          ? error.message

          : "Failed to save review."

      );

    }

  };


  const evidencePairLabel = leftIsXlsx
    ? "XLSX ↔ XLSX"
    : clientIsPdf
      ? "PDF ↔ PDF"
      : "PDF ↔ XLSX";

  const applicationNumber = getMatchValue(match, [

    "application_no",

    "application_number",

    "application",

    "app_no",

    "number",

  ]);

  const company = getMatchValue(match, [

    "company",

    "company_name",

    "applicant",

    "applicant_name",

    "owner",

    "client_owner",

  ]);

  const phone = getMatchValue(match, [

    "phone",

    "phone_number",

    "telephone",

    "tel",

    "mobile",

  ]);

  const page = getMatchValue(match, [

    "page",

    "pdf_page",

    "page_number",

  ]);

  const similarity = getMatchNumber(match, [

    "similarity",

    "similarity_score",

    "score",

    "confidence",

  ]);

  const matchType = getMatchValue(match, [

    "match_type",

    "type",

    "reason",

  ]);

  const reason = getMatchValue(match, [

    "match_reason",

    "reason",

    "description",

  ]);

  const client = getMatchValue(match, [

    "client",

    "client_name",

    "representative",

  ]);

  const sheet = getMatchValue(match, [

    "sheet",

    "sheet_name",

  ]);

  const row = getMatchValue(match, [

    "row",

    "row_number",

  ]);

  const mark = getMatchValue(match, [

    "mark",

    "trademark",

    "mark_name",

  ]);

  const pdfApplicationNumber = getMatchValue(match, [

    "pdf_application_no",

  ]);

  const clientApplicationNumber = getMatchValue(match, [

    "client_application_no",

  ]);

  const logoMatch =
    isRecord(match._logo_match)
      ? match._logo_match
      : null;

  const logoMatched =
    String(match.match_type || "").toUpperCase() === "LOGO MATCH" ||

    Boolean(match.logo_match) ||

    Boolean(match.logoMatched) ||

    Boolean(logoMatch);

  const pdfEvidence =
    typeof match.pdf_evidence === "string" || isRecord(match.pdf_evidence)
      ? match.pdf_evidence
      : null;

  const clientEvidence =
    typeof match.client_evidence === "string" || isRecord(match.client_evidence)
      ? match.client_evidence
      : null;

  const pdfEvidenceUrl = getEvidenceUrl(jobId, pdfEvidence);

  const clientEvidenceUrl = getEvidenceUrl(jobId, clientEvidence);

  const similarityValue =

    similarity !== null

      ? similarity <= 1

        ? similarity * 100

        : similarity

      : logoMatch?.similarity_percent !== undefined

        ? Number(logoMatch.similarity_percent)

        : null;

  const normalizedMatchType =

    String(matchType || "CONFLICT")

      .replace(/_/g, " ")

      .toUpperCase();

  const evidenceLabel =

    logoMatched

      ? "LOGO MATCH"

      : normalizedMatchType;

  return (

    <>

      <article className="match-card">

        <div className="match-card-header">

          <div className="match-index">

            #{String(index + 1).padStart(2, "0")}

          </div>

          <div className="match-header-info">

            <span>APPLICATION</span>

            <strong>{applicationNumber || "—"}</strong>

          </div>

          <div

            className={`match-header-badge ${logoMatched ? "logo-badge" : ""

              }`}

          >

            {evidenceLabel}

          </div>

        </div>

        <div className="match-card-body">

          <div className="match-data-grid">

            <div className="match-data">

              <span>COMPANY</span>

              <strong>{company || "—"}</strong>

            </div>

            <div className="match-data">

              <span>PHONE</span>

              <strong>{phone || "—"}</strong>

            </div>

            <div className="match-data">

              <span>PDF PAGE</span>

              <strong>{page || "—"}</strong>

            </div>

            <div className="match-data">

              <span>MATCH TYPE</span>

              <strong>{normalizedMatchType}</strong>

            </div>

          </div>

          {(client ||

            sheet ||

            row ||

            mark ||

            reason ||

            pdfApplicationNumber ||

            clientApplicationNumber) && (

              <div className="match-secondary-grid">

                {mark && (

                  <div className="match-secondary-item">

                    <span>MARK</span>

                    <strong>{mark}</strong>

                  </div>

                )}

                {client && (

                  <div className="match-secondary-item">

                    <span>CLIENT / REPRESENTATIVE</span>

                    <strong>{client}</strong>

                  </div>

                )}

                {sheet && (

                  <div className="match-secondary-item">

                    <span>CLIENT SHEET</span>

                    <strong>{sheet}</strong>

                  </div>

                )}

                {row && (

                  <div className="match-secondary-item">

                    <span>CLIENT ROW</span>

                    <strong>{row}</strong>

                  </div>

                )}

                {pdfApplicationNumber &&

                  pdfApplicationNumber !== applicationNumber && (

                    <div className="match-secondary-item">

                      <span>PDF APPLICATION</span>

                      <strong>{pdfApplicationNumber}</strong>

                    </div>

                  )}

                {clientApplicationNumber && (

                  <div className="match-secondary-item">

                    <span>CLIENT APPLICATION</span>

                    <strong>

                      {Array.isArray(clientApplicationNumber)

                        ? clientApplicationNumber.join(", ")
                        : clientApplicationNumber}

                    </strong>

                  </div>

                )}

              </div>

            )}

          {reason && (

            <div className="match-reason">

              <AlertTriangle size={17} />

              <div>

                <span>MATCH REASON</span>

                <strong>{reason}</strong>

              </div>

            </div>

          )}

          {similarityValue !== null &&

            Number.isFinite(similarityValue) && (

              <div className="similarity-row">

                <div>

                  <span>VISUAL SIMILARITY</span>

                  <strong>

                    {Math.min(100, Math.max(0, similarityValue)).toFixed(

                      1

                    )}

                    %

                  </strong>

                </div>

                <div className="similarity-bar">

                  <div

                    style={{

                      width: `${Math.min(

                        100,

                        Math.max(0, similarityValue)

                      )}%`,

                    }}

                  />

                </div>

              </div>

            )}

          <div className="conflict-evidence-section">

            <div className="conflict-evidence-title">

              <div>

                <span>EVIDENCE</span>

                <h3>Conflict Evidence</h3>

              </div>

              <div className="evidence-source-badge">

                <FileText size={14} />

                {evidencePairLabel}

              </div>

            </div>

            <div className="evidence-grid">

              <EvidenceImage

                src={pdfEvidenceUrl}

                title="GOVERNMENT JOURNAL"

                subtitle={

                  page

                    ? `Page ${page}`

                    : leftIsXlsx
                      ? "Source Trademark XLSX"
                      : "Government Journal PDF"

                }

                onOpen={(src, title) =>

                  setPreview({ src, title })

                }

              />

              <EvidenceImage

                src={clientEvidenceUrl}

                title="CLIENT TRADEMARK"

                subtitle={

                  sheet && row

                    ? `${sheet} • Row ${row}`

                    : clientIsPdf
                      ? "Client Trademark PDF"
                      : "Client Trademark XLSX"

                }

                onOpen={(src, title) =>

                  setPreview({ src, title })

                }

              />

            </div>

            <div className="evidence-footer">

              <span>

                <FileText size={13} />

                {leftIsXlsx ? "Source Trademark XLSX" : "Government Journal"}

              </span>

              <ChevronRight size={15} />

              <span>

                {clientIsPdf ? (
                  <FileText size={13} />
                ) : (
                  <FileSpreadsheet size={13} />
                )}
                {leftIsXlsx
                  ? "Source Trademark XLSX"
                  : clientIsPdf
                    ? "Client Trademark PDF"
                    : "Client Trademark XLSX"}

              </span>

            </div>

            <div className="review-panel">

              <div className="review-panel-header">

                <div>

                  <span>HUMAN REVIEW</span>

                  <h3>Review Decision</h3>

                </div>

                <span

                  className={`review-status review-${reviewStatus.toLowerCase()}`}

                >

                  {reviewStatus}

                </span>

              </div>

              <div className="review-actions">

                <button

                  type="button"

                  className={

                    reviewStatus === "PENDING"

                      ? "review-button active pending"

                      : "review-button pending"

                  }

                  onClick={() => {

                    setReviewStatus("PENDING");

                    setReviewSaved(false);

                  }}

                >

                  PENDING

                </button>

                <button

                  type="button"

                  className={

                    reviewStatus === "CONFIRMED"

                      ? "review-button active confirmed"

                      : "review-button confirmed"

                  }

                  onClick={() => {

                    setReviewStatus("CONFIRMED");

                    setReviewSaved(false);

                  }}

                >

                  ✓ CONFIRM

                </button>

                <button

                  type="button"

                  className={

                    reviewStatus === "REJECTED"

                      ? "review-button active rejected"

                      : "review-button rejected"

                  }

                  onClick={() => {

                    setReviewStatus("REJECTED");

                    setReviewSaved(false);

                  }}

                >

                  ✕ REJECT

                </button>

              </div>

              <div className="review-comment">

                <label htmlFor={`review-comment-${index}`}>

                  REVIEWER COMMENT

                </label>

                <textarea

                  id={`review-comment-${index}`}

                  value={reviewComment}

                  onChange={(event) => {

                    setReviewComment(event.target.value);

                    setReviewSaved(false);

                  }}

                  placeholder="Add a review note..."

                  rows={3}

                />

              </div>

              <div className="review-footer">

                <button
                  type="button"

                  className="save-review-button"

                  onClick={saveReview}

                >

                  SAVE REVIEW

                </button>

                {reviewSaved && (

                  <span className="review-saved">

                    ✓ Review saved

                  </span>

                )}

              </div>

            </div>

          </div>

        </div>

      </article>

      {preview && (

        <div

          className="evidence-modal"

          onClick={() => setPreview(null)}

          role="dialog"

          aria-modal="true"

        >

          <div

            className="evidence-modal-content"

            onClick={(event) => event.stopPropagation()}

          >

            <div className="evidence-modal-header">

              <div>

                <span>EVIDENCE PREVIEW</span>

                <strong>{preview.title}</strong>

              </div>

              <button

                type="button"

                className="evidence-modal-close"

                onClick={() => setPreview(null)}

                aria-label="Close evidence preview"

              >

                <X size={22} />

              </button>

            </div>

            <div className="evidence-modal-image-wrap">

              <img

                src={preview.src}

                alt={`${preview.title} enlarged evidence`}

                className="evidence-modal-image"

              />

            </div>

          </div>

        </div>

      )}

    </>

  );

}

function App() {

  const [authUser, setAuthUser] = useState<User | null>(null);
  const [authReady, setAuthReady] = useState(!oidcEnabled);
  const [pdfFile, setPdfFile] = useState<File | null>(null);

  const [clientFile, setClientFile] = useState<File | null>(null);

  const [analyzing, setAnalyzing] = useState(false);

  const [analysis, setAnalysis] =

    useState<AnalysisSummary | null>(null);

  const [error, setError] = useState<string | null>(null);

  const [jobId, setJobId] = useState<string | null>(null);
  const [analysisProgress, setAnalysisProgress] =
    useState<AnalysisJobStatus | null>(null);
  const [leftJurisdiction, setLeftJurisdiction] = useState("MM");
  const [rightJurisdiction, setRightJurisdiction] = useState("MM");
  const [leftNiceClasses, setLeftNiceClasses] = useState("");
  const [rightNiceClasses, setRightNiceClasses] = useState("");
  const [leftGoodsServices, setLeftGoodsServices] = useState("");
  const [rightGoodsServices, setRightGoodsServices] = useState("");
  const [sourceName, setSourceName] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [sourceRetrievedAt, setSourceRetrievedAt] = useState("");
  const [, setReviews] = useState<ReviewRecord[]>([]);

  const canAnalyze = Boolean(pdfFile && clientFile);

  useEffect(() => {
    if (!oidcEnabled) return;
    let cancelled = false;
    void getCurrentUser().then((user) => {
      if (cancelled) return;
      setAuthUser(user);
      setAuthReady(true);
    }).catch((authError: unknown) => {
      if (cancelled) return;
      setError(authError instanceof Error ? authError.message : "Could not load sign-in state.");
      setAuthReady(true);
    });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {

    if (!authReady || (oidcEnabled && !authUser)) return;
    let cancelled = false;

    const restoreLastAnalysis = async () => {

      const savedJobId =

        window.localStorage.getItem(

          "trademark_conflict_last_job_id"

        );

      if (!savedJobId) {

        return;

      }

      try {

        setError(null);

        const result = await getResults(

          savedJobId

        );

        if (cancelled) {

          return;

        }

        if (

          !result ||

          !Array.isArray(result.matches)

        ) {

          return;

        }

        let restoredResult = result;

        try {

          const savedReviews =

            await getReviews(savedJobId);

          if (

            Array.isArray(savedReviews) &&

            savedReviews.length > 0

          ) {

            const reviewMap = new Map(

              savedReviews.map((review) => [

                review.conflict_id,

                review,

              ])

            );

            restoredResult = {

              ...result,

              matches: result.matches.map(

                (match: MatchRecord) => {

                  const conflictId = [

                    getMatchValue(match, [

                      "application_no",

                      "application_number",

                      "application",

                      "app_no",
                      "number",

                    ]) || "NO-APPLICATION",

                    getMatchValue(match, [

                      "page",

                      "pdf_page",

                      "page_number",

                    ]) || "NO-PAGE",

                    getMatchValue(match, [

                      "match_type",

                      "type",

                      "reason",

                    ]) || "CONFLICT",

                    getMatchValue(match, [

                      "company",

                      "company_name",

                      "applicant",

                      "applicant_name",

                      "owner",

                      "client_owner",

                    ]) || "NO-COMPANY",

                  ]

                    .map((value) =>

                      String(value)

                        .trim()

                        .toUpperCase()

                        .replace(/\\s+/g, " ")

                    )

                    .join("|");

                  const review =

                    reviewMap.get(conflictId);

                  if (!review) {

                    return match;

                  }

                  return {

                    ...match,

                    review_status: review.status,

                    review_comment: review.comment,

                    reviewed_at: review.reviewed_at,

                  };

                }

              ),

            };

          }

        } catch (reviewError) {

          console.warn(

            "Could not restore saved reviews:",

            reviewError

          );

        }

        setJobId(savedJobId);

        setAnalysis(restoredResult);

      } catch (restoreError) {

        console.warn(

          "Could not restore previous analysis:",

          restoreError

        );

        window.localStorage.removeItem(

          "trademark_conflict_last_job_id"

        );

      }

    };

    restoreLastAnalysis();

    return () => {

      cancelled = true;

    };

  }, [authReady, authUser]);

  const handleAnalyze = async () => {

    if (!pdfFile || !clientFile || analyzing) {

      return;

    }

    setAnalyzing(true);

    setError(null);

    setAnalysis(null);

    setReviews([]);

    setJobId(null);

    try {

      // STEP 1

      // Upload PDF + XLSX
      const uploadResult = await uploadTwoFiles(pdfFile, clientFile, {
        leftJurisdiction,
        rightJurisdiction,
        leftNiceClasses,
        rightNiceClasses,
        leftGoodsServices,
        rightGoodsServices,
        sourceName,
        sourceUrl,
        sourceRetrievedAt: sourceRetrievedAt
          ? new Date(sourceRetrievedAt).toISOString()
          : "",
      });

      const uploadedJobId = uploadResult.job_id;

      if (!uploadedJobId) {

        throw new Error(

          "Backend did not return a job_id."

        );

      }

      setJobId(uploadedJobId);

      // STEP 2

      // Start analysis

      setAnalysisProgress(null);
      await analyzeJob(uploadedJobId);
      const result = await waitForAnalysis(uploadedJobId, setAnalysisProgress);

      try {

        const savedReviews = await getReviews(

          uploadedJobId

        );

        setReviews(savedReviews);

        if (

          Array.isArray(result.matches) &&

          savedReviews.length > 0

        ) {

          const reviewMap = new Map(

            savedReviews.map((review) => [

              review.conflict_id,

              review,

            ])

          );

          result.matches = result.matches.map(

            (match: MatchRecord) => {

              const conflictId = [

                getMatchValue(match, [

                  "application_no",

                  "application_number",

                  "application",

                  "app_no",

                  "number",

                ]) || "NO-APPLICATION",

                getMatchValue(match, [

                  "page",

                  "pdf_page",

                  "page_number",

                ]) || "NO-PAGE",

                getMatchValue(match, [

                  "match_type",

                  "type",
                  "reason",

                ]) || "CONFLICT",

                getMatchValue(match, [

                  "company",

                  "company_name",

                  "applicant",

                  "applicant_name",

                  "owner",

                  "client_owner",

                ]) || "NO-COMPANY",

              ]

                .map((value) =>

                  String(value)

                    .trim()

                    .toUpperCase()

                    .replace(/\\s+/g, " ")

                )

                .join("|");

              const review = reviewMap.get(

                conflictId

              );

              if (!review) {

                return match;

              }

              return {

                ...match,

                review_status: review.status,

                review_comment: review.comment,

                reviewed_at: review.reviewed_at,

              };

            }

          );

        }

      } catch (reviewError) {

        console.warn(

          "Could not load saved reviews:",

          reviewError

        );

        setReviews([]);

      }

      setAnalysis(result);
      setAnalysisProgress({
        job_id: uploadedJobId,
        status: "COMPLETED",
        progress: 100,
        message: "Analysis completed successfully.",
        attempts: 1,
      });

      window.localStorage.setItem(

        "trademark_conflict_last_job_id",

        uploadedJobId

      );

    } catch (err) {

      const message =

        err instanceof Error

          ? err.message

          : "Unknown analysis error.";

      setError(message);

    } finally {

      setAnalyzing(false);

    }

  };

  const handleReset = () => {

    window.localStorage.removeItem(

      "trademark_conflict_last_job_id"

    );

    setPdfFile(null);

    setClientFile(null);

    setAnalysis(null);

    setError(null);

    setJobId(null);

    setAnalyzing(false);
    setAnalysisProgress(null);
  };

  const [matchSearch, setMatchSearch] = useState("");

  const [matchFilter, setMatchFilter] = useState("ALL");

  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);

  const [caseReviewStatus, setCaseReviewStatus] =

    useState<ReviewStatus>("PENDING");

  const [reportGenerating, setReportGenerating] =

    useState(false);

  const [reportReady, setReportReady] =

    useState(false);

  const [reportFilename, setReportFilename] =

    useState("");

  const [reportHistory, setReportHistory] =
    useState<ReportHistoryRecord[]>([]);

  const [caseReviewComment, setCaseReviewComment] =

    useState("");

  const [caseReviewSaving, setCaseReviewSaving] =

    useState(false);

  const [caseReviewSaved, setCaseReviewSaved] =

    useState(false);

  const matches = Array.isArray(analysis?.matches)

    ? analysis.matches

    : [];

  const filteredMatches = matches.filter(

    (match: MatchRecord) => {

      const type = String(

        match.match_type ||

        match.matchType ||

        match.type ||

        ""

      ).toUpperCase();

      const search = matchSearch

        .trim()

        .toLowerCase();

      const matchesType =

        matchFilter === "ALL" ||

        (matchFilter === "APPLICATION" &&

          type.includes("APPLICATION")) ||

        (matchFilter === "LOGO" &&

          type.includes("LOGO")) ||

        (matchFilter === "COMPANY" &&

          type.includes("COMPANY")) ||

        (matchFilter === "PHONE" &&

          type.includes("PHONE"));

      if (!matchesType) {

        return false;

      }

      if (!search) {

        return true;

      }

      const searchable = [

        match.match_type,

        match.matchType,

        match.type,

        match.application_no,

        match.application_number,

        match.application,

        match.client_application_no,

        match.company,

        match.client,

        match.owner,

        match.mark,

        match.phone,

        match.phone_number,

        match.client_phone,

        match.pdf_text,

        match.client_text,

      ]

        .flat()

        .filter(Boolean)

        .join(" ")

        .toLowerCase();

      return searchable.includes(search);

    }

  );

  const caseGroups = new Map<

    string,

    {

      match: MatchRecord;

      status: string;

    }

  >();

  const caseRecords = Array.from(

    caseGroups.entries()

  ).map(([caseId, data]) => ({

    caseId,

    match: data.match,

    status: data.status,

  }));

  const selectedCase = caseRecords.find(

    (item) => item.caseId === selectedCaseId

  );

  const selectedCaseMatches = selectedCase

    ? matches.filter(

      (item: MatchRecord) =>

        getReviewConflictId(item) ===

        selectedCase.caseId

    )

    : [];

  const openCase = (

    caseItem: {

      caseId: string;

      match: MatchRecord;

      status: string;

    }

  ) => {

    setSelectedCaseId(caseItem.caseId);

    const status =

      String(caseItem.status || "PENDING").toUpperCase();

    setCaseReviewStatus(

      status === "CONFIRMED"

        ? "CONFIRMED"

        : status === "REJECTED"

          ? "REJECTED"

          : "PENDING"

    );

    const comment = getMatchValue(
      caseItem.match,
      ["review_comment"],
      "",
    );

    setCaseReviewComment(comment);

    setCaseReviewSaved(false);

  };

  const generateReport = async () => {

    const currentJobId =

      analysis?.job_id || jobId;

    if (!currentJobId) {

      return;

    }

    setReportGenerating(true);

    setReportReady(false);

    try {

      const report =

        await generateConflictReport(

          currentJobId

        );

      setReportFilename(

        report.filename

      );

      setReportReady(true);

      await loadReportHistory();

    } catch (error) {

      console.error(

        "Report generation failed:",

        error

      );

      window.alert(

        error instanceof Error

          ? error.message

          : "Failed to generate report."

      );

    } finally {

      setReportGenerating(false);

    }

  };

  const loadReportHistory = async () => {

    const currentJobId =

      analysis?.job_id || jobId;

    if (!currentJobId) {

      return;

    }

    try {

      const history =

        await getReportHistory(currentJobId);

      setReportHistory(history);

    } catch (error) {

      console.error(

        "Report history load failed:",

        error

      );

    }

  };

  const saveCaseReview = async () => {

    if (!analysis?.job_id || !selectedCase) {

      return;

    }

    setCaseReviewSaving(true);

    setCaseReviewSaved(false);

    try {

      const saved = await saveReviewApi(

        analysis.job_id,

        selectedCase.caseId,

        caseReviewStatus,

        caseReviewComment,

        "Admin"

      );

      setAnalysis((current) => current ? ({
        ...current,
        matches: current.matches.map((item) =>
          getReviewConflictId(item) === selectedCase.caseId
            ? {
                ...item,
                review_status: saved.status,
                review_comment: saved.comment,
                reviewed_at: saved.reviewed_at,
              }
            : item
        ),
      }) : current);
      setCaseReviewStatus(saved.status);
      setCaseReviewComment(saved.comment);
      setCaseReviewSaved(true);

    } catch (error) {

      console.error(

        "Case review save failed:",

        error

      );

      window.alert(

        error instanceof Error

          ? error.message

          : "Failed to save case review."

      );

    } finally {

      setCaseReviewSaving(false);

    }

  };

  for (const match of matches) {

    const caseId = getReviewConflictId(match);

    const currentStatus = String(

      match.review_status || "PENDING"

    ).toUpperCase();

    const existing = caseGroups.get(caseId);

    if (!existing) {

      caseGroups.set(caseId, {

        match,

        status:

          currentStatus === "CONFIRMED" ||

            currentStatus === "REJECTED"

            ? currentStatus

            : "PENDING",

      });

    } else if (

      currentStatus === "CONFIRMED" ||

      currentStatus === "REJECTED"

    ) {

      existing.status = currentStatus;

    }

  }

  const totalConflictCases = caseGroups.size;

  const confirmedCases = Array.from(

    caseGroups.values()

  ).filter(

    (item) => item.status === "CONFIRMED"

  ).length;

  const rejectedCases = Array.from(

    caseGroups.values()

  ).filter(

    (item) => item.status === "REJECTED"

  ).length;

  const pendingCases =

    totalConflictCases -

    confirmedCases -

    rejectedCases;

  const clientIsPdf = Boolean(
    analysis?.right_file_type === "pdf" ||
      (!analysis?.right_file_type &&
        clientFile?.name.toLowerCase().endsWith(".pdf"))
  );
  const leftIsXlsx = Boolean(
    analysis?.left_file_type === "xlsx" ||
      (!analysis?.left_file_type &&
        pdfFile?.name.toLowerCase().endsWith(".xlsx"))
  );

  if (oidcEnabled && !authReady) {
    return <main className="auth-gate">Checking sign-in…</main>;
  }
  if (oidcEnabled && !authUser) {
    return (
      <main className="auth-gate">
        <h1>Sign in to Trademark Conflict</h1>
        {error && <p role="alert">{error}</p>}
        <button type="button" onClick={() => void signIn()}>Sign in with your organization</button>
      </main>
    );
  }

  return (

    <div className="app-shell">

      <header className="topbar">

        <div className="brand">

          <div className="brand-mark">

            <Scale size={24} strokeWidth={1.8} />

          </div>

          <div>

            <div className="brand-name">

              TRADEMARK

            </div>

            <div className="brand-subtitle">

              INTELLIGENCE ENGINE

            </div>

          </div>

        </div>

        <div className="topbar-right">

          <div className="engine-status">

            <span className="status-dot" />

            AI ENGINE ONLINE

          </div>

          <div className="version">

            v1.0

          </div>
          {authUser && (
            <button type="button" className="auth-action" onClick={() => void signOut()}>
              Sign out
            </button>
          )}

        </div>

      </header>

      <main className="main-container">

        <section className="hero">

          <div className="eyebrow">

            <ShieldCheck size={15} />

            AI-POWERED TRADEMARK CONFLICT DETECTION

          </div>

          <h1>

            Trademark

            <span> Intelligence</span>

          </h1>

          <p>

            Compare PDF or XLSX trademark documents
            against each other using

            application, company, phone and visual

            logo intelligence.

          </p>

        </section>

        <section className="upload-section">

          <div className="section-heading">

            <div>

              <div className="section-label">

                01 / DATA INPUT

              </div>

              <h2>Upload Documents</h2>

            </div>

            <div className="secure-badge">

              <ShieldCheck size={15} />

              Secure Processing

            </div>

          </div>

          <div className="upload-grid">

            <FileBox

              title="Left Trademark Document"
              subtitle="Drop a PDF or XLSX file here"
              accept=".pdf,.xlsx,application/pdf"

              file={pdfFile}

              onFile={setPdfFile}

              onRemove={() => setPdfFile(null)}

              icon={<FileText size={28} />}

            />

            <FileBox

              title="Right Trademark Document"
              subtitle="Drop a PDF or XLSX file here"
              accept=".xlsx,.xls,.pdf,application/pdf"
              file={clientFile}
              onFile={setClientFile}
              onRemove={() => setClientFile(null)}
              icon={<FileSpreadsheet size={28} />}

            />

          </div>
          <div className="classification-inputs">
            <label>
              First document jurisdiction
              <input
                value={leftJurisdiction}
                onChange={(event) => setLeftJurisdiction(event.target.value)}
                maxLength={16}
                placeholder="MM, US, EUIPO"
              />
            </label>
            <label>
              Second document jurisdiction
              <input
                value={rightJurisdiction}
                onChange={(event) => setRightJurisdiction(event.target.value)}
                maxLength={16}
                placeholder="MM, US, EUIPO"
              />
            </label>
            <label>
              First Nice classes (comma-separated)
              <input
                value={leftNiceClasses}
                onChange={(event) => setLeftNiceClasses(event.target.value)}
                placeholder="e.g. 9, 25, 35"
              />
            </label>
            <label>
              Second Nice classes (comma-separated)
              <input
                value={rightNiceClasses}
                onChange={(event) => setRightNiceClasses(event.target.value)}
                placeholder="e.g. 9, 25, 35"
              />
            </label>
            <label>
              First goods/services description
              <textarea
                value={leftGoodsServices}
                onChange={(event) => setLeftGoodsServices(event.target.value)}
                maxLength={4000}
                placeholder="Products/services from the first record"
              />
            </label>
            <label>
              Second goods/services description
              <textarea
                value={rightGoodsServices}
                onChange={(event) => setRightGoodsServices(event.target.value)}
                maxLength={4000}
                placeholder="Products/services from the second record"
              />
            </label>
            <label>
              Registry/source name (optional)
              <input
                value={sourceName}
                onChange={(event) => setSourceName(event.target.value)}
                maxLength={255}
                placeholder="Official registry or dataset"
              />
            </label>
            <label>
              Registry/source URL (optional)
              <input
                type="url"
                value={sourceUrl}
                onChange={(event) => setSourceUrl(event.target.value)}
                placeholder="https://..."
              />
            </label>
            <label>
              Data retrieved at (optional)
              <input
                type="datetime-local"
                value={sourceRetrievedAt}
                onChange={(event) => setSourceRetrievedAt(event.target.value)}
              />
            </label>
          </div>

          <button

            className={`analyze-button ${canAnalyze ? "ready" : ""

              }`}

            disabled={!canAnalyze || analyzing}

            onClick={handleAnalyze}

          >

            {analyzing ? (

              <>

                <span className="spinner" />

                ANALYZING DOCUMENTS...

              </>

            ) : (

              <>

                <Search size={18} />

                ANALYZE TRADEMARK CONFLICT

                <ChevronRight size={18} />

              </>

            )}

          </button>

          {error && (

            <div className="analysis-error">
              <AlertTriangle size={18} />

              <div>

                <strong>Analysis failed</strong>

                <span>{error}</span>

              </div>

              <button

                type="button"

                onClick={handleAnalyze}

                disabled={!canAnalyze || analyzing}

              >

                <RefreshCw size={16} />

                Retry

              </button>

            </div>

          )}

          {jobId && (

            <div className="job-status">

              JOB ID:

              <span>{jobId}</span>

            </div>

          )}
          {analyzing && analysisProgress && (
            <div className="analysis-progress" role="status" aria-live="polite">
              <div className="analysis-progress-label">
                <span>{analysisProgress.message}</span>
                <strong>{analysisProgress.progress}%</strong>
              </div>
              <progress value={analysisProgress.progress} max={100} />
            </div>
          )}

        </section>

        <section className="results-section">

          <div className="section-heading">

            <div>

              <div className="section-label">

                02 / ANALYSIS OVERVIEW

              </div>

              <h2>Detection Results</h2>

            </div>

            <div className="result-state">

              <span

                className={`state-dot ${analysis ? "complete" : ""

                  }`}

              />

              {analyzing

                ? "ANALYSIS IN PROGRESS"

                : analysis

                  ? "ANALYSIS COMPLETE"

                  : "READY FOR ANALYSIS"}

            </div>

          </div>

          <div className="metrics-grid">

            <MetricCard

              label="PDF PAGES"

              value={

                analysis

                  ? analysis.pdf_pages

                  : "—"

              }

              icon={<FileText size={20} />}

            />

            <MetricCard

              label="CLIENT RECORDS"

              value={

                analysis

                  ? analysis.client_records

                  : "—"

              }

              icon={

                <FileSpreadsheet size={20} />

              }

            />

            <MetricCard

              label="APPLICATION MATCHES"

              value={

                analysis

                  ? analysis.application_matches

                  : "—"

              }

              icon={<Search size={20} />}

            />

            <MetricCard

              label="LOGO MATCH"

              value={

                analysis

                  ? analysis.logo_matches

                  : "—"

              }

              icon={<ImageIcon size={20} />}

              accent

            />

          </div>

          {analysis && (

            <div className="secondary-metrics">

              <div>

                <span>PDF LOGOS DETECTED</span>

                <strong>{analysis.pdf_logos}</strong>

              </div>

              <div>

                <span>CLIENT LOGOS DETECTED</span>

                <strong>{analysis.xlsx_logos}</strong>

              </div>

              <div>

                <span>TOTAL CONFLICT RECORDS</span>

                <strong>{matches.length}</strong>

              </div>

              <div className="case-management">

                <div className="case-management-header">

                  <span>CASE MANAGEMENT</span>

                  <strong>{totalConflictCases}</strong>

                </div>

                <div className="case-management-grid">

                  <div className="case-stat">

                    <span>TOTAL CONFLICTS</span>

                    <strong>{totalConflictCases}</strong>

                  </div>

                  <div className="case-stat pending">

                    <span>PENDING</span>

                    <strong>{pendingCases}</strong>

                  </div>

                  <div className="case-stat confirmed">

                    <span>CONFIRMED</span>

                    <strong>{confirmedCases}</strong>

                  </div>

                  <div className="case-stat rejected">

                    <span>REJECTED</span>

                    <strong>{rejectedCases}</strong>

                  </div>

                </div>

              </div>

            </div>

          )}
          {selectedCase && (

            <section className="case-detail-section">

              <div className="section-heading">

                <div>

                  <div className="section-label">

                    CASE DETAIL

                  </div>

                  <h2>Conflict Case</h2>

                </div>

                <button

                  type="button"

                  className="case-close-button"

                  onClick={() => setSelectedCaseId(null)}

                >

                  CLOSE

                </button>

              </div>

              <div className="case-detail-card">

                <div className="case-detail-header">

                  <div>

                    <span className="case-label">

                      APPLICATION

                    </span>

                    <strong className="case-detail-application">

                      {getMatchValue(selectedCase.match, [

                        "application_no",

                        "application_number",

                        "application",

                        "app_no",

                        "number",

                      ]) || "N/A"}

                    </strong>

                  </div>

                  <span

                    className={`case-status ${selectedCase.status.toLowerCase()}`}

                  >

                    {selectedCase.status}

                  </span>

                </div>
                <div className="case-detail-info">

                  <div className="case-info-item">

                    <span>APPLICATION NUMBER</span>

                    <strong>

                      {getMatchValue(selectedCase.match, [

                        "application_no",

                        "application_number",

                        "application",

                        "app_no",

                        "number",

                      ]) || "N/A"}

                    </strong>

                  </div>

                  <div className="case-info-item">

                    <span>PDF PAGE</span>

                    <strong>

                      {getMatchValue(selectedCase.match, [

                        "page",

                        "pdf_page",

                        "page_number",

                      ]) || "N/A"}

                    </strong>

                  </div>

                  <div className="case-info-item">

                    <span>COMPANY</span>

                    <strong>

                      {getMatchValue(selectedCase.match, [

                        "company",

                        "company_name",

                        "applicant",

                        "applicant_name",

                        "owner",

                        "client_owner",

                      ]) || "N/A"}

                    </strong>

                  </div>

                </div>

                <div className="case-source-actions">

                  <button

                    type="button"

                    className="case-source-button"

                    onClick={() => {

                      const page =

                        getMatchValue(selectedCase.match, [

                          "page",

                          "pdf_page",

                          "page_number",

                        ]) || 1;

                      const jobId = analysis?.job_id;

                      if (!jobId) {

                        return;

                      }

                      const url =

                        `/api/results/${jobId}/pdf?page=${page}`;

                      window.open(

                        url,

                        "_blank",

                        "noopener,noreferrer"

                      );

                    }}

                  >

                    VIEW PDF PAGE

                  </button>

                </div>

                <div className="case-detail-signals">

                  <div className="case-detail-signals">

                    <span className="case-detail-title">

                      CONFLICT EVIDENCE

                    </span>

                    <div className="case-evidence-table">

                      <div className="case-evidence-header">

                        <span>TYPE</span>

                        <span>PDF / GOVERNMENT</span>

                        <span>CLIENT</span>

                      </div>

                      {selectedCaseMatches.map(

                        (

                          item: MatchRecord,

                          index: number

                        ) => {

                          const signal = String(

                            item.match_type ||

                            item.matchType ||

                            item.type ||

                            "CONFLICT"

                          ).toUpperCase();

                          const governmentValue =

                            item.pdf_value ||

                            item.government_value ||

                            item.source_value ||

                            item.matched_pdf_value ||

                            item.pdf_match ||

                            item.government_match ||

                            item.value ||

                            "—";

                          const clientValue =

                            item.client_value ||

                            item.xlsx_value ||

                            item.client_match ||

                            item.matched_client_value ||

                            item.client ||

                            "—";

                          return (

                            <div

                              className="case-evidence-table-row"

                              key={`${selectedCase.caseId}-${signal}-${index}`}

                            >

                              <div>

                                <span className="evidence-type">

                                  {signal}

                                </span>

                              </div>

                              <div className="evidence-source-cell">

                                <span className="evidence-value">

                                  {String(governmentValue)}

                                </span>

                                {item.pdf_evidence !== undefined &&
                                  item.pdf_evidence !== null && (

                                  <button

                                    type="button"

                                    className="evidence-view-button"

                                    onClick={() =>

                                      openEvidenceFile(

                                        item.pdf_evidence

                                      )

                                    }

                                  >

                                    VIEW PDF EVIDENCE

                                  </button>

                                )}

                              </div>

                              <div className="evidence-source-cell">

                                <span className="evidence-value">

                                  {String(clientValue)}

                                </span>

                                {item.client_evidence !== undefined &&
                                  item.client_evidence !== null && (

                                  <button

                                    type="button"

                                    className="evidence-view-button client"

                                    onClick={() =>

                                      openEvidenceFile(

                                        item.client_evidence

                                      )

                                    }

                                  >

                                    VIEW CLIENT EVIDENCE

                                  </button>

                                )}

                              </div>

                            </div>

                          );

                        }

                      )}

                    </div>

                  </div>

                </div>

                <div className="case-review-panel">

                  <div className="case-detail-title">

                    HUMAN REVIEW

                  </div>

                  <div className="case-review-status">

                    <span>

                      CURRENT STATUS

                    </span>

                    <strong

                      className={`case-status ${selectedCase.status.toLowerCase()}`}

                    >

                      {selectedCase.status}

                    </strong>

                  </div>

                  <div className="case-review-actions">

                    <button

                      type="button"

                      className={`review-button pending ${caseReviewStatus === "PENDING"

                        ? "active"

                        : ""

                        }`}

                      onClick={() => {

                        setCaseReviewStatus("PENDING");

                        setCaseReviewSaved(false);

                      }}

                    >

                      PENDING

                    </button>

                    <button

                      type="button"

                      className={`review-button confirmed ${caseReviewStatus === "CONFIRMED"

                        ? "active"

                        : ""

                        }`}

                      onClick={() => {

                        setCaseReviewStatus("CONFIRMED");

                        setCaseReviewSaved(false);

                      }}

                    >

                      CONFIRMED

                    </button>

                    <button

                      type="button"

                      className={`review-button rejected ${caseReviewStatus === "REJECTED"

                        ? "active"

                        : ""

                        }`}

                      onClick={() => {

                        setCaseReviewStatus("REJECTED");

                        setCaseReviewSaved(false);

                      }}

                    >

                      REJECTED

                    </button>

                  </div>

                  <textarea

                    className="case-review-textarea"

                    value={caseReviewComment}

                    onChange={(event) => {

                      setCaseReviewComment(

                        event.target.value

                      );

                      setCaseReviewSaved(false);

                    }}

                    placeholder="Add review comment..."

                    rows={4}

                  />
                  <div className="case-review-footer">

                    <button

                      type="button"

                      className="case-save-review"

                      onClick={saveCaseReview}

                      disabled={caseReviewSaving}

                    >

                      {caseReviewSaving

                        ? "SAVING..."

                        : "SAVE REVIEW"}

                    </button>

                    {caseReviewSaved && (

                      <span className="review-saved-message">

                        REVIEW SAVED

                      </span>

                    )}

                  </div>

                  <div className="case-review-note">

                    Review is saved through the existing Human Review

                    persistence system.

                  </div>

                </div>

                <div className="case-report-panel">

                  <div className="case-detail-title">

                    CONFLICT INVESTIGATION REPORT

                  </div>

                  <p className="case-report-description">

                    Generate a formal PDF investigation report containing

                    conflict evidence, case details, and human review records.

                  </p>

                  <div className="case-report-actions">

                    <button

                      type="button"

                      className="case-generate-report"

                      onClick={generateReport}

                      disabled={reportGenerating}

                    >

                      {reportGenerating

                        ? "GENERATING REPORT..."

                        : "GENERATE REPORT"}

                    </button>

                  </div>

                  {reportReady && (

                    <div className="report-ready">

                      <div className="report-ready-info">

                        <span className="report-ready-label">

                          REPORT READY

                        </span>

                        <strong className="report-ready-filename">

                          {reportFilename ||

                            "Trademark_Conflict_Investigation_Report.pdf"}

                        </strong>

                      </div>

                      <div className="report-ready-actions">

                        <button

                          type="button"

                          className="report-open-button"

                          onClick={() => {
                            const currentJobId =
                              analysis?.job_id || jobId;
                            if (!currentJobId) {
                              return;
                            }
                            void downloadConflictReport(currentJobId);

                          }}

                        >

                          OPEN REPORT

                        </button>

                        <button

                          type="button"

                          className="report-download-button"

                          onClick={() => {
                            const currentJobId =
                              analysis?.job_id || jobId;
                            if (!currentJobId) {
                              return;
                            }
                            void downloadConflictReport(currentJobId);

                          }}

                        >

                          DOWNLOAD PDF

                        </button>

                      </div>

                    </div>

                  )}

                </div>

                <div className="report-history-panel">

                  <div className="case-detail-title">

                    REPORT HISTORY

                  </div>

                  {reportHistory.length === 0 ? (

                    <div className="report-history-empty">

                      No reports generated for this job yet.

                    </div>

                  ) : (

                    <div className="report-history-list">

                      {reportHistory.map((report) => (

                        <div

                          className="report-history-item"

                          key={report.id}

                        >

                          <div className="report-history-info">

                            <span className="report-history-type">

                              {report.report_type.replace(

                                /_/g,

                                " "

                              )}

                            </span>

                            <strong>

                              {report.filename}

                            </strong>

                            <span className="report-history-date">

                              {new Date(

                                report.created_at

                              ).toLocaleString()}

                            </span>

                          </div>

                          <button

                            type="button"

                            className="report-history-open"

                            onClick={() => {
                              const currentJobId =
                                analysis?.job_id || jobId;
                              if (!currentJobId) {
                                return;
                              }
                              void downloadConflictReport(currentJobId);

                            }}

                          >

                            OPEN PDF

                          </button>

                        </div>

                      ))}

                    </div>

                  )}

                </div>
              </div>

            </section>

          )}
        </section>
        {analysis && caseRecords.length > 0 && (

          <section className="case-management-section">

            <div className="section-heading">

              <div>

                <div className="section-label">

                  03 / CASE MANAGEMENT

                </div>

                <h2>Conflict Cases</h2>

              </div>

              <div className="match-count">

                {caseRecords.length}{" "}

                {caseRecords.length === 1

                  ? "CASE"

                  : "CASES"}

              </div>

            </div>

            <div className="case-list">

              {caseRecords.map((caseItem) => {

                const match = caseItem.match;

                const application =

                  getMatchValue(match, [

                    "application_no",

                    "application_number",

                    "application",

                    "app_no",

                    "number",

                  ]) || "N/A";

                const page =

                  getMatchValue(match, [

                    "page",

                    "pdf_page",

                    "page_number",

                  ]) || "N/A";

                const company =

                  getMatchValue(match, [

                    "company",

                    "company_name",

                    "applicant",

                    "applicant_name",

                    "owner",

                    "client_owner",

                  ]) || "N/A";

                const signalTypes = matches

                  .filter(

                    (item: MatchRecord) =>

                      getReviewConflictId(item) ===

                      caseItem.caseId

                  )

                  .map(

                    (item: MatchRecord) =>

                      String(

                        item.match_type ||

                        item.matchType ||

                        item.type ||

                        ""

                      ).toUpperCase()

                  )

                  .filter(Boolean);

                const uniqueSignals = Array.from(

                  new Set(signalTypes)

                );

                return (

                  <div

                    className="case-card"

                    key={caseItem.caseId}

                  >

                    <div className="case-card-top">

                      <div>

                        <span className="case-label">

                          APPLICATION

                        </span>

                        <strong className="case-application">

                          {application}

                        </strong>

                      </div>

                      <span

                        className={`case-status ${caseItem.status.toLowerCase()}`}

                      >

                        {caseItem.status}

                      </span>

                    </div>

                    <div className="case-card-info">

                      <div>

                        <span>PDF PAGE</span>

                        <strong>{page}</strong>

                      </div>

                      <div>

                        <span>COMPANY</span>

                        <strong>{company}</strong>

                      </div>

                    </div>

                    <div className="case-signals">

                      <span>SIGNALS</span>

                      <div className="signal-list">

                        {uniqueSignals.map(

                          (signal) => (

                            <span

                              className="signal-chip"

                              key={signal}

                            >

                              {signal.replace(

                                " MATCH",

                                ""

                              )}

                            </span>

                          )

                        )}

                      </div>
                    </div>

                    <div className="case-actions">

                      <button

                        type="button"

                        className="case-view-button"

                        onClick={() =>

                          openCase(caseItem)

                        }

                      >

                        VIEW CASE

                      </button>

                    </div>
                  </div>

                );

              })}

            </div>

          </section>

        )}
        <section className="matches-section">

          <div className="section-heading">

            <div>

              <div className="section-label">

                03 / EVIDENCE

              </div>

              <h2>Conflict Matches</h2>

            </div>

            <div className="match-count">

              {matches.length}{" "}

              {matches.length === 1

                ? "MATCH"

                : "MATCHES"}

            </div>

          </div>

          <div className="match-controls">

            <div className="match-search">

              <Search size={17} />

              <input

                type="text"

                value={matchSearch}

                onChange={(event) =>

                  setMatchSearch(event.target.value)

                }

                placeholder="Search company, application, mark, phone..."

                aria-label="Search conflicts"

              />

              {matchSearch && (

                <button

                  type="button"

                  onClick={() => setMatchSearch("")}

                  aria-label="Clear search"

                >

                  ×

                </button>

              )}

            </div>

            <div className="match-filters">

              {[

                "ALL",

                "APPLICATION",

                "LOGO",

                "COMPANY",

                "PHONE",

              ].map((filter) => (
                <button

                  key={filter}

                  type="button"

                  className={

                    matchFilter === filter

                      ? "active"

                      : ""

                  }

                  onClick={() =>

                    setMatchFilter(filter)

                  }

                >

                  {filter}

                </button>

              ))}

            </div>

            <div className="filter-summary">

              Showing{" "}

              <strong>{filteredMatches.length}</strong>{" "}

              of{" "}

              <strong>{matches.length}</strong>{" "}

              conflicts

            </div>

          </div>

          {!analysis ? (

            <div className="empty-results">

              <div className="empty-icon">

                <Search size={28} />

              </div>

              <h3>No analysis results yet</h3>

              <p>

                Upload two PDF files, two XLSX files, or one PDF and one XLSX file,
                then start the AI analysis.

              </p>

            </div>

          ) : filteredMatches.length === 0 ? (

            <div className="empty-results success-empty">
              <div className="empty-icon">

                <CheckCircle2 size={28} />

              </div>

              <h3>No conflicts detected</h3>

              <p>

                The analysis completed successfully.

                No application or logo conflicts were

                returned for this dataset.

              </p>

            </div>

          ) : (

            <div className="matches-list">

              {filteredMatches.map(

                (

                  match: MatchRecord,

                  index: number

                ) => (

                  match.match_type === "LOGO MATCH" ||

                    match.matchType === "LOGO MATCH" ||

                    match.type === "LOGO MATCH" ? (

                    <LogoMatchCard

                      key={`logo-${index}`}

                      match={match}

                      jobId={analysis?.job_id || ""}
                      leftIsXlsx={leftIsXlsx}
                      clientIsPdf={clientIsPdf}

                    />

                  ) : (

                    <MatchCard

                      key={`${index}-${getMatchValue(

                        match,

                        [

                          "application_no",

                          "application_number",

                          "application",

                        ]

                      )}`}

                      match={match}

                      index={index}

                      jobId={analysis?.job_id}
                      clientIsPdf={clientIsPdf}

                      leftIsXlsx={leftIsXlsx}
                      onReviewSaved={(conflictId, review) => {
                        setAnalysis((current) => current ? ({
                          ...current,
                          matches: current.matches.map((item) =>
                            getReviewConflictId(item) === conflictId
                              ? {
                                  ...item,
                                  review_status: review.status,
                                  review_comment: review.comment,
                                  reviewed_at: review.reviewed_at,
                                }
                              : item
                          ),
                        }) : current);
                      }}

                    />

                  )

                )

              )}

            </div>

          )}

        </section>

        {analysis && (

          <section className="analysis-summary">

            <div className="analysis-summary-icon">

              <CheckCircle2 size={20} />

            </div>

            <div>

              <strong>

                Analysis completed successfully

              </strong>

              <span>

                {analysis.pdf_pages} PDF pages and{" "}

                {analysis.client_records} client

                records were processed.

              </span>

            </div>

            <button

              type="button"

              className="new-analysis-button"

              onClick={handleReset}

            >

              NEW ANALYSIS

            </button>

          </section>

        )}

        <AIAssistant jobId={jobId} />

      </main>

      <footer className="footer">

        <div className="footer-brand">
          <img
            className="copyright-logo"
            src="/copyright.png"
            alt="BHONE copyright logo"
          />
          <div className="footer-brand-copy">
            <strong>TRADEMARK INTELLIGENCE ENGINE</strong>
            <small>BHONE original copyright mark</small>
          </div>
        </div>

        <div className="footer-right">
          <span>PRIVATE ANALYSIS</span>
          <span>•</span>
          <span>LOCAL PROCESSING</span>
          <span>•</span>
          <span>© {new Date().getFullYear()} BHONE. ALL RIGHTS RESERVED.</span>
        </div>

      </footer>

    </div>

  );

}

export default App;