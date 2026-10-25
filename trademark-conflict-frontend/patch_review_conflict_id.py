from pathlib import Path

path = Path("src/App.tsx")

text = path.read_text(encoding="utf-8")

# =========================================================

# 1. Add helper function

# =========================================================

marker = '''function MatchCard({

'''

helper = '''function getReviewConflictId(

  match: Record<string, any>

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

        .replace(/\\\\s+/g, " ")

    )

    .join("|");

}

function getLegacyReviewConflictId(

  match: Record<string, any>

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

  const type =

    getMatchValue(match, [

      "match_type",

      "type",

      "reason",

    ]) || "CONFLICT";

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

    type,

    company,

  ]

    .map((value) =>

      String(value)

        .trim()

        .toUpperCase()

        .replace(/\\\\s+/g, " ")

    )

    .join("|");

}

'''

if "function getReviewConflictId(" not in text:

    if marker not in text:

        raise SystemExit(

            "ERROR: MatchCard marker not found."

        )

    text = text.replace(

        marker,

        helper + marker,

        1,

    )

    print("REVIEW ID HELPER: OK")

else:

    print("REVIEW ID HELPER: ALREADY EXISTS")

# =========================================================

# 2. Replace saveReview conflict ID block

# =========================================================

old_start = '''    const conflictId = [

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

'''

if old_start in text:

    text = text.replace(

        old_start,

        '''    const conflictId =

      getReviewConflictId(match);

''',

        1,

    )

    print("SAVE CONFLICT ID: FIXED")

else:

    print(

        "SAVE CONFLICT ID: OLD BLOCK NOT FOUND "

        "(may already be patched)"

    )

# =========================================================

# 3. Replace restore conflict ID block

# =========================================================

old_restore = '''              const conflictId = [

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

'''

if old_restore in text:

    text = text.replace(

        old_restore,

        '''              const conflictId =

                getReviewConflictId(match);

              const legacyConflictId =

                getLegacyReviewConflictId(match);

              const review =

                reviewMap.get(conflictId) ||

                reviewMap.get(legacyConflictId);

''',

        1,

    )

    print("REFRESH CONFLICT ID: FIXED")

else:

    print(

        "REFRESH CONFLICT ID: OLD BLOCK NOT FOUND "

        "(may already be patched)"

    )

# =========================================================

# 4. Also fix review loading after Analyze

# =========================================================

old_analysis_restore = '''              const conflictId = [

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

'''

if old_analysis_restore in text:

    text = text.replace(

        old_analysis_restore,

        '''              const conflictId =

                getReviewConflictId(match);

              const legacyConflictId =

                getLegacyReviewConflictId(match);

              const review =

                reviewMap.get(conflictId) ||

                reviewMap.get(legacyConflictId);

''',

        1,

    )

    print("ANALYSIS REVIEW RESTORE: FIXED")

else:

    print(

        "ANALYSIS REVIEW RESTORE: OLD BLOCK NOT FOUND "

        "(may already be patched)"

    )

# =========================================================

# 5. Save

# =========================================================

path.write_text(

    text,

    encoding="utf-8",

)

print("")

print("======================================")

print("REVIEW CONFLICT ID PATCH COMPLETE")

print("======================================")