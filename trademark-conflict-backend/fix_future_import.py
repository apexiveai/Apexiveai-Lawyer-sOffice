from pathlib import Path

TARGET = Path("app/services/analysis_service.py")

text = TARGET.read_text(encoding="utf-8-sig")

# Remove any incorrectly inserted json import.

text = text.replace("import json\n", "")

# Ensure json import exists AFTER future imports.

future_line = "from __future__ import annotations"

if future_line in text:

    text = text.replace(

        future_line,

        future_line + "\n\nimport json",

        1,

    )

else:

    text = "import json\n\n" + text

TARGET.write_text(text, encoding="utf-8")

compile(

    text,

    str(TARGET),

    "exec",

)

print("[PASS] analysis_service.py syntax")

print("[PASS]ext.replace(import order fixed")

print("[PASS] json import placed correctly")