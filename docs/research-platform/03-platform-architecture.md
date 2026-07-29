# Platform Architecture

## High-level architecture

```text
Next.js Research Workspace
           |
           v
FastAPI Modular Monolith + Authentication
           |
  +--------+---------+
  |        |         |
Domain Modules + Workflow Services
  |        |         |
  +--------+---------+
           |
       PostgreSQL
      source of truth
           |
       Redis + Arq
           |
  +--------+---------+
  |                  |
General Workers    AI Workers
  |                  |
  +---- MinIO -- Qdrant -- Model APIs
```

## Storage ownership

| Data | Storage |
|---|---|
| User, project, role, workflow state | PostgreSQL |
| Scope, criteria, screening, evidence, claim | PostgreSQL |
| PDF, parsed Markdown, export | MinIO |
| Dense/sparse vectors | Qdrant |
| Queue, lock, short TTL cache | Redis |
| Workflow run, step, cost, audit | PostgreSQL |

Redis va Qdrant khong phai source of truth cho workflow hoac paper metadata.

## Core schema

```text
users
research_projects
project_memberships
research_scopes
eligibility_criteria

search_strategies
search_runs
candidate_papers
paper_identifiers
screening_decisions

papers
paper_versions
document_chunks
evidence_items

themes
synthesis_claims
claim_evidence_links
drafts
draft_versions

workflow_runs
workflow_steps
review_tasks
approvals
comments
audit_events
usage_events
outbox_events
idempotency_records
```

Moi artifact AI can luu `project_id`, input version/hash, schema version, prompt
version, model, output, confidence, status, actor va timestamps.

## Bounded contexts

```text
Identity and Access
Project and Scope
Discovery
Screening
Paper Corpus
Evidence
Synthesis
Review and Publishing
Workflow Execution
Usage and Evaluation
```

MVP la modular monolith, khong phai microservice. Moi module co domain service,
repository contract va ownership cua bang du lieu ro rang. Tach service chi khi
co scaling/ownership requirement duoc chung minh.

## Orchestration

Business workflow dai han duoc luu trong PostgreSQL. Arq xu ly job nen:

- Search provider va metadata normalization.
- Full-text acquisition.
- PDF parsing, chunking, embedding va indexing.
- Evidence extraction va verification.
- Batch synthesis va citation audit.

Job payload chi nen chua entity ID. Worker tai source data tu PostgreSQL/MinIO.
LangGraph co the dieu phoi workflow AI co branching, nhung khong thay the source
of truth cua application.

Domain transaction ghi cung luc domain change va `outbox_event`. Outbox
dispatcher publish job sang Redis. Khong duoc commit database roi enqueue truc
tiep ma khong co recovery path.

## Reliability

- Moi job co idempotency key va input hash.
- Retry chi danh cho transient error; permanent error tao review task.
- Khong danh dau completed truoc khi cac write bat buoc thanh cong.
- Worker retry phai upsert, khong insert mu.
- Workflow co the resume sau restart.
- Loi Qdrant khong duoc bien thanh empty search result mot cach im lang.
- Workflow dai khong nam trong mot Arq job qua human checkpoint.
- Co reconciliation job de tim outbox/job/artifact bi ket.

Vi du key:

```text
evidence-extraction:{paper_version_id}:{schema_version}:{model_version}
```

## Versioning and provenance

- Scope, search strategy, paper full text, evidence schema va draft co version.
- Search run tham chieu immutable scope version.
- Claim tham chieu evidence item va exact source location.
- Vector payload gan `project_id`, `paper_version_id`, `chunk_id` va
  `embedding_version`.
- Corpus thay doi thi tang `corpus_version` de invalidate semantic cache.

Citation identity dua tren immutable `paper_version + document_block/span`,
khong dua tren `chunk_id`. Chunk va vector co the duoc tao lai ma khong lam mat
provenance cua evidence/citation.

## Deployment

MVP gom Next.js, FastAPI, PostgreSQL, Redis, Qdrant, MinIO, general worker va AI
worker. Tach AI worker vi Docling/embedding co CPU va memory profile khac API.

## Observability

- Workflow completion, failure va stuck duration.
- Queue wait, step latency, retry va dead-letter count.
- Parse/extraction/citation failure rate.
- Paper throughput.
- Token, model cost va USD/project.
- Human acceptance va override rate.
- Correlation ID xuyen API, workflow va worker.
