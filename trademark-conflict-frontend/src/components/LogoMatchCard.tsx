type LogoMatch = {

  logo_match?: boolean;

  similarity?: number;

  similarity_percent?: number;

  visual_similarity?: number;

  text_match?: string;

  visual_match?: string | boolean;

  decision?: string;

  decision_reason?: string;

  page?: number;

  pdf_page?: number;

  client_page?: number;

  client_row?: number;

  row?: number;

  pdf_row?: number;

  sheet?: string;

  pdf_sheet?: string;

  company?: string;

  client?: string;

  application_no?: string;

  client_application_no?: string | string[];

  pdf_evidence?: string | {

    url?: string;

    image_path?: string;

  };

  client_evidence?: string | {

    url?: string;

    image_path?: string;

  };

  pdf_evidence_url?: string;

  client_evidence_url?: string;

};

type Props = {

  jobId: string;

  match: LogoMatch;

  leftIsXlsx: boolean;

  clientIsPdf: boolean;

};

function getEvidenceValue(

  value?: string | { url?: string; image_path?: string }

): string | undefined {

  if (!value) return undefined;

  if (typeof value === "string") {

    return value;

  }

  return value.url || value.image_path;

}

function evidenceUrl(jobId: string, value?: string): string | null {

  if (!value) return null;

  if (/^https?:\/\//i.test(value)) {

    return value;

  }

  if (value.startsWith("/evidence/")) {
    return value;

  }

  const filename = value

    .replace(/\\/g, "/")

    .split("/")

    .pop();

  if (!filename) {

    return null;

  }

  return `/evidence/${encodeURIComponent(
    jobId
  )}/${encodeURIComponent(filename)}`;

}

function displayApplication(

  value?: string | string[]

): string {

  if (!value) return "—";

  if (Array.isArray(value)) {

    return value.join(", ");

  }

  return value;

}

export default function LogoMatchCard({

  jobId,

  match,

  leftIsXlsx,

  clientIsPdf,

}: Props) {

  const pdfEvidenceValue =

    match.pdf_evidence_url ||

    getEvidenceValue(match.pdf_evidence);

  const clientEvidenceValue =

    match.client_evidence_url ||

    getEvidenceValue(match.client_evidence);

  const pdfImage = evidenceUrl(

    jobId,

    pdfEvidenceValue

  );

  const clientImage = evidenceUrl(

    jobId,

    clientEvidenceValue

  );

  const similarity = Number(

    match.visual_similarity ??

      match.similarity_percent ??

      (match.similarity

        ? match.similarity * 100

        : 0)

  );

  const textMatch =

    match.text_match || "NO_TEXT";

  const visualMatch =

    String(match.visual_match ?? "");

  const confirmed =

    match.logo_match === true ||

    match.decision === "CONFIRMED" ||

    match.decision === "VISUAL_CONFIRMED";

  const page =

    match.page ??

    match.pdf_page;

  const clientPage = match.client_page;

  const clientRow =

    match.client_row ??

    match.row;
  const leftRow = match.pdf_row;

  const leftTitle = leftIsXlsx
    ? "LEFT XLSX"
    : clientIsPdf
      ? "LEFT PDF"
      : "GOVERNMENT PDF";
  const rightTitle = leftIsXlsx
    ? "RIGHT XLSX"
    : clientIsPdf
      ? "RIGHT PDF"
      : "CLIENT TRADEMARK";
  const pairLabel = leftIsXlsx
    ? "XLSX ↔ XLSX"
    : clientIsPdf
      ? "PDF ↔ PDF"
      : "PDF ↔ XLSX";

  return (

    <div
      className={`logo-match-card ${
        leftIsXlsx ? "xlsx-logo-match-card" : ""
      }`}
    >

      <div className="logo-match-card-header">

        <div>

          <strong>LOGO MATCH</strong>

          <span>

            {pairLabel} · {match.company ||

              match.client ||

              "Trademark record"}

          </span>

        </div>

        <strong>

          {similarity.toFixed(2)}%

        </strong>

      </div>

      <div className="logo-match-evidence-grid">

        <EvidencePanel

          title={leftTitle}

          image={pdfImage}

          subtitle={

            leftIsXlsx && leftRow
              ? `${match.pdf_sheet || "Source"} · Row ${leftRow}`
              : page

              ? `Page ${page}`

              : leftIsXlsx
                ? "Source XLSX evidence"
                : "PDF evidence"

          }

        />

        <EvidencePanel

          title={rightTitle}

          image={clientImage}

          subtitle={

            clientIsPdf && clientPage
              ? `Page ${clientPage}`
              : clientRow

              ? `${match.sheet || "Client"} · Row ${clientRow}`

              : clientIsPdf
                ? "PDF evidence"
                : "Client evidence"

          }

        />

      </div>

      <div className="logo-match-status-grid">

        <Status

          label="TEXT MATCH"

          value={textMatch}

          ok={textMatch === "EXACT"}

        />

        <Status

          label="VISUAL MATCH"

          value={

            visualMatch ||

            (confirmed

              ? "CONFIRMED"

              : "NOT CONFIRMED")

          }

          ok={confirmed}

        />

        <Status

          label="RESULT"

          value={

            confirmed

              ? "LOGO MATCH"

              : "REVIEW"
            }

          ok={confirmed}

        />

      </div>

      {match.decision_reason && (

        <div className="logo-match-reason">

          <small>DECISION</small>

          <span>{match.decision_reason}</span>

        </div>

      )}

      <div className="logo-match-meta">

        <span>

          Page: {page ?? "—"}

        </span>

        <span>

          Client Row: {clientRow ?? "—"}

        </span>

        <span>

          Application:{" "}

          {displayApplication(

            match.application_no ??

              match.client_application_no

          )}

        </span>

      </div>

    </div>

  );

}

function EvidencePanel({

  title,

  image,

  subtitle,

}: {

  title: string;

  image: string | null;

  subtitle: string;

}) {

  return (

    <div>

      <div className="logo-match-evidence-title">

        {title}

      </div>

      <div className="logo-match-evidence">

        {image ? (

          <img

            src={image}

            alt={`${title} evidence`}

          />

        ) : (

          <span>No evidence image</span>

        )}

      </div>

      <small>{subtitle}</small>

    </div>

  );

}

function Status({

  label,

  value,

  ok,

}: {

  label: string;

  value: string;

  ok: boolean;

}) {

  return (

    <div className="logo-match-status">

      <small>{label}</small>

      <strong

        className={

          ok

            ? "is-ok"

            : "needs-review"

        }

      >

        {value}

      </strong>

    </div>

  );

}