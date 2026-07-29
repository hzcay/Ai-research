# Roadmap and Evaluation

## MVP vertical slice

MVP can chung minh mot workflow hep nhung hoan chinh:

```text
Create project and approved scope
-> search one provider: OpenAlex
-> deduplicate and screen candidates
-> select 10-15 papers
-> process 5 available full-text papers
-> extract one fixed evidence schema
-> build one comparison matrix
-> generate one thematic section
-> verify every claim
-> export Markdown
```

MVP bao gom:

- Project Workspace, roles, scope version va audit.
- OpenAlex search.
- Metadata normalization va deduplication.
- Title/abstract screening co include/exclude/uncertain.
- Full-text ingestion va structured evidence extraction.
- Evidence Matrix va human verification.
- Mot thematic synthesis section tren verified evidence.
- Claim ledger, citation audit va Markdown export.

V1 moi bo sung Semantic Scholar, nhieu extraction schema, full review draft,
DOCX/reference-manager integration va collaboration mo rong.

## Phase plan

### Phase 0: Repair current base

- Hoan thanh ingestion: parse, chunk, persist, embed va index.
- Sua retrieval metadata/citation va Qdrant error handling.
- Dong bo API contract va tests.
- Bao dam document chi `completed` khi san sang search.
- Tao immutable document block/span cho evidence location.
- Them upload security baseline va integration test PDF-to-citation.

### Phase 1: Workspace foundation

- Project, membership va authorization.
- Scope versioning va approval.
- Workflow run, review task va audit event.
- Transactional outbox, idempotency va project RBAC.
- Next.js workspace shell.

### Phase 2: Search and Screening

- Academic provider adapters.
- Reproducible search runs va provider provenance.
- DOI/title deduplication.
- Screening AI, reason schema va HITL queue.

### Phase 3: Evidence Engine

- Paper/full-text version.
- Typed extraction schema.
- Exact evidence locations.
- Evidence Matrix va verification state.
- Evaluation dataset co human labels.

### Phase 4: Synthesis and Draft

- Candidate themes va contradiction map.
- Claim-evidence ledger.
- Citation audit.
- Versioned draft va reviewer approval.

### Phase 5: Advanced capabilities

- Candidate gap detection.
- Cost-aware map-reduce synthesis.
- Project portfolio dashboard.
- Data analysis suggestion va code sandbox.

Security, observability, evaluation va cost khong phai phase cuoi. Chung la
quality track chay xuyen suot moi phase.

## Evaluation design

Khong chi dung RAGAS. Can mot tap mau do researcher gan nhan va user study nho.

| Stage | Metrics |
|---|---|
| Search | Recall@K, candidate precision |
| Dedup | Pair precision/recall |
| Screening | Accuracy, F1, human disagreement |
| Extraction | Field F1, span/page accuracy, acceptance rate |
| Synthesis | Faithfulness, contradiction accuracy |
| Citation | Precision, completeness, metadata/location validity |
| Product | Time to first acceptable draft, human edit time |

De do time saved, cung mot task va rubric duoc lam thu cong va lam voi platform.
Reviewer cham chat luong ma khong dua tren viec output do AI tao hay khong.

## MVP exit criteria

- Time to first acceptable draft giam >= 50% tren pilot task.
- Information accuracy >= 80% tren labeled evaluation set.
- Citation precision >= 90%.
- Unsupported empirical claim rate <= 5%.
- 100% approved claim co evidence provenance.
- Workflow resume duoc sau worker restart.
- Cost/project duoc ghi va co budget guardrail.

## Cost controls

- Chi extract full text cho paper da include hoac duoc nguoi dung chon.
- Batch metadata va embedding.
- Cache theo input/model/schema version.
- Dung model nho cho classification, model manh cho synthesis.
- Gioi han candidate, page va token theo project budget.
- Khong regenerate artifact neu input hash khong thay doi.
