from fastapi import APIRouter, Depends

from src.api.dependencies import get_settings_dep
from src.api.models import ChatRequest, ChatResponse
from src.application.container import (
    get_generate_answer_use_case,
    get_retrieve_context_use_case,
)

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(req: ChatRequest, settings=Depends(get_settings_dep)) -> ChatResponse:
    _ = settings  # placeholder to show dependency usage
    retrieve_use_case = get_retrieve_context_use_case()
    generate_use_case = get_generate_answer_use_case()

    contexts = retrieve_use_case.execute(req.query)
    gen = generate_use_case.execute(req.query, contexts)
    return ChatResponse(answer=gen["answer"], contexts=gen["contexts"])