from fastapi import APIRouter, Depends

from src.api.dependencies import get_settings_dep
from src.api.models import ChatRequest, ChatResponse
from src.core import generator, retriever

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(req: ChatRequest, settings=Depends(get_settings_dep)) -> ChatResponse:
    _ = settings  # placeholder to show dependency usage
    contexts = retriever.retrieve(req.query)
    gen = generator.generate_answer(req.query, contexts)
    return ChatResponse(answer=gen["answer"], contexts=gen["contexts"])