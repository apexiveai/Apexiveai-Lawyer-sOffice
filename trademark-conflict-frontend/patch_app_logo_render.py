from pathlib import Path

path = Path("src/App.tsx")

text = path.read_text(encoding="utf-8")

start_marker = "<MatchCard\n"

start = text.find(start_marker)

if start == -1:

    raise SystemExit("ERROR: <MatchCard not found")

# Find the end of this MatchCard JSX

end = text.find("/>", start)

if end == -1:

    raise SystemExit("ERROR: MatchCard closing /> not found")

end += 2

old_block = text[start:end]

new_block = """{match.match_type === "LOGO MATCH" ||

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

)}"""

text = text[:start] + new_block + text[end:]

path.write_text(text, encoding="utf-8")

print("LOGO MATCH RENDER PATCHED")

print("PATCHED OK")