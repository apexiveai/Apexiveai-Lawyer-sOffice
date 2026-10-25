from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.models.job import AnalysisJob


def get_accessible_job(
    job_id: str,
    principal: Principal,
    db: Session,
) -> AnalysisJob:
    job = db.execute(
        select(AnalysisJob).where(
            AnalysisJob.job_id == job_id,
            AnalysisJob.tenant_id == principal.tenant_id,
        )
    ).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Analysis job not found.")
    return job
