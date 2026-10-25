from __future__ import annotations

import re
import unicodedata

from typing import Iterable

def normalize_logo_text(value: str | None) -> str:

    """

    Normalize OCR/logo text for exact trademark comparison.

    Examples:

        SAILUN        -> SAILUN

        Sailun Group  -> SAILUNGROUP

        SAILUN-GROUP  -> SAILUNGROUP

    """

    if value is None:

        return ""

    # Remove trademark decorations before compatibility normalization, which
    # otherwise turns ™ into "TM" and ® into "(R)".
    text = str(value).replace("®", "").replace("™", "")
    text = unicodedata.normalize("NFKC", text).casefold()

    # Keep letters, numbers, and combining marks from every script. Myanmar
    # vowels/medials are combining marks and must not be discarded.
    return "".join(
        character
        for character in text
        if unicodedata.category(character)[0] in {"L", "N", "M"}
    )

def extract_tokens(value: str | None) -> list[str]:

    if not value:

        return []

    text = str(value).upper()

    return re.findall(r"[A-Z0-9]+", text)

def exact_logo_text_match(

    pdf_text: str | None,

    client_text: str | None,

) -> dict:

    """

    Strict text verification.

    SAILUN vs SAILUN  -> EXACT

    SAILUN GROUP vs Sailun Group -> EXACT

    SAILUN vs SAILUNN -> NOT_MATCH

    """

    pdf_normalized = normalize_logo_text(pdf_text)

    client_normalized = normalize_logo_text(client_text)

    if not pdf_normalized or not client_normalized:

        return {

            "has_text": False,

            "text_match": "NO_TEXT",

            "pdf_text": pdf_text or "",

            "client_text": client_text or "",

            "pdf_normalized": pdf_normalized,

            "client_normalized": client_normalized,

        }

    exact = pdf_normalized == client_normalized

    return {

        "has_text": True,

        "text_match": "EXACT" if exact else "NOT_MATCH",

        "pdf_text": pdf_text or "",

        "client_text": client_text or "",

        "pdf_normalized": pdf_normalized,

        "client_normalized": client_normalized,

    }

def collect_text_candidates(values: Iterable[str | None]) -> list[str]:

    result = []

    for value in values:

        normalized = normalize_logo_text(value)

        if normalized and normalized not in result:

            result.append(normalized)

    return result

def any_exact_text_match(

    pdf_candidates: Iterable[str | None],

    client_candidates: Iterable[str | None],

) -> bool:

    pdf_normalized = set(

        collect_text_candidates(pdf_candidates)

    )

    client_normalized = set(

        collect_text_candidates(client_candidates)

    )

    if not pdf_normalized or not client_normalized:

        return False

    return bool(pdf_normalized.intersection(client_normalized))