from fastapi import APIRouter, Depends, HTTPException

from fastapi.responses import FileResponse

from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.core.auth import Principal, require_roles
from app.core.authorization import get_accessible_job
from app.db.database import get_db

from app.models.report import Report

from app.services.report_service import TrademarkConflictReportService

router = APIRouter(

    prefix="/api/reports",

    tags=["reports"],

)

@router.post("/{job_id}")

async def generate_report(
    job_id: str,
    principal: Principal = Depends(
        require_roles("analyst", "admin", "reviewer")
    ),
    db: Session = Depends(get_db),
):
    get_accessible_job(job_id, principal, db)

    try:

        service = TrademarkConflictReportService(job_id)
        report_path = service.generate()
        report = Report(
            job_id=job_id,
            filename=report_path.name,
            report_type="CONFLICT_INVESTIGATION",
        )
        db.add(report)
        record_audit_event(db, principal, "report.generated", job_id)
        db.commit()
        db.refresh(report)
        return {
            "status": "ready",
            "id": report.id,
            "job_id": job_id,
            "filename": report_path.name,
            "report_type": report.report_type,
            "created_at": report.created_at,
            "download_url": f"/api/reports/{job_id}/download",
        }

    except FileNotFoundError as exc:

        raise HTTPException(

            status_code=404,

            detail=str(exc),

        )

@router.get("/{job_id}/history")

async def get_report_history(
    job_id: str,
    principal: Principal = Depends(
        require_roles("analyst", "admin", "reviewer")
    ),
    db: Session = Depends(get_db),
):

    get_accessible_job(job_id, principal, db)

    reports = (

            db.query(Report)

            .filter(

                Report.job_id == job_id

            )

            .order_by(

                Report.created_at.desc()

            )

            .all()

        )

    return [

            {

                "id": report.id,

                "job_id": report.job_id,

                "filename": report.filename,

                "report_type": report.report_type,

                "created_at": report.created_at,

                "download_url": (

                    f"/api/reports/"

                    f"{report.job_id}/download"

                ),

            }

        for report in reports
    ]

@router.get("/{job_id}/download")

async def download_report(
    job_id: str,
    principal: Principal = Depends(
        require_roles("analyst", "admin", "reviewer")
    ),
    db: Session = Depends(get_db),
):

    get_accessible_job(job_id, principal, db)

    service = TrademarkConflictReportService(job_id)

    report_path = service.report_file

    if not report_path.exists():

        raise HTTPException(

            status_code=404,

            detail=(

                "Report not found. "

                "Generate the report first."

            ),

        )

    return FileResponse(

        path=str(report_path),

        media_type="application/pdf",

        filename=(

            "Trademark_Conflict_"

            "Investigation_Report.pdf"

        ),

    )