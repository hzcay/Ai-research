from fastapi import APIRouter, Depends

from src.api.dependencies import get_settings_dep
from src.api.models import ChatRequest, ChatResponse
from src.application.container import (
    get_generate_answer_use_case,
)

router = APIRouter()

@router.post("/", response_model=ChatResponse)
async def chat(req: ChatRequest, settings=Depends(get_settings_dep)) -> ChatResponse:
    _ = settings  # placeholder to show dependency usage
    generate_use_case = get_generate_answer_use_case()

    gen = generate_use_case.execute(
        req.query,
        document_id=req.document_id,
        auto_expand_corpus=req.auto_expand_corpus,
    )
    return ChatResponse(
        answer=gen["answer"],
        contexts=gen["contexts"],
        retrieval_scope=gen.get("retrieval_scope"),
    )