from pathlib import Path

path = Path("src/App.tsx")

text = path.read_text(encoding="utf-8")

# =========================================================

# 1. Add search/filter state

# =========================================================

matches_marker = "  const matches = Array.isArray(analysis?.matches)"

if matches_marker not in text:

    raise SystemExit("ERROR: const matches marker not found")

if "const [matchSearch" not in text:

    text = text.replace(

        matches_marker,

        """  const [matchSearch, setMatchSearch] = useState("");

  const [matchFilter, setMatchFilter] = useState("ALL");

""" + matches_marker,

        1,

    )

# =========================================================

# 2. Replace matches block using line positions

# =========================================================

start = text.find("  const matches = Array.isArray(analysis?.matches)")

if start == -1:

    raise SystemExit("ERROR: matches block start not found")

end = text.find(

    "  const clientIsPdf = clientFile?.name",

    start,

)

if end == -1:

    raise SystemExit("ERROR: matches block end not found")

new_logic = """  const matches = Array.isArray(analysis?.matches)

    ? analysis.matches

    : [];

  const filteredMatches = matches.filter(

    (match: Record<string, any>) => {

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

"""

text = text[:start] + new_logic + text[end:]

# =========================================================

# 3. Add search/filter UI

# =========================================================

conditional_marker = "          {!analysis ? ("

if conditional_marker not in text:

    raise SystemExit(

        "ERROR: evidence conditional marker not found"

    )

if "className=\"match-controls\"" not in text:

    controls = """          <div className="match-controls">

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

"""

    text = text.replace(

        conditional_marker,

        controls + conditional_marker,

        1,

    )

# =========================================================

# 4. Only modify matches-section

# =========================================================

section_start = text.find(

    '<section className="matches-section">'

)

if section_start == -1:

    raise SystemExit(

        "ERROR: matches-section not found"

    )

section_end = text.find(

    "</section>",

    section_start,

)

if section_end == -1:

    raise SystemExit(

        "ERROR: matches-section closing tag not found"

    )

section = text[section_start:section_end]

section = section.replace(

    "matches.length === 0",

    "filteredMatches.length === 0",

    1,

)

section = section.replace(

    "{matches.map(",

    "{filteredMatches.map(",

    1,

)

text = (

    text[:section_start]

    + section

    + text[section_end:]

)

path.write_text(text, encoding="utf-8")

print("SEARCH STATE: OK")

print("FILTER LOGIC: OK")

print("SEARCH UI: OK")

print("FILTER UI: OK")

print("RESULT LIST: FILTERED")

print("PATCHED OK")