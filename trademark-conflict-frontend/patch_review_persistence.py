from pathlib import Path

path = Path("src/App.tsx")

text = path.read_text(encoding="utf-8")

# ---------------------------------------------------------

# 1. Replace MatchCard saveReview with async backend save

# ---------------------------------------------------------

old_save = '''  const saveReview = () => {

    match.review_status = reviewStatus;

    match.review_comment = reviewComment;

    match.reviewed_at = new Date().toISOString();

    setReviewSaved(true);

  };

'''

new_save = '''  const saveReview = async () => {

    if (!jobId) {

      return;

    }

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

          .replace(/\\\\s+/g, " ")

      )

      .join("|");

    try {

      const saved = await saveReviewApi(

        jobId,

        conflictId,

        reviewStatus as ReviewStatus,

        reviewComment,

        "Admin"

      );

      match.review_status = saved.status;

      match.review_comment = saved.comment;

      match.reviewed_at = saved.reviewed_at;

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

'''

if old_save not in text:

    raise SystemExit(

        "ERROR: Existing saveReview block not found."

    )

text = text.replace(old_save, new_save, 1)

# ---------------------------------------------------------

# 2. Add persisted reviews state

# ---------------------------------------------------------

state_marker = '''  const [jobId, setJobId] = useState<string | null>(null);

'''

state_insert = '''  const [jobId, setJobId] = useState<string | null>(null);

  const [reviews, setReviews] = useState<ReviewRecord[]>([]);

'''

if state_marker not in text:

    raise SystemExit(

        "ERROR: jobId state marker not found."

    )

text = text.replace(

    state_marker,

    state_insert,

    1,

)

# ---------------------------------------------------------

# 3. Load reviews after analysis

# ---------------------------------------------------------

analysis_marker = '''      const result = await analyzeJob(uploadedJobId);

      setAnalysis(result);

'''

analysis_replacement = '''      const result = await analyzeJob(uploadedJobId);

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

            (match: Record<string, any>) => {

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

                    .replace(/\\\\s+/g, " ")

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

'''

if analysis_marker not in text:

    raise SystemExit(

        "ERROR: Analysis result marker not found."

    )

text = text.replace(

    analysis_marker,

    analysis_replacement,

    1,

)

# ---------------------------------------------------------

# 4. Clear reviews when starting a new analysis

# ---------------------------------------------------------

clear_marker = '''    setAnalysis(null);

    setJobId(null);

'''

clear_replacement = '''    setAnalysis(null);

    setReviews([]);

    setJobId(null);

'''

if clear_marker in text:

    text = text.replace(

        clear_marker,

        clear_replacement,

        1,

    )

# ---------------------------------------------------------

# 5. Prevent unused ReviewStatus if TS decides it is only

#    needed in a type assertion but keep explicit usage.

# ---------------------------------------------------------

path.write_text(text, encoding="utf-8")

print("REVIEW API SAVE: OK")

print("REVIEW LOAD: OK")

print("REVIEW STATE: OK")

print("REVIEW RESTORE: OK")

print("PATCHED OK")