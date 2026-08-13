from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import get_settings_dep
from src.api.dependencies import get_current_user
from src.application.container import get_workspace_service
from src.application.use_cases.manage_workspace import WorkspaceError, WorkspacePermissionError
from src.api.models import ChatRequest, ChatResponse
from src.application.container import (
    get_generate_answer_use_case,
)

router = APIRouter()

@router.post("/", response_model=ChatResponse)
async def chat(req: ChatRequest, settings=Depends(get_settings_dep), user=Depends(get_current_user)) -> ChatResponse:
    _ = settings 
    
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
    generate_use_case = get_generate_answer_use_case()

    gen = await generate_use_case.execute(
        req.query,
        document_id=req.document_id,
        auto_expand_corpus=req.auto_expand_corpus,
        project_id=req.project_id,
    )
    from src.application.container import get_global_metrics
    debug_info = gen.get("debug", {})
    metrics = get_global_metrics()
    
    if "cache_hit" in debug_info:
        metrics.record_cache(hit=debug_info["cache_hit"])
        
    debug_info["global_metrics"] = metrics.get_summary()

    return ChatResponse(
        answer=gen["answer"],
        citations=gen.get("citations", []),
        debug=debug_info,
    )
