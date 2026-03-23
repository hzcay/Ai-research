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


@lru_cache()
def get_retrieve_context_use_case() -> RetrieveContextUseCase:
    settings = get_settings()
    embedder = BgeEmbedder(model_name=settings.embed_model_name)
    vector_store = QdrantVectorStore(
        qdrant_url=settings.qdrant_url,
        collection_name=settings.qdrant_collection,
    )
    return RetrieveContextUseCase(embedder=embedder, vector_store=vector_store)


@lru_cache()
def get_generate_answer_use_case() -> GenerateAnswerUseCase:
    settings = get_settings()
    llm = GroqChatModel(
        api_key=settings.groq_api_key or "",
        model_name=settings.groq_model,
        model_name_2=settings.groq_model_2,
    )
    retrieve = get_retrieve_context_use_case()
    return GenerateAnswerUseCase(llm=llm, retrieve=retrieve)


@lru_cache()
def get_ingest_pdfs_use_case() -> IngestPdfsUseCase:
    settings = get_settings()
    parser = PdfParser()
    indexer = DocumentIndexer(settings=settings)
    return IngestPdfsUseCase(parser=parser, indexer=indexer)
