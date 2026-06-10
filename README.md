# Research Assistant Platform
![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-00a393.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)
![MinIO](https://img.shields.io/badge/MinIO-Object_Storage-c7202c.svg)
![Qdrant](https://img.shields.io/badge/Qdrant-Vector_Database-ff5252.svg)
![Redis](https://img.shields.io/badge/Redis-Distributed_Cache-dc382d.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B.svg)

Production-oriented Retrieval-Augmented Generation (RAG) system for academic and technical research.
Built with FastAPI, Arq, Qdrant, Redis, PostgreSQL, MinIO, and BGE-M3 hybrid retrieval to support scalable document ingestion, grounded question answering, and retrieval observability.
## Quick demo

https://github.com/user-attachments/assets/141681c7-0ad6-487a-a2ce-e6c93a29f92f

## Why This Project?

Most open-source RAG (Retrieval-Augmented Generation) tutorials focus primarily on orchestration frameworks and small-scale demos, often hiding the underlying retrieval pipeline and system behavior.

This project was built to explore the engineering challenges involved in developing more reliable and observable retrieval systems, including:

### Retrieval Transparency & Observability
The system exposes retrieval telemetry, citation tracing, and chunk-level inspection so users can understand where generated responses originate from.

### Hybrid Retrieval Architecture
Instead of relying on Python-side keyword filtering, the project uses native database-level dense and sparse retrieval fusion through Qdrant and BGE-M3 embeddings.

### Resource-Constrained Ingestion
The ingestion pipeline includes asynchronous processing, bounded concurrency, and disk-backed intermediate storage to improve stability during concurrent document uploads on CPU-only local hardware.

### Production-Oriented System Design
The architecture emphasizes:
- separation of concerns
- retrieval evaluation
- ingestion benchmarking
- scalability analysis
- graceful degradation under load

Rather than serving as a simple chatbot wrapper, the project is intended as an experimentation platform for studying retrieval behavior, ingestion scalability, and AI system observability.
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
* **Arq (Redis) Background Workers:** Document parsing (via `Docling`), chunking, embedding, and upserting are fully delegated to robust, distributed background workers, guaranteeing zero data loss.
* **Persistent Storage:** Metadata is safely persisted in PostgreSQL and raw documents in MinIO before processing.
* **Streamlit Fragments (`@st.fragment`):** The frontend UI polls the backend status API without re-rendering the entire chat interface, providing a smooth user experience.

### 4. Advanced Observability & Citation Debugging
Built for transparency, ensuring the LLM is truly grounded:
* **Strict Citation:** The LLM (via Groq) is strictly prompted to cite its sources using `[1]`, `[2]` markers.
* **Retrieval Debug UI:** A dedicated side-panel in Streamlit exposes raw telemetry: 
  * Cache Hit/Miss status.
  * Micro-latencies breakdown: *Embedding Time*, *Vector Search Time*, *LLM Generation Time*.
* **Context Inspector:** Users can expand citations to inspect the exact Chunk ID, Document Name, Page Number, and Similarity Score used by the LLM.
### 5. Concurrent Ingestion Benchmark

The ingestion pipeline is benchmarked using concurrent PDF uploads through the HTTP API layer.

The benchmark simulates multiple users uploading documents simultaneously to evaluate:
- API responsiveness
- ingestion stability
- queue behavior
- resource saturation under constrained local hardware

#### Benchmark Setup

**Hardware**
- Intel i5-5200U
- 16GB RAM
- CPU-only environment

**Pipeline Constraints**
- Bounded ingestion workers: 2
- Disk-backed intermediate storage enabled

#### Test Scenarios

- Batch 5 concurrent uploads
- Batch 10 concurrent uploads

#### Metrics

- Success / failure count
- API response latency
- Average ingestion time
- P95 ingestion time
- Throughput
- Queue saturation behavior

#### Benchmark Results

| Batch Size | Success / Fail | Total Time | Avg API Latency | Avg Ingestion | P95 Ingestion | Throughput |
|------------|----------------|------------|-----------------|---------------|---------------|------------|
| 5 Users    | 5 / 0          | 1140.18s   | 0.59s           | 854.19s       | 1110.91s      | 0.26 files/min |
| 10 Users   | 10 / 0         | 2115.71s   | 0.90s           | 1381.64s      | 2051.32s      | 0.28 files/min |
| 15 Users   | 15 / 0         | 3196.06s   | 1.05s           | 2000.16s      | 3097.40s      | 0.28 files/min |

#### Benchmark Analysis

The API layer remained extremely responsive (~1 second latency) under concurrent uploads. The slight increase in API latency compared to the legacy system is expected, as the API now synchronously persists metadata to **PostgreSQL**, saves raw files to **MinIO**, and enqueues jobs to **Redis / Arq** to guarantee zero data loss.

Crucially, ingestion throughput remained completely stable at **0.28 files/minute** regardless of the batch size (10 vs 15 users). This indicates that the **Arq Background Workers** effectively bound concurrency, preventing OOM crashes and CPU locking while maximizing available resources.

Under bounded concurrency, increasing upload bursts primarily increased queue waiting time (P95 Ingestion) rather than failing requests or degrading throughput.

The benchmark demonstrates textbook graceful degradation behavior for a decoupled microservice architecture:
- the API layer remained responsive
- ingestion tasks completed successfully with guaranteed durability
- throughput remained bounded by available worker capacity
- no ingestion failures or server crashes were observed

#### Performance Notes

These benchmarks were executed on CPU-only local hardware and are intended to analyze architectural behavior and bottlenecks rather than represent production-scale throughput.

Stress testing beyond 10 concurrent uploads was intentionally avoided due to thermal saturation and diminishing benchmarking value on constrained hardware.

#### Observed Bottlenecks

- **CPU Saturation:** Both `Docling` layout parsing and `BGE-M3` vector encoding are heavily CPU-bound. In a CPU-only environment, this creates a strict upper limit on ingestion throughput.
- **ThreadPool Contention:** Running heavy CPU tasks in Starlette's default `BackgroundTasks` ThreadPool requires strict concurrency controls (like `Semaphore`) to prevent starvation of synchronous API endpoints.

---

## System Architecture

![Flow Diagram](photo/uml/flow_diagram.png)

![Flow Mini-Diagram](photo/uml/flow_mini_diagram.png)

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
- **Task Queue & Background Worker:** Arq (Redis)
- **Vector Database:** Qdrant
- **Relational Database:** PostgreSQL
- **Object Storage:** MinIO
- **Caching Layer:** Redis
- **Embedding Model:** BAAI/bge-m3 (via `FlagEmbedding`)
- **LLM Provider:** Groq / Gemini
- **Document Parsing:** Docling / PyMuPDF

---

## Future Work

To further evolve this enterprise architecture, the following improvements are planned:
- GPU embedding workers
- Retrieval evaluation datasets
- Prometheus / Grafana observability
- CI/CD automated deployment

---

## Getting Started
### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Groq API Key

### 1. Configure Environment Variables
```bash
cp .env.example .env
# Open .env and add your GROQ_API_KEY or GEMINI_API_KEY
```

### 2. Spin up the Backend Services
The backend API, Arq worker, PostgreSQL, MinIO, Qdrant, and Redis are all containerized:
```bash
cd docker
docker-compose up -d --build
```

### 3. Run the Streamlit UI (Locally)
The frontend Streamlit app runs locally:
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt

export API_BASE_URL=http://127.0.0.1:8000
```

**Terminal:** Start the Streamlit UI
```bash
export API_BASE_URL=http://127.0.0.1:8000
streamlit run app.py
```

Open `http://localhost:8501` in your browser. Upload a research paper and start querying!