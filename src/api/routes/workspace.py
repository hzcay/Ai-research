from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import get_current_user
from src.api.models import (
    MemberUpsertRequest,
    ProjectCreateRequest,
    ScopeCreateRequest,
    ScopeReviewRequest,
    ProjectStatusRequest,
    WorkflowStartRequest,
)
from src.application.container import get_workspace_service
from src.application.use_cases.manage_workspace import (
    WorkspaceError,
    WorkspacePermissionError,
)

router = APIRouter()


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, WorkspacePermissionError):
        return HTTPException(status_code=403, detail=str(exc))
    return HTTPException(status_code=409, detail=str(exc))


@router.post("/projects")
async def create_project(req: ProjectCreateRequest, user=Depends(get_current_user)):
    return await get_workspace_service().create_project(
        user["id"], req.title, req.research_question
    )


@router.get("/projects")
async def list_projects(user=Depends(get_current_user)):
    return await get_workspace_service().list_projects(user["id"])


@router.get("/projects/{project_id}")
async def get_project(project_id: str, user=Depends(get_current_user)):
    try:
        return await get_workspace_service().get_project(user["id"], project_id)
    except (WorkspaceError, WorkspacePermissionError) as exc:
        raise _http_error(exc) from exc


@router.put("/projects/{project_id}/members")
async def upsert_member(project_id: str, req: MemberUpsertRequest, user=Depends(get_current_user)):
    try:
        return await get_workspace_service().add_member(
            user["id"], project_id, req.user_id, req.role, req.email
        )
    except (WorkspaceError, WorkspacePermissionError) as exc:
        raise _http_error(exc) from exc


@router.get("/projects/{project_id}/members")
async def list_members(project_id: str, user=Depends(get_current_user)):
    try:
        return await get_workspace_service().list_members(user["id"], project_id)
    except (WorkspaceError, WorkspacePermissionError) as exc:
        raise _http_error(exc) from exc


@router.delete("/projects/{project_id}/members/{member_id}")
async def remove_member(project_id: str, member_id: str, user=Depends(get_current_user)):
    try:
        await get_workspace_service().remove_member(user["id"], project_id, member_id)
        return {"status": "removed"}
    except (WorkspaceError, WorkspacePermissionError) as exc:
        raise _http_error(exc) from exc


@router.patch("/projects/{project_id}/status")
async def update_project_status(project_id: str, req: ProjectStatusRequest, user=Depends(get_current_user)):
    try:
        return await get_workspace_service().update_project_status(user["id"], project_id, req.status)
    except (WorkspaceError, WorkspacePermissionError) as exc:
        raise _http_error(exc) from exc


@router.post("/projects/{project_id}/workflows")
async def start_workflow(project_id: str, req: WorkflowStartRequest, user=Depends(get_current_user)):
    try:
        return await get_workspace_service().start_workflow(user["id"], project_id, req.workflow_type, req.input_hash, req.idempotency_key)
    except (WorkspaceError, WorkspacePermissionError) as exc:
        raise _http_error(exc) from exc


@router.get("/projects/{project_id}/workflows")
async def list_workflows(project_id: str, user=Depends(get_current_user)):
    try:
        return await get_workspace_service().list_workflows(user["id"], project_id)
    except (WorkspaceError, WorkspacePermissionError) as exc:
        raise _http_error(exc) from exc


@router.post("/projects/{project_id}/scopes")
async def create_scope(project_id: str, req: ScopeCreateRequest, user=Depends(get_current_user)):
    try:
        return await get_workspace_service().create_scope(
            user["id"], project_id, req.model_dump()
        )
    except (WorkspaceError, WorkspacePermissionError) as exc:
        raise _http_error(exc) from exc


@router.get("/projects/{project_id}/scopes")
async def list_scopes(project_id: str, user=Depends(get_current_user)):
    try:
        return await get_workspace_service().list_scopes(user["id"], project_id)
    except (WorkspaceError, WorkspacePermissionError) as exc:
        raise _http_error(exc) from exc


@router.post("/projects/{project_id}/scopes/{scope_id}/submit")
async def submit_scope(project_id: str, scope_id: str, user=Depends(get_current_user)):
    try:
        return await get_workspace_service().submit_scope(user["id"], project_id, scope_id)
    except (WorkspaceError, WorkspacePermissionError) as exc:
        raise _http_error(exc) from exc


@router.post("/projects/{project_id}/scopes/{scope_id}/review")
async def review_scope(project_id: str, scope_id: str, req: ScopeReviewRequest, user=Depends(get_current_user)):
    try:
        return await get_workspace_service().review_scope(
            user["id"], project_id, scope_id, req.decision, req.comment
        )
    except (WorkspaceError, WorkspacePermissionError) as exc:
        raise _http_error(exc) from exc


@router.get("/projects/{project_id}/tasks")
async def list_tasks(project_id: str, user=Depends(get_current_user)):
    try:
        return await get_workspace_service().list_tasks(user["id"], project_id)
    except (WorkspaceError, WorkspacePermissionError) as exc:
        raise _http_error(exc) from exc


@router.get("/projects/{project_id}/audit")
async def list_audit(project_id: str, user=Depends(get_current_user)):
    try:
        return await get_workspace_service().list_audit(user["id"], project_id)
    except (WorkspaceError, WorkspacePermissionError) as exc:
        raise _http_error(exc) from exc
