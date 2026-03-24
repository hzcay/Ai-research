from fastapi import FastAPI
from groq import Groq
from qdrant_client import QdrantClient

from src.api.dependencies import init_app_dependencies
from src.api.routes import chat, search
from src.infrastructure.config.settings import get_settings

app = FastAPI(title="Research Assistant RAG", version="0.1.0")


@app.on_event("startup")
async def startup_event() -> None:
    init_app_dependencies()


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness_check() -> dict:
    settings = get_settings()
    checks = {"qdrant": False, "groq": False}
    errors: dict[str, str] = {}

    try:
        qc = QdrantClient(url=settings.qdrant_url, timeout=settings.qdrant_timeout_s)
        qc.get_collections()
        checks["qdrant"] = True
    except Exception as e:
        errors["qdrant"] = str(e)

    try:
        client = Groq(api_key=settings.groq_api_key or "")
        client.chat.completions.create(
            model=settings.groq_model_2,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
            timeout=settings.groq_timeout_s,
        )
        checks["groq"] = True
    except Exception as e:
        errors["groq"] = str(e)

    all_ok = all(checks.values())
    return {"status": "ready" if all_ok else "degraded", "checks": checks, "errors": errors}

app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(search.router, prefix="/search", tags=["search"])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
