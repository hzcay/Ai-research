from __future__ import annotations

from functools import lru_cache

from src.application.use_cases.generate_answer import GenerateAnswerUseCase
from src.application.use_cases.ingest_pdfs import IngestPdfsUseCase
from src.application.use_cases.retrieve_context import RetrieveContextUseCase
from src.infrastructure.config.settings import get_settings
from src.infrastructure.embeddings.bge_embedder import BgeEmbedder
from src.infrastructure.indexing.document_indexer import DocumentIndexer
from src.infrastructure.llm.groq_chat_model import GroqChatModel
from src.infrastructure.llm.gemini_chat_model import GeminiChatModel
from src.infrastructure.parsing.pdf_parser import PdfParser
from src.infrastructure.vectorstores.qdrant_store import QdrantVectorStore
from src.application.ports.cache_port import SemanticCachePort
from src.infrastructure.cache.qdrant_semantic_cache import QdrantSemanticCache
from src.infrastructure.cache.redis_hot_cache import RedisHotCache
from src.infrastructure.database.postgres_repository import PostgresRepository
from src.infrastructure.storage.minio_storage import MinioStorage
from src.infrastructure.indexing.task_tracker import TaskTracker
from src.utils.metrics import GlobalMetricsTracker
from src.application.ports.reranker_port import RerankerPort
from src.infrastructure.embeddings.noop_reranker import NoOpReranker
from src.infrastructure.embeddings.bge_reranker import BgeReranker
from src.infrastructure.indexing.arq_task_queue import ArqTaskQueueAdapter
from src.infrastructure.parsing.docling_adapter import DoclingParseAdapter
from src.application.use_cases.process_document import ProcessDocumentUseCase

@lru_cache()
def get_global_metrics() -> GlobalMetricsTracker:
    return GlobalMetricsTracker()

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
def get_redis_hot_cache() -> RedisHotCache:
    return RedisHotCache()

@lru_cache()
def get_postgres_repository() -> PostgresRepository:
    return PostgresRepository()

@lru_cache()
def get_minio_storage() -> MinioStorage:
    return MinioStorage()

@lru_cache()
def get_task_queue_adapter() -> ArqTaskQueueAdapter:
    return ArqTaskQueueAdapter()

@lru_cache()
def get_parse_adapter() -> DoclingParseAdapter:
    return DoclingParseAdapter()

@lru_cache()
def get_document_indexer() -> DocumentIndexer:
    return DocumentIndexer(
        settings=get_settings(),
        minio_storage=get_minio_storage(),
        postgres_repo=get_postgres_repository()
    )


@lru_cache()
def get_reranker() -> RerankerPort:
    settings = get_settings()
    if settings.rerank_enabled:
        return BgeReranker()
    else:
        return NoOpReranker()


@lru_cache()
def get_retrieve_context_use_case() -> RetrieveContextUseCase:
    settings = get_settings()
    embedder = get_embedder()
    vector_store = QdrantVectorStore(
        qdrant_url=settings.qdrant_url,
        collection_name=settings.qdrant_collection,
        embedder=embedder,
        timeout_s=settings.qdrant_timeout_s,
        retries=settings.qdrant_retries,
        lexical_candidate_limit=settings.lexical_candidate_limit,
    )
    return RetrieveContextUseCase(
        embedder=embedder,
        vector_store=vector_store,
        chunk_cache=get_redis_hot_cache(),
        document_repo=get_postgres_repository(),
        hybrid_enabled=settings.hybrid_enabled,
        alpha=settings.hybrid_alpha,
        beta=settings.hybrid_beta,
        reranker=get_reranker(),
        rerank_enabled=settings.rerank_enabled,
        rerank_top_n=settings.rerank_top_n,
        rerank_final_k=settings.rerank_final_k,
    )


@lru_cache()
def get_generate_answer_use_case() -> GenerateAnswerUseCase:
    settings = get_settings()
    if settings.llm_provider.lower() == "gemini":
        llm = GeminiChatModel(
            api_key=settings.gemini_api_key or "",
            model_name=settings.gemini_model,
            timeout_s=settings.groq_timeout_s,
            retries=settings.groq_retries,
        )
    else:
        llm = GroqChatModel(
            api_key=settings.groq_api_key or "",
            model_name=settings.groq_model,
            model_name_2=settings.groq_model_2,
            timeout_s=settings.groq_timeout_s,
            retries=settings.groq_retries,
        )
    retrieve = get_retrieve_context_use_case()
    return GenerateAnswerUseCase(
        llm=llm, 
        retrieve=retrieve,
        embedder=get_embedder(),
        semantic_cache=get_semantic_cache()
    )

@lru_cache()
def get_ingest_pdfs_use_case() -> IngestPdfsUseCase:
    return IngestPdfsUseCase(
        storage_port=get_minio_storage(),
        repo_port=get_postgres_repository(),
        task_queue=get_task_queue_adapter()
    )

@lru_cache()
def get_process_document_use_case() -> ProcessDocumentUseCase:
    settings = get_settings()
    vector_store = QdrantVectorStore(
        qdrant_url=settings.qdrant_url,
        collection_name=settings.qdrant_collection,
        embedder=get_embedder(),
        timeout_s=settings.qdrant_timeout_s,
        retries=settings.qdrant_retries,
        lexical_candidate_limit=settings.lexical_candidate_limit,
    )
    return ProcessDocumentUseCase(
        document_repo=get_postgres_repository(),
        storage_port=get_minio_storage(),
        parse_port=get_parse_adapter(),
        embedder=get_embedder(),
        vector_store=vector_store
    )
