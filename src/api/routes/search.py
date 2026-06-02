from fastapi import APIRouter

from src.api.models import SearchRequest, SearchResponse, SearchResult
from src.application.container import get_retrieve_context_use_case

router = APIRouter()


@router.post("/", response_model=SearchResponse)
async def search(req: SearchRequest) -> SearchResponse:
    retrieve_use_case = get_retrieve_context_use_case()
    docs, metrics = await retrieve_use_case.execute(
        req.query,
        top_k=req.top_k,
        document_id=req.document_id,
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