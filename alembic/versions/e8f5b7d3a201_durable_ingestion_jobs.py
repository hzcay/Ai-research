"""durable ingestion jobs and document identity

Revision ID: e8f5b7d3a201
Revises: d7e4a6c2f190
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e8f5b7d3a201"
down_revision: Union[str, Sequence[str], None] = "d7e4a6c2f190"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("content_hash", sa.String(), nullable=True))
    op.create_index(
        op.f("ix_documents_content_hash"),
        "documents",
        ["content_hash"],
        unique=True,
    )
    op.add_column("ingestion_jobs", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("queue_job_id", sa.String(), nullable=True))
    op.create_index(
        "uq_ingestion_jobs_doc_id",
        "ingestion_jobs",
        ["doc_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_ingestion_jobs_doc_id", table_name="ingestion_jobs")
    op.drop_column("ingestion_jobs", "queue_job_id")
    op.drop_column("ingestion_jobs", "error_message")
    op.drop_index(op.f("ix_documents_content_hash"), table_name="documents")
    op.drop_column("documents", "content_hash")
