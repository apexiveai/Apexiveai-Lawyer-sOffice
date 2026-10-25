from __future__ import annotations

import json

import os

from pathlib import Path

from typing import Any, Dict, List, Optional

from app.core.config import EVIDENCE_DIR

from app.services.ai_assistant.prompts import SYSTEM_PROMPT

class TrademarkAssistant:

    """

    Analysis-aware assistant.

    Phase 1:

        Reads the persisted analysis_result.json directly.

    Phase 2:

        This service will use MCP tools for tool-calling.

    """

    def __init__(self) -> None:

        self.model = os.getenv(

            "AI_MODEL",

            os.getenv("CEREBRAS_MODEL", "llama-3.3-70b"),

        )

    # --------------------------------------------------------

    # Load analysis

    # --------------------------------------------------------

    def _result_paths(self, job_id: str) -> List[Path]:

        directory = EVIDENCE_DIR / job_id

        return [

            directory / "analysis_result.json",

            directory / "result.json",

        ]

    def load_analysis(self, job_id: str) -> Optional[Dict[str, Any]]:

        for path in self._result_paths(job_id):

            if not path.exists():

                continue

            try:

                with path.open("r", encoding="utf-8") as file:

                    data = json.load(file)

                if isinstance(data, dict):

                    return data

            except Exception:

                continue

        return None

    # --------------------------------------------------------

    # Build compact context

    # --------------------------------------------------------

    def build_context(

        self,

        job_id: str,

        result: Dict[str, Any],

    ) -> Dict[str, Any]:

        context: Dict[str, Any] = {

            "job_id": job_id,

            "summary": {

                "pdf_pages": result.get("pdf_pages", 0),

                "client_records": result.get("client_records", 0),

                "pdf_logos": result.get("pdf_logos", 0),

                "xlsx_logos": result.get("xlsx_logos", 0),

                "application_matches": result.get(

                    "application_matches", 0

                ),

                "logo_matches": result.get(

                    "logo_matches", 0

                ),

                "company_matches": result.get(

                    "company_matches", 0

                ),

                "phone_matches": result.get(

                    "phone_matches", 0

                ),

            },

            "application_matches": result.get(

                "application_match_details", []

            ),

            "logo_matches": result.get(

                "logo_match_details", []

            ),

            "company_matches": result.get(

                "company_match_details", []

            ),

            "phone_matches": result.get(

                "phone_match_details", []

            ),

            "matches": result.get(

                "matches", []

            ),

        }

        return context

    # --------------------------------------------------------

    # Local deterministic response

    #

    # This gives us a working Assistant immediately even

    # before connecting an external LLM.

    # --------------------------------------------------------

    def answer_from_analysis(

        self,

        job_id: str,

        question: str,

    ) -> Dict[str, Any]:

        result = self.load_analysis(job_id)

        if result is None:

            return {

                "job_id": job_id,

                "answer": (

                    "No completed analysis result was found for "

                    f"job {job_id}."

                ),

                "source": "analysis_result.json",

                "tool_calls": [],

            }

        context = self.build_context(job_id, result)
        summary = context["summary"]
        q = question.lower().strip()
        tool_calls: list[dict[str, Any]] = []

        # Summary
        if any(
            word in q
            for word in [
                "summary",
                "how many",
                "count",
                "total",
            ]
        ) and "logo" not in q:
            tool_calls.append({
                "tool": "get_analysis_summary",
                "arguments": {"job_id": job_id},
            })

            answer = (

                "Analysis summary:\n\n"

                f"• PDF pages: {summary['pdf_pages']}\n"

                f"• Client records: {summary['client_records']}\n"

                f"• Application matches: "

                f"{summary['application_matches']}\n"

                f"• Logo matches: "

                f"{summary['logo_matches']}\n"

                f"• Company matches: "

                f"{summary['company_matches']}\n"

                f"• Phone matches: "

                f"{summary['phone_matches']}"

            )

        # Evidence explanation
        elif any(word in q for word in ["why", "flagged", "evidence", "reason"]):
            items = context["matches"]
            tool_calls.append({
                "tool": "get_conflict_evidence",
                "arguments": {"job_id": job_id, "match_index": 0},
            })
            if not items:
                answer = "No conflict evidence is available for this analysis."
            else:
                item = items[0]
                answer = (
                    f"This trademark was flagged as {item.get('match_type', 'CONFLICT')}.\n\n"
                    f"Application: {item.get('application_no') or 'N/A'}\n"
                    f"PDF page: {item.get('pdf_page') or 'N/A'}\n"
                    f"Company: {item.get('company') or 'N/A'}\n"
                    f"Evidence: "
                    f"{'FOUND' if item.get('pdf_evidence') or item.get('client_evidence') else 'NOT FOUND'}"
                )

        # Search
        elif q.startswith("find ") or q.startswith("search "):
            query = q.split(" ", 1)[1].strip()
            query = query.removesuffix(" conflicts").removesuffix(" conflict").strip()
            items = [
                item for item in context["matches"]
                if query in " ".join(
                    str(item.get(key, ""))
                    for key in (
                        "match_type", "application_no", "company",
                        "client", "mark", "phone",
                    )
                ).lower()
            ]
            tool_calls.append({
                "tool": "search_trademark_conflicts",
                "arguments": {"job_id": job_id, "query": query},
            })
            answer = (
                f"Search results for {query}: {len(items)} match(es)\n\n"
                + "\n".join(
                    f"{index}. {item.get('match_type', 'CONFLICT')} - "
                    f"{item.get('company') or item.get('mark') or 'N/A'}"
                    for index, item in enumerate(items[:20], start=1)
                )
            )

        # Logo
        elif "logo" in q:

            logo_matches = [
                item
                for item in context["matches"]
                if "logo" in str(item.get("match_type", "")).lower()
            ]
            tool_calls.append({
                "tool": "get_logo_matches",
                "arguments": {"job_id": job_id},
            })

            if not logo_matches:

                answer = (

                    "No logo matches met the current matching "

                    "criteria in this analysis."

                )

            else:

                lines = [

                    f"Logo matches found: {len(logo_matches)}",

                    "",

                ]

                for index, item in enumerate(

                    logo_matches[:10],

                    start=1,

                ):

                    similarity = (

                        item.get("similarity_percent")

                        or item.get("similarity")

                        or item.get("score")

                        or "N/A"

                    )

                    page = (

                        item.get("pdf_page")

                        or item.get("page")

                        or "N/A"

                    )

                    row = (

                        item.get("client_row")

                        or item.get("row")

                        or "N/A"

                    )

                    owner = (

                        item.get("client_owner")

                        or item.get("owner")

                        or item.get("company")

                        or "N/A"

                    )

                    lines.append(
f"LOGO MATCH {index}\n"
f"   Similarity: {similarity} | "
f"PDF Page: {page} | "
f"Client Row: {row} | "
f"Owner: {owner}\n"
f"   Text Match: {item.get('text_match', 'N/A')} | "
f"Visual Match: {item.get('visual_match', 'N/A')} | "
f"Evidence: "
f"{'FOUND' if item.get('pdf_evidence') or item.get('client_evidence') else 'NOT FOUND'}"
                    )

                answer = "\n".join(lines)

        # Application

        elif "application" in q:
            items = context["application_matches"]
            tool_calls.append({
                "tool": "get_application_matches",
                "arguments": {"job_id": job_id},
            })

            if not items:

                answer = (

                    "No application-number matches were found "

                    "in this analysis."

                )

            else:

                lines = [

                    f"Application matches found: {len(items)}",

                    "",

                ]

                for item in items[:20]:

                    lines.append(

                        str(item)

                    )

                answer = "\n".join(lines)

        # Company

        elif "company" in q or "owner" in q:
            items = context["company_matches"]
            tool_calls.append({
                "tool": "get_company_matches",
                "arguments": {"job_id": job_id},
            })

            if not items:

                answer = (

                    "No company-name matches were found."

                )

            else:

                lines = [

                    f"Company matches found: {len(items)}",

                    "",

                ]

                for index, item in enumerate(

                    items[:20],

                    start=1,

                ):

                    lines.append(

                        f"{index}. {item}"

                    )

                answer = "\n".join(lines)

        # Phone

        elif "phone" in q or "telephone" in q or "mobile" in q:
            items = context["phone_matches"]
            tool_calls.append({
                "tool": "get_phone_matches",
                "arguments": {"job_id": job_id},
            })

            if not items:

                answer = (

                    "No phone-number matches were found."

                )

            else:
                tool_calls.append({
                    "tool": "get_all_conflicts",
                    "arguments": {"job_id": job_id},
                })

                answer = (

                    f"Phone matches found: {len(items)}\n\n"

                    + "\n".join(

                        str(item)

                        for item in items[:20]

                    )

                )

        else:

            answer = (

                "I can analyze this trademark job. You can ask "

                "about:\n\n"

                "• analysis summary\n"

                "• logo matches\n"

                "• application matches\n"

                "• company matches\n"

                "• phone matches\n"

                "• conflict evidence\n"

                "• specific trademark owners or application numbers"

            )

        return {

            "job_id": job_id,

            "answer": answer,

            "source": "analysis_result.json",

            "tool_calls": tool_calls,

            "context": context,

        }

assistant = TrademarkAssistant()
