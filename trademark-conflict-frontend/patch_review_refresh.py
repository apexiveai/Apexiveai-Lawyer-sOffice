from pathlib import Path

import re

path = Path("src/App.tsx")

text = path.read_text(encoding="utf-8")

# =========================================================

# 1. Add useEffect

# =========================================================

if "useEffect," not in text:

    text = text.replace(

        "  useState,\n",

        "  useEffect,\n\n  useState,\n",

        1,

    )

print("USEEFFECT: OK")

# =========================================================

# 2. Add getResults to API import

# =========================================================

if "  getResults," not in text:

    marker = "  analyzeJob,\n"

    if marker not in text:

        raise SystemExit(

            "ERROR: analyzeJob import not found."

        )

    text = text.replace(

        marker,

        "  analyzeJob,\n\n  getResults,\n",

        1,

    )

print("GETRESULTS IMPORT: OK")

# =========================================================

# 3. Save latest job ID after analysis

# =========================================================

old = """      setAnalysis(result);

    } catch (err) {

"""

new = """      setAnalysis(result);

      window.localStorage.setItem(

        "trademark_conflict_last_job_id",

        uploadedJobId

      );

    } catch (err) {

"""

if old in text:

    text = text.replace(

        old,

        new,

        1,

    )

    print("JOB ID PERSISTENCE: OK")

elif "trademark_conflict_last_job_id" in text:

    print("JOB ID PERSISTENCE: ALREADY EXISTS")

else:

    raise SystemExit(

        "ERROR: Could not find setAnalysis(result) block."

    )

# =========================================================

# 4. Clear saved job on Reset

# =========================================================

old = """  const handleReset = () => {

    setPdfFile(null);

"""

new = """  const handleReset = () => {

    window.localStorage.removeItem(

      "trademark_conflict_last_job_id"

    );

    setPdfFile(null);

"""

if old in text:

    text = text.replace(

        old,

        new,

        1,

    )

    print("RESET STORAGE: OK")

elif "localStorage.removeItem" in text:

    print("RESET STORAGE: ALREADY EXISTS")

else:

    raise SystemExit(

        "ERROR: handleReset block not found."

    )

# =========================================================

# 5. Add restore useEffect

# =========================================================

if "const restoreLastAnalysis = async" in text:

    print("RESTORE EFFECT: ALREADY EXISTS")

else:

    marker = """  const canAnalyze = Boolean(pdfFile && clientFile);

  const handleAnalyze = async () => {

"""

    restore = """  const canAnalyze = Boolean(pdfFile && clientFile);

  useEffect(() => {

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

  }, []);

  const handleAnalyze = async () => {

"""

    if marker not in text:

        raise SystemExit(

            "ERROR: canAnalyze marker not found."

        )

    text = text.replace(

        marker,

        restore,

        1,

    )

    print("RESTORE EFFECT: OK")

# =========================================================

# Save

# =========================================================

path.write_text(

    text,

    encoding="utf-8",

)

print("")

print("================================")

print("REFRESH PERSISTENCE PATCHED OK")

print("================================")