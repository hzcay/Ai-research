"""workflow runs and idempotency records

Revision ID: f3c4d5e6f7a8
Revises: f2b3c4d5e6f7
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f3c4d5e6f7a8"
down_revision = "f2b3c4d5e6f7"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("workflow_runs", sa.Column("id", sa.String(), primary_key=True), sa.Column("project_id", sa.String(), sa.ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False), sa.Column("workflow_type", sa.String(), nullable=False), sa.Column("status", sa.String(), nullable=False), sa.Column("input_hash", sa.String()), sa.Column("error_message", sa.Text()), sa.Column("created_by", sa.String(), sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("completed_at", sa.DateTime()))
    op.create_index("ix_workflow_runs_project_id", "workflow_runs", ["project_id"])
    op.create_table("idempotency_records", sa.Column("key", sa.String(), primary_key=True), sa.Column("project_id", sa.String(), sa.ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False), sa.Column("operation", sa.String(), nullable=False), sa.Column("status", sa.String(), nullable=False), sa.Column("result", postgresql.JSONB()), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("completed_at", sa.DateTime()))
    op.create_index("ix_idempotency_records_project_id", "idempotency_records", ["project_id"])

def downgrade():
    op.drop_table("idempotency_records")
    op.drop_table("workflow_runs")
