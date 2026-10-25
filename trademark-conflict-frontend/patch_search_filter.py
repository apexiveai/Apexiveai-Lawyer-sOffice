from pathlib import Path

path = Path("src/App.tsx")

text = path.read_text(encoding="utf-8")

# ---------------------------------------------------------

# 1. Add search/filter state before "const matches"

# ---------------------------------------------------------

marker = """  const matches = Array.isArray(analysis?.matches)"""

if marker not in text:

    raise SystemExit("ERROR: const matches marker not found")

state_block = """  const [matchSearch, setMatchSearch] = useState("");

  const [matchFilter, setMatchFilter] = useState("ALL");

"""

if "const [matchSearch" not in text:

    text = text.replace(marker, state_block + marker, 1)

# ---------------------------------------------------------

# 2. Replace the matches derived block

# ---------------------------------------------------------

old_block = """  const matches = Array.isArray(analysis?.matches)

    ? analysis.matches

    : [];

"""

new_block = """  const matches = Array.isArray(analysis?.matches)

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

if old_block not in text:

    raise SystemExit("ERROR: Original matches block not found")

text = text.replace(old_block, new_block, 1)

# ---------------------------------------------------------

# 3. Insert search/filter controls before empty-results logic

# ---------------------------------------------------------

marker2 = """          {!analysis ? (

"""

if marker2 not in text:

    raise SystemExit("ERROR: Evidence result conditional not found")

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

            {(matchSearch || matchFilter !== "ALL") && (

              <div className="filter-summary">

                Showing{" "}

                <strong>{filteredMatches.length}</strong>{" "}

                of{" "}

                <strong>{matches.length}</strong>{" "}

                conflicts

              </div>

            )}

          </div>

"""

text = text.replace(marker2, controls + marker2, 1)

# ---------------------------------------------------------

# 4. Use filteredMatches for result empty/map logic

# ---------------------------------------------------------

# Only replace the occurrences in the evidence section.

section_start = text.find('<section className="matches-section">')

if section_start == -1:

    raise SystemExit("ERROR: matches-section not found")

section_end = text.find("</section>", section_start)

if section_end == -1:

    raise SystemExit("ERROR: matches-section closing tag not found")

section = text[section_start:section_end]

section = section.replace(

    ") : matches.length === 0 ? (",

    ") : filteredMatches.length === 0 ? (",

    1

)

section = section.replace(

    "{matches.map(",

    "{filteredMatches.map(",

    1

)

text = (

    text[:section_start]

    + section

    + text[section_end:]

)

path.write_text(text, encoding="utf-8")

print("SEARCH STATE ADDED")

print("FILTER LOGIC ADDED")

print("SEARCH UI ADDED")

print("FILTER UI ADDED")

print("PATCHED OK")