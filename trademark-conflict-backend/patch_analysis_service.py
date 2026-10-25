from __future__ import annotations

from pathlib import Path

from datetime import datetime

import py_compile

import shutil

import sys

# ============================================================

# CONFIG

# ============================================================

BASE_DIR = Path(__file__).resolve().parent

TARGET = (

    BASE_DIR

    / "app"

    / "services"

    / "analysis_service.py"

)

BACKUP_DIR = BASE_DIR / "patch_backups"

# ============================================================

# HELPERS

# ============================================================

def fail(message: str) -> None:

    print()

    print("[ERROR]")

    print(message)

    print()

    sys.exit(1)

def info(message: str) -> None:

    print(f"[PATCH] {message}")

def success(message: str) -> None:

    print(f"[OK]    {message}")

def backup_file() -> Path:

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup_path = (

        BACKUP_DIR

        / f"analysis_service.py.before_patch_{timestamp}.bak"

    )

    shutil.copy2(TARGET, backup_path)

    return backup_path

# ============================================================

# PATCH 1

# Ensure logo_matches is actually calculated before print

# ============================================================

def patch_logo_matches(source: str) -> tuple[str, bool]:

    marker = '''print("[5/8] Comparing trademark logos...")'''

    if marker not in source:

        fail(

            "Could not find the '[5/8] Comparing trademark logos...' "

            "section in analysis_service.py."

        )

    # --------------------------------------------------------

    # Already patched?

    # --------------------------------------------------------

    existing = '''logo_matches = self._compare_logos(

            pdf_logos,

            client_logos,

        )'''

    if existing in source:

        success(

            "Logo comparison assignment already exists. "

            "No duplicate inserted."

        )

        return source, False

    # --------------------------------------------------------

    # Look for the expected broken section

    # --------------------------------------------------------

    old_section = '''print("[5/8] Comparing trademark logos...")

        print(

            f"      Logo matches: "

            f"{len(logo_matches)}"

        )'''

    new_section = '''print("[5/8] Comparing trademark logos...")

        logo_matches = self._compare_logos(

            pdf_logos,

            client_logos,

        )

        print(

            f"      Logo matches: "

            f"{len(logo_matches)}"

        )'''

    if old_section in source:

        source = source.replace(

            old_section,

            new_section,

            1,

        )

        success(

            "Inserted logo comparison call: "

            "self._compare_logos(pdf_logos, client_logos)"

        )

        return source, True

    # --------------------------------------------------------

    # Flexible fallback

    # --------------------------------------------------------

    marker_index = source.find(marker)

    if marker_index == -1:

        fail("Logo comparison marker not found.")

    # Find next occurrence of logo_matches print

    logo_print = 'f"{len(logo_matches)}"'

    print_index = source.find(

        logo_print,

        marker_index,

    )

    if print_index == -1:

        fail(

            "Found logo comparison section, but could not locate "

            "the logo_matches print statement."

        )

    # Find beginning of the print() block

    print_start = source.rfind(

        "print(",

        marker_index,

        print_index,

    )

    if print_start == -1:

        fail(

            "Could not safely locate the Logo matches print block."

        )

    insertion = '''logo_matches = self._compare_logos(

            pdf_logos,

            client_logos,

        )

        '''

    source = (

        source[:print_start]
+ insertion

        + source[print_start:]

    )

    success(

        "Inserted logo comparison call using fallback detection."

    )

    return source, True

# ============================================================

# PATCH 2

# Fix type(error).name -> type(error).__name__

# ============================================================

def patch_exception_name(source: str) -> tuple[str, bool]:

    old = "type(error).name"

    new = "type(error).__name__"

    count = source.count(old)

    if count == 0:

        success(

            "No invalid 'type(error).name' expression found."

        )

        return source, False

    source = source.replace(old, new)

    success(

        f"Fixed {count} occurrence(s) of "

        "'type(error).name'."

    )

    return source, True

# ============================================================

# PATCH 3

# Verify result dictionary contains logo_match_details

# ============================================================

def check_result_fields(source: str) -> None:

    required_fields = [

        '"logo_matches": len(logo_matches)',

        '"logo_match_details": logo_matches',

    ]

    for field in required_fields:

        if field in source:

            success(f"Result field present: {field}")

        else:

            print(

                f"[WARN]  Result field not found: {field}"

            )

    # Do not automatically inject result fields here.

    # This is intentionally a safety check only.

# ============================================================

# COMPILE CHECK

# ============================================================

def compile_check() -> None:

    info("Running Python syntax check...")

    try:

        py_compile.compile(

            str(TARGET),

            doraise=True,

        )

    except py_compile.PyCompileError as exc:

        print()

        print(exc)

        fail(

            "Syntax check FAILED. "

            "The original file remains recoverable from the backup."

        )

    success(

        "analysis_service.py passed Python syntax check."

    )

# ============================================================

# MAIN

# ============================================================

def main() -> None:

    print()

    print("=" * 70)

    print(" Apexive AI - Trademark Conflict Detector")

    print(" analysis_service.py automatic patcher")

    print("=" * 70)

    print()

    if not TARGET.exists():

        fail(

            "analysis_service.py was not found:\n"

            f"{TARGET}"

        )

    info(f"Target file: {TARGET}")

    # --------------------------------------------------------

    # Read

    # --------------------------------------------------------

    try:

        source = TARGET.read_text(

            encoding="utf-8"

        )

    except UnicodeDecodeError:

        fail(

            "Could not read analysis_service.py as UTF-8."

        )

    original_source = source

    print()

    info("Creating automatic backup...")

    backup_path = backup_file()

    success(

        f"Backup created:\n{backup_path}"

    )

    # --------------------------------------------------------

    # Apply patches

    # --------------------------------------------------------

    print()

    info("Checking logo comparison section...")

    source, logo_changed = patch_logo_matches(source)

    print()

    info("Checking exception error-name bug...")

    source, exception_changed = patch_exception_name(source)

    print()

    info("Checking result fields...")

    check_result_fields(source)

    # --------------------------------------------------------

    # Write only when changed

    # --------------------------------------------------------

    if source == original_source:

        print()

        success(

            "No source changes were necessary."

        )

    else:

        print()

        info("Writing patched analysis_service.py...")

        TARGET.write_text(

            source,

            encoding="utf-8",
newline="",

        )

        success(

            "analysis_service.py updated successfully."

        )

    # --------------------------------------------------------

    # Compile

    # --------------------------------------------------------

    print()

    compile_check()

    # --------------------------------------------------------

    # Summary

    # --------------------------------------------------------

    print()

    print("=" * 70)

    print(" PATCH COMPLETE")

    print("=" * 70)

    print()

    print(f"Target : {TARGET}")

    print(f"Backup : {backup_path}")

    print()

    print("Changes:")

    if logo_changed:

        print("  [YES] Logo comparison call inserted")

    else:

        print("  [NO ] Logo comparison already present")

    if exception_changed:

        print("  [YES] type(error).__name__ fixed")

    else:

        print("  [NO ] Exception-name bug already fixed")

    print()

    print("Syntax:")

    print("  [PASS] analysis_service.py")

    print()

    print("Next step:")

    print("  Restart the backend and run one analysis job.")

    print()

if __name__ == "__main__":

    main()