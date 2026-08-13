"""project scoped document identity

Revision ID: f2b3c4d5e6f7
Revises: f1a2b3c4d5e6
"""

from alembic import op

revision = "f2b3c4d5e6f7"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_documents_content_hash", table_name="documents")
    op.create_index("ix_documents_content_hash", "documents", ["content_hash"], unique=False)
    op.create_unique_constraint(
        "uq_documents_project_content_hash",
        "documents",
        ["project_id", "content_hash"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_documents_project_content_hash", "documents", type_="unique")
    op.drop_index("ix_documents_content_hash", table_name="documents")
    op.create_index("ix_documents_content_hash", "documents", ["content_hash"], unique=True)
