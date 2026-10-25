from pathlib import Path

path = Path("src/App.tsx")

text = path.read_text(encoding="utf-8")

start = text.find("{match.match_type === \"LOGO MATCH\"")

if start == -1:

    raise SystemExit("ERROR: Broken LogoMatch block not found")

# Find the end of the broken conditional.

# It ends immediately before the closing of matches.map().

end_marker = """

              )}

"""

end = text.find(end_marker, start)

if end == -1:

    raise SystemExit("ERROR: End of matches.map() not found")

new_block = """              {match.match_type === "LOGO MATCH" ||

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

              )}

"""

text = text[:start] + new_block + text[end:]

path.write_text(text, encoding="utf-8")

print("FIXED LOGO MATCH JSX")

print("PATCHED OK")