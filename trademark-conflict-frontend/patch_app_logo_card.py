from pathlib import Path

import re

path = Path("src/App.tsx")

text = path.read_text(encoding="utf-8")

# ---------------------------------------------------------

# 1. Add LogoMatchCard import

# ---------------------------------------------------------

if "LogoMatchCard" not in text:

    match = re.search(

        r'import\s+MatchCard\s+from\s+["\']([^"\']+)["\'];?',

        text

    )

    if match:

        match_import_path = match.group(1)

        if "/" in match_import_path:

            base = match_import_path.rsplit("/", 1)[0]

            logo_import_path = f"{base}/LogoMatchCard"

        else:

            logo_import_path = "./components/LogoMatchCard"

        import_line = (

            f'import LogoMatchCard from "{logo_import_path}";\n'

        )

        text = text[:match.end()] + "\n" + import_line + text[match.end():]

    else:

        # Fallback: add after React imports

        text = (

            'import LogoMatchCard from "./components/LogoMatchCard";\n'

            + text

        )

# ---------------------------------------------------------

# 2. Replace MatchCard render inside matches.map()

# ---------------------------------------------------------

pattern = re.compile(

    r'<MatchCard\s+'

    r'key=\{\$\{index\}-\$\{getMatchValue\(\s*'

    r'match,\s*'

    r'\[\s*'

    r'"application_no",\s*'

    r'"application_number",\s*'

    r'"application"\s*'

    r'\]\s*'

    r'\)\}\}\s*'

    r'match=\{match\}\s*'

    r'index=\{index\}\s*'

    r'jobId=\{analysis\?\.job_id\}\s*'

    r'clientIsPdf=\{clientIsPdf\}\s*'

    r'leftIsXlsx=\{leftIsXlsx\}\s*'

    r'/>',

    re.MULTILINE

)

replacement = r'''match.match_type === "LOGO MATCH" ||

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

)'''

text, count = pattern.subn(replacement, text, count=1)

if count == 0:

    print("WARNING: MatchCard block was not replaced.")

else:

    print("MATCH CARD PATCHED")

path.write_text(text, encoding="utf-8")

print("PATCHED OK")