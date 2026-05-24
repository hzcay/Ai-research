# Enterprise-Grade RAG System (Research Assistant)
roduction-oriented Retrieval-Augmented Generation (RAG) system for academic and technical research.
Built with FastAPI, Qdrant, Redis, and BGE-M3 hybrid retrieval to support scalable document ingestion, grounded question answering, and retrieval observability.
![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-00a393.svg)
![Qdrant](https://img.shields.io/badge/Qdrant-Vector_Database-ff5252.svg)
![Redis](https://img.shields.io/badge/Redis-Distributed_Cache-dc382d.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B.svg)
## Key Features & Architecture Highlights

### 1. True Multi-Stage Hybrid Retrieval
Unlike basic RAGs that rely solely on Dense embeddings (Semantic) or perform "fake hybrid" by manually filtering keywords in Python, this system utilizes **Native Database-level Hybrid Search**:
* **BGE-M3 (FlagEmbedding):** Extracts both 1024-dimensional **Dense Vectors** (Semantic context) and **Sparse Vectors** (Lexical/BM25 exact match weights) simultaneously.
* **Qdrant Native RRF:** Both vectors are sent to Qdrant's C++ engine via the `Prefetch` Query API. Qdrant performs the multi-stage search and **Reciprocal Rank Fusion (RRF)** natively, eliminating Python-side bottlenecks and Out-Of-Memory (OOM) risks.

### 2. Distributed Cache Pattern
To optimize latency and memory, the system decouples vector search from payload retrieval:
* **Qdrant** acts strictly as the Vector Index (storing only dense/sparse arrays and lightweight `cache_id`s).
* **Redis** acts as the high-speed KV Store for storing heavy document payloads (Markdown chunks, metadata) with strict Time-To-Live (TTL) management.
* *Fallback Strategy:* If a cache miss occurs in Redis, the system seamlessly falls back to regenerating the context.

### 3. Asynchronous, Non-Blocking Ingestion Pipeline
Uploading large PDFs does not freeze the API or the UI:
* **FastAPI BackgroundTasks:** Document parsing (via `Docling`), chunking, embedding, and upserting are fully delegated to background workers.
* **Thread-Safe TaskTracker:** An in-memory singleton tracks real-time progress.
* **Streamlit Fragments (`@st.fragment`):** The frontend UI polls the backend status API without re-rendering the entire chat interface, providing a smooth user experience.

### 4. Advanced Observability & Citation Debugging
Built for transparency, ensuring the LLM is truly grounded:
* **Strict Citation:** The LLM (via Groq) is strictly prompted to cite its sources using `[1]`, `[2]` markers.
* **Retrieval Debug UI:** A dedicated side-panel in Streamlit exposes raw telemetry: 
  * Cache Hit/Miss status.
  * Micro-latencies breakdown: *Embedding Time*, *Vector Search Time*, *LLM Generation Time*.
* **Context Inspector:** Users can expand citations to inspect the exact Chunk ID, Document Name, Page Number, and Similarity Score used by the LLM.

---

## System Architecture

```text
src/
├── api/             # FastAPI Routers & Pydantic Models
├── application/     # Use Cases (GenerateAnswer, RetrieveContext, IngestDocument) & Ports
├── domain/          # Core Business Entities (RetrievedChunk, Citation, Debug)
├── infrastructure/  # Adapters (QdrantStore, BgeEmbedder, RedisCache, GroqChatModel)
└── utils/           # Structured Logging & Telemetry
```

## Tech Stack
- **Backend Framework:** FastAPI
- **Frontend UI:** Streamlit
- **Vector Database:** Qdrant (Docker)
- **Caching Layer:** Redis (Docker)
- **Embedding Model:** BAAI/bge-m3 (via `FlagEmbedding`)
- **LLM Provider:** Groq (Llama-3/Mixtral)
- **Document Parsing:** Docling / PyMuPDF

---

## Getting Started
### Quick demo

https://github.com/user-attachments/assets/141681c7-0ad6-487a-a2ce-e6c93a29f92f

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Groq API Key

### 1. Spin up the Infrastructure (Qdrant & Redis)
```bash
cd docker
docker-compose up -d
```

### 2. Install Dependencies
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

### 3. Configure Environment Variables
```bash
cp .env.example .env
# Open .env and add your GROQ_API_KEY
```

### 4. Run the Application
You will need two terminal windows:

**Terminal 1: Start the Backend API**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Terminal 2: Start the Streamlit UI**
```bash
export API_BASE_URL=http://127.0.0.1:8000
streamlit run app.py
```

Open `http://localhost:8501` in your browser. Upload a research paper and start querying!

```bash
pytest
```
