from fastapi import APIRouter, Depends

from src.api.dependencies import get_settings_dep
from src.api.models import ChatRequest, ChatResponse
from src.application.container import (
    get_generate_answer_use_case,
)

router = APIRouter()

@router.post("/", response_model=ChatResponse)
async def chat(req: ChatRequest, settings=Depends(get_settings_dep)) -> ChatResponse:
    _ = settings 
    
    from src.application.container import get_task_tracker
    tracker = get_task_tracker()
    if req.document_id:
        task = tracker.get_task(req.document_id)
        if task and task.get("status") == "processing":
            req.document_id = None

    generate_use_case = get_generate_answer_use_case()

    gen = await generate_use_case.execute(
        req.query,
        document_id=req.document_id,
        auto_expand_corpus=req.auto_expand_corpus,
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