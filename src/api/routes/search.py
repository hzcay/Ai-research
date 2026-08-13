from fastapi import APIRouter, Depends, HTTPException

from src.api.models import SearchRequest, SearchResponse, SearchResult
from src.application.container import get_retrieve_context_use_case
from src.api.dependencies import get_current_user
from src.application.container import get_workspace_service
from src.application.use_cases.manage_workspace import WorkspaceError, WorkspacePermissionError

router = APIRouter()


@router.post("/", response_model=SearchResponse)
async def search(req: SearchRequest, user=Depends(get_current_user)) -> SearchResponse:
    if req.project_id:
        try:
            await get_workspace_service().get_project(user["id"], req.project_id)
        except (WorkspaceError, WorkspacePermissionError) as exc:
            raise HTTPException(status_code=403, detail="Project access denied") from exc
    if req.document_id:
        from src.application.container import get_postgres_repository
        try:
            await get_workspace_service().authorize_document(
                user["id"], get_postgres_repository(), req.document_id, req.project_id
            )
        except (WorkspaceError, WorkspacePermissionError) as exc:
            raise HTTPException(status_code=403, detail="Document access denied") from exc
    retrieve_use_case = get_retrieve_context_use_case()
    docs, metrics = await retrieve_use_case.execute(
        req.query,
        top_k=req.top_k,
        document_id=req.document_id,
        project_id=req.project_id,
    )
    results = [
        SearchResult(
            id=doc.id,
            score=doc.score,
            metadata={
                "text": doc.text,
                "metadata": doc.metadata,
            },
        )
        for doc in docs
    ]
    return SearchResponse(results=results)
