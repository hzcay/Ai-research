from __future__ import annotations

import pytest
from sqlalchemy import delete, func, select

from src.application.use_cases.manage_workspace import (
    WorkspacePermissionError,
    WorkspaceService,
)
from src.infrastructure.database.models import (
    OutboxEvent,
    ResearchProject,
    User,
)
from src.infrastructure.database.postgres_repository import async_session_factory


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_project_scope_review_is_versioned_audited_and_authorized() -> None:
    service = WorkspaceService(async_session_factory)
    owner_id = "phase1-owner"
    reviewer_id = "phase1-reviewer"
    outsider_id = "phase1-outsider"

    await service.ensure_user(owner_id, "phase1-owner@example.test", "Owner")
    await service.ensure_user(reviewer_id, "phase1-reviewer@example.test", "Reviewer")
    await service.ensure_user(outsider_id, "phase1-outsider@example.test", "Outsider")
    project_id = None

    try:
        project = await service.create_project(
            owner_id, "Phase 1 verification", "How does retrieval evaluation affect RAG quality?"
        )
        project_id = project["id"]
        await service.add_member(owner_id, project_id, reviewer_id, "reviewer")
        members = await service.list_members(owner_id, project_id)
        assert {member["role"] for member in members} == {"owner", "reviewer"}
        with pytest.raises(WorkspacePermissionError):
            await service.get_project(outsider_id, project_id)

        scope_v1 = await service.create_scope(owner_id, project_id, {
            "research_question": project["research_question"],
            "framework": "freeform",
            "population": "RAG systems",
            "languages": ["English"],
            "inclusion_criteria": ["Reports retrieval quality"],
            "exclusion_criteria": ["No empirical evaluation"],
        })
        submitted = await service.submit_scope(owner_id, project_id, scope_v1["id"])
        assert submitted["status"] == "pending_review"
        approved = await service.review_scope(
            reviewer_id, project_id, scope_v1["id"], "approved", "Scope is reproducible."
        )
        assert approved["status"] == "approved"

        scope_v2 = await service.create_scope(owner_id, project_id, {
            "research_question": project["research_question"],
            "framework": "freeform",
            "population": "Production RAG systems",
            "languages": ["English"],
            "inclusion_criteria": ["Reports retrieval and citation quality"],
            "exclusion_criteria": [],
        })
        assert scope_v2["version"] == 2
        assert scope_v2["supersedes_id"] == scope_v1["id"]

        first_run = await service.start_workflow(
            owner_id, project_id, "scope_foundation", "hash-v1", "phase1-key"
        )
        repeated_run = await service.start_workflow(
            owner_id, project_id, "scope_foundation", "hash-v1", "phase1-key"
        )
        assert repeated_run["workflow_id"] == first_run["workflow_id"]
        assert len(await service.list_workflows(owner_id, project_id)) == 1

        paused = await service.update_project_status(owner_id, project_id, "paused")
        assert paused["status"] == "paused"
        active = await service.update_project_status(owner_id, project_id, "active")
        assert active["status"] == "active"

        tasks = await service.list_tasks(owner_id, project_id)
        assert tasks[0]["resolution"] == "approved"
        audit = await service.list_audit(owner_id, project_id)
        assert {event["action"] for event in audit} >= {
            "project.created", "membership.updated", "scope.created",
            "scope.submitted", "scope.approved",
        }

        async with async_session_factory() as session:
            outbox_count = await session.scalar(
                select(func.count()).select_from(OutboxEvent).where(
                    OutboxEvent.project_id == project_id
                )
            )
            assert outbox_count
    finally:
        async with async_session_factory() as session:
            if project_id:
                await session.execute(delete(ResearchProject).where(ResearchProject.id == project_id))
            await session.execute(delete(User).where(User.id.in_([owner_id, reviewer_id, outsider_id])))
            await session.commit()
