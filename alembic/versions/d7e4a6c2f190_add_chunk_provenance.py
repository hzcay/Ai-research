"""add chunk provenance

Revision ID: d7e4a6c2f190
Revises: c9bd121b6642
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d7e4a6c2f190"
down_revision: Union[str, Sequence[str], None] = "c9bd121b6642"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chunks", sa.Column("section_path", sa.String(), nullable=True))
    op.add_column("chunks", sa.Column("source_content_hash", sa.String(), nullable=True))
    op.create_index(
        op.f("ix_chunks_source_content_hash"),
        "chunks",
        ["source_content_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_chunks_source_content_hash"), table_name="chunks")
    op.drop_column("chunks", "source_content_hash")
    op.drop_column("chunks", "section_path")
