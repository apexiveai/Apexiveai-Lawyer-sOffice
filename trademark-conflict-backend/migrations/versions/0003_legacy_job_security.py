"""Add tenant and worker fields to pre-existing analysis job tables.

Revision ID: 0003_legacy_job_security
Revises: 0002_job_source_citations
"""

from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0003_legacy_job_security"
down_revision = "0002_job_source_citations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_columns = {
        column["name"] for column in inspect(bind).get_columns("analysis_jobs")
    }
    columns = (
        (
            "tenant_id",
            sa.Column(
                "tenant_id",
                sa.String(255),
                nullable=False,
                server_default="legacy-unassigned",
            ),
        ),
        (
            "owner_id",
            sa.Column(
                "owner_id",
                sa.String(255),
                nullable=False,
                server_default="legacy-unassigned",
            ),
        ),
        (
            "status",
            sa.Column(
                "status",
                sa.String(20),
                nullable=False,
                server_default="UPLOADED",
            ),
        ),
        (
            "progress",
            sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        ),
        (
            "message",
            sa.Column("message", sa.Text(), nullable=False, server_default=""),
        ),
        (
            "attempts",
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        ),
        ("error", sa.Column("error", sa.Text(), nullable=True)),
        (
            "jurisdiction",
            sa.Column("jurisdiction", sa.String(32), nullable=True),
        ),
        (
            "nice_classes",
            sa.Column(
                "nice_classes",
                sa.Text(),
                nullable=False,
                server_default="[]",
            ),
        ),
        (
            "retention_until",
            sa.Column("retention_until", sa.DateTime(timezone=True), nullable=True),
        ),
    )
    for name, column in columns:
        if name not in existing_columns:
            op.add_column("analysis_jobs", column)

    now = datetime.now(timezone.utc)
    job_table = sa.table(
        "analysis_jobs",
        sa.column("job_id", sa.String(64)),
        sa.column("tenant_id", sa.String(255)),
        sa.column("owner_id", sa.String(255)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.execute(
        job_table.update()
        .where(job_table.c.tenant_id.is_(None))
        .values(tenant_id="legacy-unassigned")
    )
    op.execute(
        job_table.update()
        .where(job_table.c.owner_id.is_(None))
        .values(owner_id="legacy-unassigned")
    )
    for name in ("created_at", "updated_at"):
        if name not in existing_columns:
            op.add_column(
                "analysis_jobs",
                sa.Column(name, sa.DateTime(timezone=True), nullable=True),
            )
        op.execute(
            job_table.update()
            .where(job_table.c[name].is_(None))
            .values({name: now})
        )


def downgrade() -> None:
    raise RuntimeError(
        "The legacy job compatibility migration is intentionally irreversible."
    )
