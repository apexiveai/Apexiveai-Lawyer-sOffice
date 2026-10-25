from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from pydantic import BaseModel, Field

from sqlalchemy import select

from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.core.auth import Principal, require_roles
from app.core.authorization import get_accessible_job
from app.db.database import get_db

from app.models.review import Review

router = APIRouter(

    prefix="/api/reviews",

    tags=["Human Review"],

)

class ReviewRequest(BaseModel):

    job_id: str = Field(min_length=1, max_length=64)

    conflict_id: str = Field(min_length=1, max_length=255)

    status: str = Field(default="PENDING")

    comment: str = Field(default="")

    reviewer: str = Field(default="Admin")

class ReviewResponse(BaseModel):

    id: int

    job_id: str

    conflict_id: str

    status: str

    comment: str

    reviewer: str

    reviewed_at: datetime

    created_at: datetime

def _validate_status(status: str) -> str:

    normalized = status.strip().upper()

    if normalized not in {

        "PENDING",

        "CONFIRMED",

        "REJECTED",

    }:

        raise HTTPException(

            status_code=400,

            detail=(

                "Invalid review status. "

                "Use PENDING, CONFIRMED, or REJECTED."

            ),

        )

    return normalized

def _serialize(review: Review) -> ReviewResponse:

    return ReviewResponse(

        id=review.id,

        job_id=review.job_id,

        conflict_id=review.conflict_id,

        status=review.status,

        comment=review.comment,

        reviewer=review.reviewer,

        reviewed_at=review.reviewed_at,

        created_at=review.created_at,

    )

@router.post("", response_model=ReviewResponse)

def save_review(

    payload: ReviewRequest,

    principal: Principal = Depends(require_roles("reviewer", "admin")),
    db: Session = Depends(get_db),

):

    get_accessible_job(payload.job_id, principal, db)
    status = _validate_status(payload.status)

    existing = db.execute(

        select(Review).where(

            Review.job_id == payload.job_id,

            Review.conflict_id == payload.conflict_id,

        )

    ).scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if existing:

        existing.status = status

        existing.comment = payload.comment.strip()

        existing.reviewer = principal.subject
        existing.reviewed_at = now
        record_audit_event(
            db, principal, "review.updated", payload.job_id,
            {"conflict_id": payload.conflict_id, "status": status},
        )

        db.commit()

        db.refresh(existing)

        return _serialize(existing)

    review = Review(

        job_id=payload.job_id,

        conflict_id=payload.conflict_id,

        status=status,

        comment=payload.comment.strip(),

        reviewer=principal.subject,

        reviewed_at=now,

        created_at=now,

    )

    db.add(review)
    record_audit_event(
        db, principal, "review.created", payload.job_id,
        {"conflict_id": payload.conflict_id, "status": status},
    )

    db.commit()

    db.refresh(review)

    return _serialize(review)

@router.get("/{job_id}", response_model=list[ReviewResponse])

def get_reviews(

    job_id: str,

    principal: Principal = Depends(
        require_roles("analyst", "reviewer", "admin")
    ),
    db: Session = Depends(get_db),

):

    get_accessible_job(job_id, principal, db)
    reviews = db.execute(

        select(Review)

        .where(Review.job_id == job_id)

        .order_by(Review.id.asc())

    ).scalars().all()

    return [

        _serialize(review)

        for review in reviews

    ]