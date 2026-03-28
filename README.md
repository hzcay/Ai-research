# Research Assistant (RAG)

End-to-end assistant for research PDFs: ingest, hybrid retrieval (semantic + lexical), and chat over a Qdrant-backed library. **FastAPI** API + **Streamlit** UI.

## Architecture (short)

- **API** (`main.py`): `/health`, `/chat`, `/search`, `/ingest/upload`
- **Ingest**: PDF → parse (Docling / fallback) → chunk → embed → Qdrant; optional dedupe by content hash
- **Retrieve**: hybrid + RRF-style fusion; optional rerank; filter by `document_id` when focusing one paper
- **Answer**: Groq LLM with grounded system prompt; can prefer one uploaded doc then widen to the full corpus

## Prerequisites

- Python 3.11+ recommended
- **Qdrant** running (e.g. [Docker](https://qdrant.tech/documentation/guides/installation/): `docker run -p 6333:6333 qdrant/qdrant`)
- **Groq** API key for chat (`GROQ_API_KEY`)

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
cp .env.example .env
# Edit .env and set GROQ_API_KEY
```

## Run

**1. API**

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

**2. UI** (in another terminal)

```bash
set API_BASE_URL=http://127.0.0.1:8000   # Windows
export API_BASE_URL=http://127.0.0.1:8000  # macOS/Linux
streamlit run app.py
```

Open the Streamlit URL (usually http://localhost:8501). Use **Attach** to add a PDF, then ask questions.

## Tests

Install dependencies first (`pip install -r requirements.txt`). The default suite **does not** call real Qdrant or Groq (HTTP handlers are mocked).

```bash
pytest
```

## Project layout (high level)

| Path | Role |
|------|------|
| `main.py` | FastAPI app and routers |
| `app.py` | Streamlit client |
| `src/application/use_cases/` | Chat, retrieve, ingest orchestration |
| `src/infrastructure/` | Qdrant, embeddings, parsing, LLM |
| `tests/` | Pytest API tests |

## Screenshot

_Add a screenshot of the Streamlit chat UI here for your portfolio README (`docs/screenshot.png` optional)._

## License

Use for learning and portfolio; add a license if you publish publicly.
