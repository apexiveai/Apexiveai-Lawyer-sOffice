from pathlib import Path

import py_compile

ROOT = Path(__file__).resolve().parent

# ============================================================

# 1. Create AI Assistant package

# ============================================================

assistant_dir = ROOT / "app" / "services" / "ai_assistant"

assistant_dir.mkdir(parents=True, exist_ok=True)

init_file = assistant_dir / "__init__.py"

init_file.write_text(

    '"""Trademark AI Assistant service."""\n',

    encoding="utf-8",

)

# ============================================================

# 2. prompts.py

# ============================================================

prompts_file = assistant_dir / "prompts.py"

prompts_file.write_text(

'''SYSTEM_PROMPT = """

You are Trademark Intelligence Assistant for a professional

Trademark Conflict Detection system.

Your job is to explain trademark analysis results using ONLY

the data supplied by the application.

Important rules:

- Never invent application numbers.

- Never invent similarity scores.

- Never claim a conflict exists unless the supplied analysis

  identifies it as a match/conflict.

- Clearly distinguish SIMILARITY from CONFIRMED MATCH.

- The current logo matching threshold is supplied by the system.

- When evidence is available, mention the PDF page and client row.

- Be concise, professional and suitable for legal/business users.

- If the requested information is not available, say so.

You can explain:

- Analysis summary

- Application matches

- Logo matches

- Company matches

- Phone matches

- Conflict reasons

- Evidence

- Similarity results

"""

''',

    encoding="utf-8",

)

# ============================================================

# 3. assistant.py

# ============================================================

assistant_file = assistant_dir / "assistant.py"

assistant_file.write_text(

r'''from __future__ import annotations

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

        # Summary

        if any(

            word in q

            for word in [

                "summary",

                "how many",

                "count",

                "total",

                "conflicts",

            ]

        ):

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

        # Logo

        elif "logo" in q:

            logo_matches = context["logo_matches"]

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

                        f"{index}. Similarity: {similarity} | "
f"PDF Page: {page} | "

                        f"Client Row: {row} | "

                        f"Owner: {owner}"

                    )

                answer = "\n".join(lines)

        # Application

        elif "application" in q:

            items = context["application_matches"]

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

            if not items:

                answer = (

                    "No phone-number matches were found."

                )

            else:

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

            "tool_calls": [],

            "context": context,

        }

assistant = TrademarkAssistant()

''',

    encoding="utf-8",

)

# ============================================================

# 4. assistant API

# ============================================================

api_file = ROOT / "app" / "api" / "assistant.py"

api_file.write_text(

r'''from

          import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from pydantic import BaseModel, Field

from app.services.ai_assistant.assistant import assistant

router = APIRouter(

    prefix="/api/assistant",

    tags=["AI Assistant"],

)

class AssistantRequest(BaseModel):

    job_id: str = Field(..., min_length=1)

    message: str = Field(..., min_length=1, max_length=5000)

@router.post("/chat")

async def assistant_chat(

    request: AssistantRequest,

) -> Dict[str, Any]:

    try:

        return assistant.answer_from_analysis(

            job_id=request.job_id,

            question=request.message,

        )

    except Exception as error:

        raise HTTPException(

            status_code=500,

            detail=str(error),

        )

''',

    encoding="utf-8",

)

# ============================================================

# 5. Patch main.py

# ============================================================

main_file = ROOT / "app" / "main.py"

if not main_file.exists():

    raise SystemExit(

        f"[ERROR] main.py not found: {main_file}"

    )

main_text = main_file.read_text(

    encoding="utf-8-sig"

)

if "from app.api.assistant import router as assistant_router" not in main_text:

    marker = "from app.api."

    lines = main_text.splitlines()

    insert_at = 0

    for index, line in enumerate(lines):

        if line.startswith("from app.api."):

            insert_at = index

            break

    lines.insert(

        insert_at,

        "from app.api.assistant import router as assistant_router",

    )

    main_text = "\n".join(lines) + "\n"

if "include_router(assistant_router)" not in main_text:

    # Put the router after existing include_router calls.

    lines = main_text.splitlines()

    insert_index = None

    for index, line in enumerate(lines):

        if "include_router(" in line:

            insert_index = index + 1

    if insert_index is None:

        lines.append(

            "app.include_router(assistant_router)"

        )

    else:

        lines.insert(

            insert_index,

            "app.include_router(assistant_router)"

        )

    main_text = "\n".join(lines) + "\n"

main_file.write_text(

    main_text,

    encoding="utf-8",

)

# ============================================================

# 6. Syntax checks

# ============================================================

targets = [

    assistant_dir / "__init__.py",

    prompts_file,

    assistant_file,

    api_file,

    main_file,

]

print()

print("=" * 60)

print("AI ASSISTANT PATCH")

print("=" * 60)

for target in targets:

    try:

        py_compile.compile(

            str(target),

            doraise=True,

        )

        print(f"[PASS] {target}")

    except Exception as error:

        print(f"[FAIL] {target}")

        print(error)

        raise

print()

print("=" * 60)

print("AI ASSISTANT PATCH COMPLETE")

print("=" * 60)

print()

print("New endpoint:")

print("POST /api/assistant/chat")