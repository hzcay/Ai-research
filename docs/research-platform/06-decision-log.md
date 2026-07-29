# Decision Log

## Accepted decisions

### ADR-001: Workspace-first, not chat-first

Primary UI la Research Workspace. Chat chi la context-aware Copilot.

### ADR-002: Project and artifacts are the domain center

Conversation history khong chua workflow state. Project, paper, evidence, claim
va draft la cac entity co schema va version.

### ADR-003: PostgreSQL is the workflow source of truth

Redis dung cho queue/cache/lock. Qdrant dung cho vector retrieval. MinIO dung
cho object. Khong storage nao trong ba loai nay thay PostgreSQL quan ly state.

### ADR-004: AI output is a proposal

Agent khong tu approve scope, screening, evidence, claim hoac draft. Domain
service chi promote proposal sau human checkpoint phu hop.

### ADR-005: Evidence before synthesis

Synthesis va draft dua tren structured evidence da trich xuat, khong dua truc
tiep tren mot prompt gom nhieu PDF.

### ADR-006: Claim-level provenance

Citation marker khong du. Claim phai lien ket evidence item, exact source span,
paper version va verification status.

### ADR-007: Reproducibility through versioning

Scope, search run, full text, extraction schema, prompt/model va draft phai co
version/input hash de co the tai lap va audit.

### ADR-008: Separate general and AI workers

Metadata/queue work va Docling/embedding/LLM work co resource profile khac nhau
va can scale doc lap.

### ADR-009: Modular monolith for MVP

FastAPI duoc to chuc theo bounded context trong mot deployable. Khong tach
microservice truoc khi co nhu cau scale/ownership duoc do luong.

### ADR-010: Project-isolated corpus for MVP

Vector va cache bat buoc gan `project_id`. Chap nhan duplicate vector de doi lay
tenant isolation don gian. Shared global corpus la quyet dinh Phase sau.

### ADR-011: Artifact state over project current stage

Project chi co lifecycle tong quat. Workflow progress duoc tinh tu state cua
tung artifact va task, khong dung mot state tuyen tinh duy nhat.

### ADR-012: Transactional outbox

Domain change va outbox event duoc ghi trong cung PostgreSQL transaction. Redis
job duoc publish boi dispatcher co retry va reconciliation.

### ADR-013: Stable evidence identity

Evidence/citation tham chieu immutable paper version va document block/span.
Qdrant chunk ID chi la retrieval detail va co the thay doi.

### ADR-014: MVP targets rapid/scoping review

MVP ho tro mot workflow rapid/scoping review cho nhom nho, khong tuyen bo tuan
thu toan bo systematic review/PRISMA.

## Deferred decisions

- LangGraph co duoc dung cho tung workflow hay khong: quyet dinh khi node va
  checkpoint cu the duoc implementation.
- Authentication provider va organization model mo rong. Project RBAC toi thieu
  khong duoc defer.
- Export DOCX/LaTeX va reference-manager integration.
- Cloud provider va production topology.
- Statistical code sandbox technology.

## Not in MVP

- Autonomous multi-agent research team.
- Real-time collaborative editor.
- Public project sharing.
- Portfolio analytics phuc tap.
- Tu dong tuyen bo research gap la su that.
- Code sandbox chay code co network access.
- Agent tu dong tao va publish final review.

## Questions for each future feature

1. Pain point cu the la gi?
2. Workflow hien tai mat thoi gian o dau?
3. KPI nao thay doi neu feature thanh cong?
4. Co phuong an don gian hon khong?
5. Du lieu va source of truth nam o dau?
6. Artifact, schema va version la gi?
7. Human checkpoint va failure state o dau?
8. Feature nay co bat buoc cho MVP khong?
