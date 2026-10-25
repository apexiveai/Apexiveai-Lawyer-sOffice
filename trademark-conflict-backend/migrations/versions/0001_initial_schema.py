"""Create initial application schema.

Revision ID: 0001_initial_schema
Revises:
"""

from alembic import op

from app.db.database import Base
from app.models.audit_event import AuditEvent
from app.models.job import AnalysisJob
from app.models.report import Report
from app.models.review import Review

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    raise RuntimeError(
        "The initial schema migration is intentionally irreversible "
        "to prevent accidental deletion of application data."
    )
