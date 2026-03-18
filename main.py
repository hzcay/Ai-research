from fastapi import FastAPI

from src.api.routes import chat, search

app = FastAPI(title="Research Assistant RAG", version="0.1.0")


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}


app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(search.router, prefix="/search", tags=["search"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
