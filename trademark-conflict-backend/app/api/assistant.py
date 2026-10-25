from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from pydantic import BaseModel, Field

from app.core.auth import Principal, require_roles
from app.core.authorization import get_accessible_job
from app.db.database import get_db
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
    principal: Principal = Depends(
        require_roles("analyst", "reviewer", "admin")
    ),
    db: Session = Depends(get_db),

) -> Dict[str, Any]:

    get_accessible_job(request.job_id, principal, db)
    return assistant.answer_from_analysis(
        job_id=request.job_id,
        question=request.message,
    )
