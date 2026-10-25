"""Add registry source citation metadata to analysis jobs.

Revision ID: 0002_job_source_citations
Revises: 0001_initial_schema
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0002_job_source_citations"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing_columns = {
        column["name"] for column in inspect(op.get_bind()).get_columns("analysis_jobs")
    }
    if "source_name" not in existing_columns:
        op.add_column(
            "analysis_jobs", sa.Column("source_name", sa.String(255), nullable=True)
        )
    if "source_url" not in existing_columns:
        op.add_column(
            "analysis_jobs", sa.Column("source_url", sa.String(2048), nullable=True)
        )
    if "source_record_id" not in existing_columns:
        op.add_column(
            "analysis_jobs",
            sa.Column("source_record_id", sa.String(255), nullable=True),
        )
    if "source_retrieved_at" not in existing_columns:
        op.add_column(
            "analysis_jobs",
            sa.Column(
                "source_retrieved_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )
    if "left_jurisdiction" not in existing_columns:
        op.add_column(
            "analysis_jobs",
            sa.Column("left_jurisdiction", sa.String(32), nullable=True),
        )
    if "right_jurisdiction" not in existing_columns:
        op.add_column(
            "analysis_jobs",
            sa.Column("right_jurisdiction", sa.String(32), nullable=True),
        )
    if "left_nice_classes" not in existing_columns:
        op.add_column(
            "analysis_jobs",
            sa.Column(
                "left_nice_classes", sa.Text(), nullable=False, server_default="[]"
            ),
        )
    if "right_nice_classes" not in existing_columns:
        op.add_column(
            "analysis_jobs",
            sa.Column(
                "right_nice_classes", sa.Text(), nullable=False, server_default="[]"
            ),
        )
    if "left_goods_services" not in existing_columns:
        op.add_column(
            "analysis_jobs",
            sa.Column(
                "left_goods_services", sa.Text(), nullable=False, server_default=""
            ),
        )
    if "right_goods_services" not in existing_columns:
        op.add_column(
            "analysis_jobs",
            sa.Column(
                "right_goods_services", sa.Text(), nullable=False, server_default=""
            ),
        )


def downgrade() -> None:
    op.drop_column("analysis_jobs", "right_goods_services")
    op.drop_column("analysis_jobs", "left_goods_services")
    op.drop_column("analysis_jobs", "right_nice_classes")
    op.drop_column("analysis_jobs", "left_nice_classes")
    op.drop_column("analysis_jobs", "right_jurisdiction")
    op.drop_column("analysis_jobs", "left_jurisdiction")
    op.drop_column("analysis_jobs", "source_retrieved_at")
    op.drop_column("analysis_jobs", "source_record_id")
    op.drop_column("analysis_jobs", "source_url")
    op.drop_column("analysis_jobs", "source_name")
