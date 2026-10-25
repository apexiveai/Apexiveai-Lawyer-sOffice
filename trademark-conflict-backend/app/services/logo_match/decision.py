from __future__ import annotations

from .exact_text import exact_logo_text_match

def decide_logo_match(

    pdf_text: str | None,

    client_text: str | None,

    visual_similarity: float,

    threshold: float = 0.82,

) -> dict:

    """

    Final logo conflict decision.

    Rules:

    1. Text exists on both sides:

       text must match EXACTLY.

    2. Text does not exist:

       visual similarity is used.

    3. Text mismatch always blocks the logo match.

    """

    text_result = exact_logo_text_match(

        pdf_text,

        client_text,

    )

    similarity = float(visual_similarity)

    if text_result["text_match"] == "NOT_MATCH":

        return {

            "logo_match": False,

            "visual_match": similarity >= threshold,

            "visual_similarity": round(similarity * 100, 2),

            "text_match": "NOT_MATCH",

            "decision": "REJECTED_TEXT_MISMATCH",

            "reason": "Logo text is not exactly identical.",

            "pdf_text": text_result["pdf_text"],

            "client_text": text_result["client_text"],

            "pdf_normalized": text_result["pdf_normalized"],

            "client_normalized": text_result["client_normalized"],

        }

    if text_result["text_match"] == "EXACT":

        visual_match = similarity >= threshold

        return {

            "logo_match": bool(visual_match),

            "visual_match": bool(visual_match),

            "visual_similarity": round(similarity * 100, 2),

            "text_match": "EXACT",

            "decision": (

                "CONFIRMED"

                if visual_match

                else "TEXT_EXACT_VISUAL_LOW"

            ),

            "reason": (

                "Text is exact and visual similarity "

                "passes the configured threshold."

                if visual_match

                else "Text is exact but visual similarity is below threshold."

            ),

            "pdf_text": text_result["pdf_text"],

            "client_text": text_result["client_text"],

            "pdf_normalized": text_result["pdf_normalized"],

            "client_normalized": text_result["client_normalized"],

        }

    # No readable text on either side.

    visual_match = similarity >= threshold

    return {

        "logo_match": bool(visual_match),

        "visual_match": bool(visual_match),

        "visual_similarity": round(similarity * 100, 2),

        "text_match": "NO_TEXT",

        "decision": (

            "VISUAL_CONFIRMED"

            if visual_match

            else "VISUAL_LOW"

        ),

        "reason": (

            "No readable trademark text was detected; "

            "visual identity was evaluated."

        ),

        "pdf_text": text_result["pdf_text"],

        "client_text": text_result["client_text"],

        "pdf_normalized": text_result["pdf_normalized"],

        "client_normalized": text_result["client_normalized"],

    }