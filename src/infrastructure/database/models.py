import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, String, Text, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("project_id", "content_hash", name="uq_documents_project_content_hash"),
    )
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    minio_path = Column(String, nullable=True)
    markdown_path = Column(String, nullable=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata_ = Column("metadata", JSONB, default=dict)
    content_hash = Column(String, nullable=True, index=True)
    project_id = Column(String, ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=True, index=True)

class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    doc_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default="queued")
    created_at = Column(DateTime, default=datetime.utcnow)
    error_message = Column(Text, nullable=True)
    queue_job_id = Column(String, nullable=True)

class Chunk(Base):
    __tablename__ = "chunks"
    
    chunk_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    doc_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    parent_id = Column(String, nullable=True, index=True)
    chunk_type = Column(String, default="child", nullable=False)
    
    text_content = Column(Text, nullable=False)
    
    chunk_index = Column(Integer, nullable=False)
    page_start = Column(Integer, nullable=True)
    page_end = Column(Integer, nullable=True)
    token_count = Column(Integer, nullable=True)
    content_hash = Column(String, nullable=True, index=True)
    section_path = Column(String, nullable=True)
    source_content_hash = Column(String, nullable=True, index=True)
    
    embedding_status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, nullable=False, unique=True, index=True)
    display_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ResearchProject(Base):
    __tablename__ = "research_projects"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    research_question = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="draft")
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ProjectMembership(Base):
    __tablename__ = "project_memberships"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_membership"),)

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ResearchScope(Base):
    __tablename__ = "research_scopes"
    __table_args__ = (UniqueConstraint("project_id", "version", name="uq_project_scope_version"),)

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="draft")
    research_question = Column(Text, nullable=False)
    framework = Column(String, nullable=False, default="freeform")
    population = Column(Text, nullable=True)
    intervention = Column(Text, nullable=True)
    comparison = Column(Text, nullable=True)
    outcomes = Column(Text, nullable=True)
    study_types = Column(Text, nullable=True)
    date_from = Column(Integer, nullable=True)
    date_to = Column(Integer, nullable=True)
    languages = Column(JSONB, nullable=False, default=list)
    inclusion_criteria = Column(JSONB, nullable=False, default=list)
    exclusion_criteria = Column(JSONB, nullable=False, default=list)
    change_note = Column(Text, nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    supersedes_id = Column(String, ForeignKey("research_scopes.id"), nullable=True)


class ReviewTask(Base):
    __tablename__ = "review_tasks"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    artifact_type = Column(String, nullable=False)
    artifact_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="open")
    assigned_role = Column(String, nullable=False, default="reviewer")
    requested_by = Column(String, ForeignKey("users.id"), nullable=False)
    resolved_by = Column(String, ForeignKey("users.id"), nullable=True)
    resolution = Column(String, nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(String, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)
    artifact_type = Column(String, nullable=False)
    artifact_id = Column(String, nullable=False)
    details = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String, nullable=False)
    aggregate_type = Column(String, nullable=False)
    aggregate_id = Column(String, nullable=False)
    payload = Column(JSONB, nullable=False, default=dict)
    status = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    delivered_at = Column(DateTime, nullable=True)


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"
    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="running")
    input_hash = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    key = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    operation = Column(String, nullable=False)
    status = Column(String, nullable=False, default="started")
    result = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
