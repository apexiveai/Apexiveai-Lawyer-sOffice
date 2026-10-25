from pathlib import Path

from datetime import datetime

import shutil

import re

ROOT = Path(__file__).resolve().parent

TARGET = ROOT / "app" / "services" / "analysis_service.py"

def main():

    print("=" * 70)

    print("TRADEMARK CONFLICT DETECTOR")

    print("ANALYSIS RESULT PERSISTENCE PATCH")

    print("=" * 70)

    text = TARGET.read_text(encoding="utf-8-sig")

    # ------------------------------------------------------------

    # Backup

    # ------------------------------------------------------------

    backup_dir = ROOT / "patch_backups"

    backup_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup = (

        backup_dir

        / f"analysis_service.before_result_persistence_{stamp}.py"

    )

    shutil.copy2(TARGET, backup)

    print(f"[BACKUP] {backup}")

    # ------------------------------------------------------------

    # Make sure json is imported

    # ------------------------------------------------------------

    if "import json" not in text:

        text = "import json\n" + text

        print("[YES] Added json import")

    else:

        print("[OK ] json import already exists")

    # ------------------------------------------------------------

    # Find the final result return

    # ------------------------------------------------------------

    marker = '        result = {\n'

    if marker not in text:

        raise RuntimeError(

            "Could not find final result = { block."

        )

    # Find the LAST occurrence because this is the run() result.

    result_pos = text.rfind(marker)

    if result_pos < 0:

        raise RuntimeError(

            "Final result block not found."

        )

    # Find "return result" after the result block.

    return_pos = text.find(

        "        return result",

        result_pos,

    )

    if return_pos < 0:

        raise RuntimeError(

            "Could not find 'return result'."

        )

    # ------------------------------------------------------------

    # Avoid duplicate patch

    # ------------------------------------------------------------

    if "analysis_result.json" in text:

        print("[OK ] Result persistence already exists")

    else:

        persistence = '''

        # --------------------------------------------------------

        # Persist complete analysis result

        # --------------------------------------------------------

        try:

            result_path = (

                self.evidence_dir /

                "analysis_result.json"

            )

            result_path.write_text(

                json.dumps(

                    result,

                    ensure_ascii=False,

                    indent=2,

                    default=str,

                ),

                encoding="utf-8",

            )

            print(

                f"      Result saved: "

                f"{result_path}"

            )

        except Exception as error:

            print(

                "      Result persistence warning: "

                f"{type(error).__name__}: {error}"

            )

'''

        text = (

            text[:return_pos]

            + persistence

            + text[return_pos:]

        )

        print("[YES] Added analysis_result.json persistence")

    # ------------------------------------------------------------

    # Write + syntax check

    # ------------------------------------------------------------

    TARGET.write_text(

        text,

        encoding="utf-8",

    )

    compile(

        text,

        str(TARGET),

        "exec",

    )

    print("[PASS] analysis_service.py syntax")

    print("=" * 70)

    print("PATCH COMPLETE")

    print("=" * 70)

if __name__ == "__main__":

    main()