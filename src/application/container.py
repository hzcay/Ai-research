from __future__ import annotations

from functools import lru_cache

from src.application.use_cases.generate_answer import GenerateAnswerUseCase
from src.application.use_cases.ingest_pdfs import IngestPdfsUseCase
from src.application.use_cases.retrieve_context import RetrieveContextUseCase
from src.infrastructure.config.settings import get_settings
from src.infrastructure.embeddings.bge_embedder import BgeEmbedder
from src.infrastructure.indexing.document_indexer import DocumentIndexer
from src.infrastructure.llm.groq_chat_model import GroqChatModel
from src.infrastructure.parsing.pdf_parser import PdfParser
from src.infrastructure.vectorstores.qdrant_store import QdrantVectorStore
from src.application.ports.cache_port import SemanticCachePort
from src.infrastructure.cache.qdrant_semantic_cache import QdrantSemanticCache
from src.infrastructure.indexing.task_tracker import TaskTracker

@lru_cache()
def get_task_tracker() -> TaskTracker:
    return TaskTracker()


@lru_cache()
def get_embedder() -> BgeEmbedder:
    settings = get_settings()
    return BgeEmbedder(model_name=settings.embed_model_name)


@lru_cache()
def get_redis_client():
    import redis
    settings = get_settings()
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


@lru_cache()
def get_semantic_cache() -> SemanticCachePort:
    from qdrant_client import QdrantClient
    
    settings = get_settings()
    client = QdrantClient(url=settings.qdrant_url)
    redis_client = get_redis_client()
    
    return QdrantSemanticCache(
        qdrant_client=client,
        redis_client=redis_client,
        cache_ttl_seconds=settings.cache_ttl_seconds,
        collection_name="semantic_cache"
    )


@lru_cache()
def get_document_indexer() -> DocumentIndexer:
    return DocumentIndexer(settings=get_settings())


@lru_cache()
def get_retrieve_context_use_case() -> RetrieveContextUseCase:
    settings = get_settings()
    embedder = get_embedder()
    vector_store = QdrantVectorStore(
        qdrant_url=settings.qdrant_url,
        collection_name=settings.qdrant_collection,
        timeout_s=settings.qdrant_timeout_s,
        retries=settings.qdrant_retries,
        lexical_candidate_limit=settings.lexical_candidate_limit,
    )
    return RetrieveContextUseCase(
        embedder=embedder,
        vector_store=vector_store,
        hybrid_enabled=settings.hybrid_enabled,
        alpha=settings.hybrid_alpha,
        beta=settings.hybrid_beta,
        rerank_enabled=settings.rerank_enabled,
        rerank_top_n=settings.rerank_top_n,
        rerank_final_k=settings.rerank_final_k,
    )


@lru_cache()
def get_generate_answer_use_case() -> GenerateAnswerUseCase:
    settings = get_settings()
    llm = GroqChatModel(
        api_key=settings.groq_api_key or "",
        model_name=settings.groq_model,
        model_name_2=settings.groq_model_2,
        timeout_s=settings.groq_timeout_s,
        retries=settings.groq_retries,
    )
    retrieve = get_retrieve_context_use_case()
    return GenerateAnswerUseCase(llm=llm, retrieve=retrieve)


@lru_cache()
def get_ingest_pdfs_use_case() -> IngestPdfsUseCase:
    parser = PdfParser()
    return IngestPdfsUseCase(parser=parser, indexer=get_document_indexer())
    