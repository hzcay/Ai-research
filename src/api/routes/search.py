from fastapi import APIRouter

from src.api.models import SearchRequest, SearchResponse, SearchResult
from src.core import retriever

router = APIRouter()


@router.post("/", response_model=SearchResponse)
async def search(req: SearchRequest) -> SearchResponse:
    docs = retriever.retrieve(req.query, top_k=req.top_k)
    results = [
        SearchResult(id=str(i), score=doc.get("score"), metadata=doc)
        for i, doc in enumerate(docs)
    ]
    return SearchResponse(results=results)