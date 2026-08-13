# Agent Handoff: Current Implementation and Next Phases

This file is the implementation map for the next coding agent. Read it before changing code. The repository is intentionally dirty; preserve unrelated user changes and inspect `git diff` before editing overlapping files.

## Product direction

This is an evidence-grounded literature-review workspace, not a generic PDF chatbot. The primary UI is a custom Next.js workspace. Chat is a project-scoped Copilot. PostgreSQL is the workflow/provenance source of truth; Qdrant is a derived retrieval index.

## Current phase status

### Phase 0 — RAG substrate: complete

Implemented ingestion, parsing, deterministic chunking, persistence, embeddings/indexing, retrieval metadata and citations, durable ingestion jobs, empty-corpus handling, and PDF-to-citation tests.

### Phase 1 — Workspace foundation: complete

Implemented project lifecycle, membership/RBAC, project authorization, versioned scope and approval, review tasks, audit events, transactional outbox, workflow idempotency, project-scoped documents/Qdrant, and the Next.js workspace UI. Local email/password authentication uses scrypt password hashes, hashed database sessions, and an HttpOnly cookie. Header authentication remains only as a compatibility adapter for tests/tooling; external identity provider is deferred.

### Phase 2 — Search and screening: next

Build provider adapters (start with OpenAlex), reproducible SearchRun records, normalized paper metadata, DOI/title deduplication, AI-assisted screening proposals, and a human-in-the-loop screening queue.

## File map by responsibility

### API and composition

- `main.py`: FastAPI application entrypoint and route registration.
- `src/api/dependencies.py`: local identity headers and dependency wiring.
- `src/api/routes/auth.py`: registration, login, current session and logout endpoints.
- `src/api/models.py`: Pydantic request/response contracts.
- `src/api/routes/ingest.py`: PDF upload and ingestion status endpoints.
- `src/api/routes/chat.py`: project-scoped Copilot/chat endpoint.
- `src/api/routes/search.py`: retrieval/search endpoint.
- `src/api/routes/workspace.py`: projects, members, status, scopes, workflows, tasks, audit.
- `src/application/container.py`: dependency composition; add new services here.

### Application use cases

- `src/application/use_cases/manage_workspace.py`: project/membership/RBAC, lifecycle, scope versioning and review, audit/outbox records, workflow idempotency, document authorization.
- `src/application/use_cases/manage_auth.py`: local credential hashing and database-backed sessions.
- `src/application/use_cases/ingest_pdfs.py`: upload deduplication and durable enqueue.
- `src/application/use_cases/process_document.py`: parse → chunk → persist → embed/index → complete/fail state machine.
- `src/application/use_cases/retrieve_context.py`: retrieval orchestration and metrics.
- `src/application/use_cases/generate_answer.py`: grounded answer generation and citation assembly.
- `src/application/use_cases/dispatch_outbox.py`: pending outbox locking and ARQ enqueue.

### Domain and infrastructure

- `src/infrastructure/database/models.py`: SQLAlchemy source-of-truth schema, including workspace, scope, review, audit, outbox and workflow tables.
- `src/infrastructure/database/postgres_repository.py`: document/chunk persistence.
- `src/infrastructure/vectorstores/qdrant_store.py`: Qdrant collection/index and project payload filters.
- `src/infrastructure/indexing/chunker.py`: deterministic page-aware chunks and provenance.
- `src/infrastructure/indexing/document_indexer.py`, `qdrant_indexer.py`: indexing pipeline.
- `src/infrastructure/parsing/*`: PDF/Docling parsing and parsed artifact writing.
- `src/infrastructure/embeddings/*`: BGE embedder/reranker implementations.
- `src/infrastructure/cache/*`: Redis and semantic cache layers.
- `src/worker.py`: ARQ worker, ingestion reconciliation, outbox cron, domain-event handler.
- `alembic/versions/`: migrations; current Phase 1 head is `f3c4d5e6f7a8_workflow_idempotency.py`.

### Frontend

- `frontend/app/page.tsx`: single workspace shell and current project views (overview, scope, tasks, team, activity, locked Phase 2 views).
- `frontend/app/api/backend/[...path]/route.ts`: same-origin proxy to FastAPI.
- `frontend/app/globals.css`: primary visual system and responsive layout.
- `frontend/app/phase1.css`: Phase 1 lifecycle/team control styles.
- `frontend/AGENTS.md`: Next.js-specific instruction; read Next.js local docs before modifying frontend patterns.
- `scripts/dev-local.sh`: local API/worker/UI/infrastructure commands.

## Critical invariants

- Only project members can read or mutate project artifacts.
- Only owners can change membership or project lifecycle.
- A project must always retain at least one owner; archived projects cannot reopen.
- Scope versions are immutable in history; a new version supersedes the previous approved version.
- Outbox events are marked delivered only after ARQ enqueue succeeds; enqueue failure leaves them pending with `last_error`.
- A document is searchable only after processing and indexing complete.
- Qdrant data must include `project_id`; never perform an unscoped cross-project query.
- AI proposes; approval and official artifact state remain human/domain-service decisions.

## Verification commands

```bash
.venv/bin/python -m compileall -q src tests
.venv/bin/pytest -q -m 'not integration'
.venv/bin/pytest -q tests/test_phase1_workspace.py -m integration
cd frontend && npm run build
```

Integration tests require the local PostgreSQL container and current Alembic migrations. Do not reset the worktree or delete user data to fix test setup.

## Phase 2 implementation order

1. Add paper/search entities and migration (`SearchRun`, `Paper`, provider result/provenance, dedup groups).
2. Add provider port and OpenAlex adapter with bounded retries and captured request parameters.
3. Add a project-scoped search-run use case and API route; persist normalized metadata before indexing.
4. Add DOI/title normalization and deterministic deduplication with merge provenance.
5. Add screening artifact/state machine (`include`, `exclude`, `uncertain`) and reviewer task endpoints.
6. Extend Next.js with Discover, Search Run detail, candidate table, filters, and screening queue.
7. Add tests for provider replay, dedup edge cases, cross-project denial, idempotent reruns, and reviewer approval.

## Do not do yet

Do not add external auth, Semantic Scholar, full-text evidence extraction, synthesis, gap detection, or portfolio dashboards before Phase 2 acceptance criteria are met.
