from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select

from src.infrastructure.database.models import (
    AuditEvent,
    OutboxEvent,
    ProjectMembership,
    ResearchProject,
    ResearchScope,
    ReviewTask,
    User,
    WorkflowRun,
    IdempotencyRecord,
)


class WorkspaceError(ValueError):
    pass


class WorkspacePermissionError(PermissionError):
    pass


class WorkspaceService:
    def __init__(self, session_factory) -> None:
        self._sessions = session_factory

    async def ensure_user(self, user_id: str, email: str, display_name: str) -> dict:
        async with self._sessions() as session:
            user = await session.get(User, user_id)
            if user is None:
                user = User(id=user_id, email=email, display_name=display_name)
                session.add(user)
            else:
                user.email = email
                user.display_name = display_name
            await session.commit()
            return self._user(user)

    async def create_project(self, actor_id: str, title: str, question: str) -> dict:
        now = datetime.utcnow()
        project_id = str(uuid4())
        async with self._sessions() as session:
            project = ResearchProject(
                id=project_id,
                title=title.strip(),
                research_question=question.strip(),
                status="draft",
                created_by=actor_id,
                created_at=now,
                updated_at=now,
            )
            session.add(project)
            await session.flush()
            session.add(ProjectMembership(
                id=str(uuid4()), project_id=project_id, user_id=actor_id, role="owner"
            ))
            self._record(session, project_id, actor_id, "project.created", "project", project_id, {"title": title})
            await session.commit()
            return self._project(project, "owner")

    async def list_projects(self, actor_id: str) -> list[dict]:
        async with self._sessions() as session:
            rows = await session.execute(
                select(ResearchProject, ProjectMembership.role)
                .join(ProjectMembership, ProjectMembership.project_id == ResearchProject.id)
                .where(ProjectMembership.user_id == actor_id)
                .order_by(ResearchProject.updated_at.desc())
            )
            return [self._project(project, role) for project, role in rows.all()]

    async def get_project(self, actor_id: str, project_id: str) -> dict:
        async with self._sessions() as session:
            role = await self._role(session, actor_id, project_id)
            project = await session.get(ResearchProject, project_id)
            if project is None:
                raise WorkspaceError("Project not found")
            return self._project(project, role)

    async def authorize_document(self, actor_id: str, document_repo, document_id: str, project_id: str | None = None) -> dict:
        document = await document_repo.get_document(document_id)
        if document is None:
            raise WorkspaceError("Document not found")
        if not document.project_id:
            raise WorkspacePermissionError("Legacy document has no project boundary")
        if project_id and document.project_id != project_id:
            raise WorkspacePermissionError("Document does not belong to this project")
        async with self._sessions() as session:
            await self._role(session, actor_id, document.project_id)
        return {"document_id": document.id, "project_id": document.project_id}

    async def add_member(self, actor_id: str, project_id: str, user_id: str | None, role: str, email: str | None = None) -> dict:
        if role not in {"owner", "researcher", "reviewer"}:
            raise WorkspaceError("Invalid project role")
        async with self._sessions() as session:
            await self._require_role(session, actor_id, project_id, {"owner"})
            member_user = await session.get(User, user_id) if user_id else None
            if member_user is None and email:
                member_user = await session.scalar(select(User).where(User.email == email.strip().lower()))
            if member_user is None:
                raise WorkspaceError("No registered account was found for this email")
            user_id = member_user.id
            existing = await session.scalar(select(ProjectMembership).where(
                ProjectMembership.project_id == project_id,
                ProjectMembership.user_id == user_id,
            ))
            if existing:
                existing.role = role
                membership = existing
            else:
                membership = ProjectMembership(
                    id=str(uuid4()), project_id=project_id, user_id=user_id, role=role
                )
                session.add(membership)
            self._record(session, project_id, actor_id, "membership.updated", "membership", membership.id, {"user_id": user_id, "role": role})
            await session.commit()
            return {"user_id": user_id, "role": role}

    async def list_members(self, actor_id: str, project_id: str) -> list[dict]:
        async with self._sessions() as session:
            await self._role(session, actor_id, project_id)
            rows = await session.execute(select(ProjectMembership, User).join(User, User.id == ProjectMembership.user_id).where(ProjectMembership.project_id == project_id).order_by(ProjectMembership.created_at))
            return [{"id": membership.id, "user_id": user.id, "email": user.email, "display_name": user.display_name, "role": membership.role, "created_at": membership.created_at} for membership, user in rows.all()]

    async def remove_member(self, actor_id: str, project_id: str, user_id: str) -> None:
        async with self._sessions() as session:
            await self._require_role(session, actor_id, project_id, {"owner"})
            membership = await session.scalar(select(ProjectMembership).where(ProjectMembership.project_id == project_id, ProjectMembership.user_id == user_id))
            if membership is None:
                raise WorkspaceError("Member not found")
            if membership.role == "owner":
                owners = await session.scalar(select(func.count()).select_from(ProjectMembership).where(ProjectMembership.project_id == project_id, ProjectMembership.role == "owner"))
                if owners <= 1:
                    raise WorkspaceError("A project must retain one owner")
            await session.delete(membership)
            self._record(session, project_id, actor_id, "membership.removed", "membership", membership.id, {"user_id": user_id})
            await session.commit()

    async def update_project_status(self, actor_id: str, project_id: str, status: str) -> dict:
        if status not in {"draft", "active", "paused", "completed", "archived"}:
            raise WorkspaceError("Invalid project status")
        async with self._sessions() as session:
            role = await self._require_role(session, actor_id, project_id, {"owner"})
            project = await session.get(ResearchProject, project_id)
            if project is None:
                raise WorkspaceError("Project not found")
            if project.status == "archived" and status != "archived":
                raise WorkspaceError("Archived projects cannot be reopened")
            project.status = status
            project.updated_at = datetime.utcnow()
            self._record(session, project_id, actor_id, "project.status_changed", "project", project_id, {"status": status})
            await session.commit()
            return self._project(project, role)

    async def start_workflow(self, actor_id: str, project_id: str, workflow_type: str, input_hash: str | None = None, idempotency_key: str | None = None) -> dict:
        async with self._sessions() as session:
            await self._role(session, actor_id, project_id)
            if idempotency_key:
                existing = await session.get(IdempotencyRecord, idempotency_key)
                if existing:
                    return existing.result or {"status": existing.status, "workflow_id": None}
            workflow = WorkflowRun(id=str(uuid4()), project_id=project_id, workflow_type=workflow_type, status="running", input_hash=input_hash, created_by=actor_id)
            session.add(workflow)
            if idempotency_key:
                session.add(IdempotencyRecord(key=idempotency_key, project_id=project_id, operation=workflow_type, status="started", result={"workflow_id": workflow.id}))
            self._record(session, project_id, actor_id, "workflow.started", "workflow", workflow.id, {"workflow_type": workflow_type, "input_hash": input_hash})
            await session.commit()
            return {"workflow_id": workflow.id, "status": workflow.status, "workflow_type": workflow.workflow_type}

    async def list_workflows(self, actor_id: str, project_id: str) -> list[dict]:
        async with self._sessions() as session:
            await self._role(session, actor_id, project_id)
            rows = await session.scalars(select(WorkflowRun).where(WorkflowRun.project_id == project_id).order_by(WorkflowRun.created_at.desc()))
            return [{"id": x.id, "workflow_type": x.workflow_type, "status": x.status, "input_hash": x.input_hash, "error_message": x.error_message, "created_at": x.created_at, "completed_at": x.completed_at} for x in rows.all()]

    async def create_scope(self, actor_id: str, project_id: str, data: dict[str, Any]) -> dict:
        async with self._sessions() as session:
            await self._require_role(session, actor_id, project_id, {"owner", "researcher"})
            current = await session.scalar(
                select(ResearchScope).where(ResearchScope.project_id == project_id).order_by(ResearchScope.version.desc()).limit(1)
            )
            if current and current.status in {"draft", "pending_review"}:
                raise WorkspaceError("Finish the current scope version before creating another")
            version = (current.version + 1) if current else 1
            scope = ResearchScope(
                id=str(uuid4()), project_id=project_id, version=version,
                status="draft", created_by=actor_id,
                supersedes_id=current.id if current else None,
                **self._scope_fields(data),
            )
            session.add(scope)
            self._record(session, project_id, actor_id, "scope.created", "scope", scope.id, {"version": version})
            await session.commit()
            return self._scope(scope)

    async def list_scopes(self, actor_id: str, project_id: str) -> list[dict]:
        async with self._sessions() as session:
            await self._role(session, actor_id, project_id)
            rows = await session.scalars(
                select(ResearchScope).where(ResearchScope.project_id == project_id).order_by(ResearchScope.version.desc())
            )
            return [self._scope(scope) for scope in rows.all()]

    async def submit_scope(self, actor_id: str, project_id: str, scope_id: str) -> dict:
        async with self._sessions() as session:
            await self._require_role(session, actor_id, project_id, {"owner", "researcher"})
            scope = await self._scope_for_project(session, scope_id, project_id)
            if scope.status != "draft":
                raise WorkspaceError("Only a draft scope can be submitted")
            scope.status = "pending_review"
            scope.submitted_at = datetime.utcnow()
            task = ReviewTask(
                id=str(uuid4()), project_id=project_id, artifact_type="scope",
                artifact_id=scope.id, status="open", assigned_role="reviewer",
                requested_by=actor_id,
            )
            session.add(task)
            self._record(session, project_id, actor_id, "scope.submitted", "scope", scope.id, {"task_id": task.id})
            await session.commit()
            return self._scope(scope)

    async def review_scope(self, actor_id: str, project_id: str, scope_id: str, decision: str, comment: str | None) -> dict:
        if decision not in {"approved", "changes_requested"}:
            raise WorkspaceError("Invalid review decision")
        async with self._sessions() as session:
            await self._require_role(session, actor_id, project_id, {"owner", "reviewer"})
            scope = await self._scope_for_project(session, scope_id, project_id)
            if scope.status != "pending_review":
                raise WorkspaceError("Scope is not pending review")
            task = await session.scalar(select(ReviewTask).where(
                ReviewTask.project_id == project_id,
                ReviewTask.artifact_id == scope.id,
                ReviewTask.status == "open",
            ))
            now = datetime.utcnow()
            if decision == "approved":
                await session.execute(
                    ResearchScope.__table__.update().where(
                        ResearchScope.project_id == project_id,
                        ResearchScope.status == "approved",
                        ResearchScope.id != scope.id,
                    ).values(status="superseded")
                )
                scope.status = "approved"
                scope.approved_at = now
                project = await session.get(ResearchProject, project_id)
                project.status = "active"
                project.updated_at = now
            else:
                scope.status = "draft"
                scope.change_note = comment
            if task:
                task.status = "resolved"
                task.resolved_by = actor_id
                task.resolution = decision
                task.comment = comment
                task.resolved_at = now
            self._record(session, project_id, actor_id, f"scope.{decision}", "scope", scope.id, {"comment": comment})
            await session.commit()
            return self._scope(scope)

    async def list_tasks(self, actor_id: str, project_id: str) -> list[dict]:
        async with self._sessions() as session:
            await self._role(session, actor_id, project_id)
            tasks = await session.scalars(select(ReviewTask).where(ReviewTask.project_id == project_id).order_by(ReviewTask.created_at.desc()))
            return [self._task(task) for task in tasks.all()]

    async def list_audit(self, actor_id: str, project_id: str) -> list[dict]:
        async with self._sessions() as session:
            await self._role(session, actor_id, project_id)
            events = await session.scalars(select(AuditEvent).where(AuditEvent.project_id == project_id).order_by(AuditEvent.created_at.desc()).limit(100))
            return [self._audit(event) for event in events.all()]

    async def _role(self, session, actor_id: str, project_id: str) -> str:
        role = await session.scalar(select(ProjectMembership.role).where(
            ProjectMembership.project_id == project_id,
            ProjectMembership.user_id == actor_id,
        ))
        if role is None:
            raise WorkspacePermissionError("Project access denied")
        return role

    async def _require_role(self, session, actor_id: str, project_id: str, roles: set[str]) -> str:
        role = await self._role(session, actor_id, project_id)
        if role not in roles:
            raise WorkspacePermissionError("Insufficient project role")
        return role

    @staticmethod
    async def _scope_for_project(session, scope_id: str, project_id: str):
        scope = await session.get(ResearchScope, scope_id)
        if scope is None or scope.project_id != project_id:
            raise WorkspaceError("Scope not found")
        return scope

    @staticmethod
    def _record(session, project_id, actor_id, action, artifact_type, artifact_id, details):
        session.add(AuditEvent(id=str(uuid4()), project_id=project_id, actor_id=actor_id, action=action, artifact_type=artifact_type, artifact_id=artifact_id, details=details))
        session.add(OutboxEvent(id=str(uuid4()), project_id=project_id, event_type=action, aggregate_type=artifact_type, aggregate_id=artifact_id, payload=details, status="pending"))

    @staticmethod
    def _scope_fields(data):
        return {key: data.get(key) for key in ["research_question", "framework", "population", "intervention", "comparison", "outcomes", "study_types", "date_from", "date_to", "languages", "inclusion_criteria", "exclusion_criteria", "change_note"]}

    @staticmethod
    def _user(x): return {"id": x.id, "email": x.email, "display_name": x.display_name}
    @staticmethod
    def _project(x, role): return {"id": x.id, "title": x.title, "research_question": x.research_question, "status": x.status, "role": role, "created_at": x.created_at}
    @staticmethod
    def _scope(x): return {key: getattr(x, key) for key in ["id", "project_id", "version", "status", "research_question", "framework", "population", "intervention", "comparison", "outcomes", "study_types", "date_from", "date_to", "languages", "inclusion_criteria", "exclusion_criteria", "change_note", "created_at", "submitted_at", "approved_at", "supersedes_id"]}
    @staticmethod
    def _task(x): return {key: getattr(x, key) for key in ["id", "project_id", "artifact_type", "artifact_id", "status", "assigned_role", "requested_by", "resolved_by", "resolution", "comment", "created_at", "resolved_at"]}
    @staticmethod
    def _audit(x): return {key: getattr(x, key) for key in ["id", "actor_id", "action", "artifact_type", "artifact_id", "details", "created_at"]}
