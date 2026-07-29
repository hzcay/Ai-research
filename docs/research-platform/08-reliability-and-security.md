# Reliability and Security

## Consistency model

PostgreSQL, Redis, MinIO va Qdrant khong co distributed transaction. He thong
dung state machine, transactional outbox, idempotent worker va reconciliation.

```text
API transaction
  -> write domain entity
  -> write outbox event

Outbox dispatcher
  -> publish Arq job
  -> mark event delivered

Worker
  -> claim idempotency key
  -> execute step
  -> persist artifact/status
  -> emit next outbox event
```

## Ingestion saga

```text
create paper version
-> upload object
-> parse to immutable document blocks
-> persist parse artifact
-> embed/index Qdrant
-> mark searchable
```

- MinIO object thanh cong nhung DB fail: orphan cleanup theo TTL.
- Parse thanh cong nhung Qdrant fail: giu `parsed`, retry `indexing`.
- Qdrant loi khong duoc tra ve nhu zero result.
- Human checkpoint ket thuc job hien tai; workflow chuyen `waiting_for_human`.

## Retry policy

| Error | Retry | Outcome |
|---|---:|---|
| Timeout, 429, temporary 5xx | Exponential backoff | Retry co gioi han |
| Invalid schema/output | Toi da 2 model retries | Review task |
| Invalid PDF/corrupt file | Khong | Failed + user action |
| Permission denied | Khong | Security event |
| Missing entity/version conflict | Khong | Reconcile/manual review |
| Qdrant unavailable | Co | Artifact khong searchable |

## Authorization

- Moi API query va mutation scope theo project membership.
- Worker nhan project/entity ID tu trusted job payload va validate ownership.
- Owner, researcher, reviewer la role MVP.
- Qdrant query bat buoc filter `project_id`.
- Semantic cache key/filter gom `project_id` va `corpus_version`.
- MinIO object chi truy cap qua backend hoac signed URL ngan han.

## Data classification

| Class | Vi du | Policy |
|---|---|---|
| Public metadata | DOI, title, abstract | Co the gui provider/model theo policy |
| Licensed full text | Publisher PDF | Kiem tra quyen luu/xu ly |
| Private manuscript | Unpublished paper | Khong gui external model neu chua opt-in |
| Research dataset | CSV, participant data | Ngoai MVP, can policy rieng |
| Credentials | API key | Secret manager, khong log |

## Upload and parser security

- File size/page limit.
- MIME va magic-byte validation.
- Malware scan neu deploy public.
- Parser chay voi timeout, CPU/RAM limit va filesystem tam.
- Khong cho parser/agent tu truy cap URL hoac network tu noi dung PDF.
- Sanitize Markdown/HTML truoc render.
- PDF text la untrusted data, khong phai instruction.

## External model policy

Moi model adapter khai bao retention/training policy, region, max payload va loai
du lieu duoc phep gui. Prompt log mac dinh chi luu hash/metadata; full content
chi luu khi project policy cho phep.

## Operational baseline

- TLS, encryption at rest theo cloud capability.
- Secrets khong nam trong image/repository.
- Backup PostgreSQL/MinIO va restore test.
- Data retention, project export va deletion workflow.
- Correlation ID tren API, outbox, job va model call.
- Alert cho stuck workflow, dead-letter, cost spike va citation failure.
