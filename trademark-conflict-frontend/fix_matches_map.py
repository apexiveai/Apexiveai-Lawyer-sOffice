from pathlib import Path

path = Path("src/App.tsx")

text = path.read_text(encoding="utf-8")

start_marker = "{matches.map("

start = text.find(start_marker)

if start == -1:

    raise SystemExit("ERROR: matches.map() not found")

# Find the matches-list closing div after the map.

end_marker = """

            </div>

          )}

        </section>

"""

end = text.find(end_marker, start)

if end == -1:

    raise SystemExit("ERROR: matches-list closing block not found")

new_map = """{matches.map(

                (

                  match: Record<string, any>,

                  index: number

                ) => (

                  match.match_type === "LOGO MATCH" ||

                  match.matchType === "LOGO MATCH" ||

                  match.type === "LOGO MATCH" ? (

                    <LogoMatchCard

                      key={`logo-${index}`}

                      match={match}

                      jobId={analysis?.job_id || ""}

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

                    />

                  )

                )

              )}"""

text = text[:start] + new_map + text[end:]

path.write_text(text, encoding="utf-8")

print("MATCHES MAP REBUILT")

print("LOGO MATCH CARD ENABLED")

print("PATCHED OK")