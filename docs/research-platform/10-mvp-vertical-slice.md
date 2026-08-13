# MVP Vertical Slice

## Product promise

Voi mot research question, researcher co the tao mot rapid/scoping review nho,
tu search den mot thematic section co claim-level citation va reviewer approval.

## In scope

- Mot project, owner/researcher/reviewer.
- Mot approved scope version.
- Mot provider: OpenAlex.
- Dedup deterministic + ambiguous review queue.
- Screening include/exclude/uncertain.
- 10-15 candidate papers duoc human-confirm.
- 5 full-text papers duoc upload/acquire va parse.
- Mot evidence schema co dinh, vi du:
  - research objective
  - population/dataset
  - method  
  - sample size
  - main finding
  - limitation
- Evidence Matrix co exact source location.
- Mot comparison matrix.
- Mot thematic synthesis section.
- Claim ledger va citation audit.
- Markdown export.

## Out of scope

- Full systematic review/PRISMA compliance.
- Meta-analysis.
- Multi-provider exhaustive search.
- Automatic global research-gap claim.
- Full paper/review generation.
- Real-time collaboration.
- Organization administration.
- DOCX/LaTeX/reference-manager integration.
- Data-analysis code sandbox.
- Autonomous multi-agent team.

## End-to-end demo

```text
1. Researcher tao project va nhap research question.
2. Scope Assistant tao proposal; researcher/reviewer approve.
3. He thong tao va review OpenAlex query.
4. Search Run luu raw result, normalize va deduplicate.
5. AI de xuat screening; human resolve uncertain/high-risk decisions.
6. Researcher chon 5 full-text paper.
7. Worker parse thanh immutable blocks va index retrieval.
8. AI trich evidence co schema va exact span.
9. Human verify evidence matrix.
10. AI tao candidate theme va claim tren verified evidence.
11. Citation verifier danh dau support/weak/contradiction.
12. Reviewer approve mot thematic section va export Markdown.
```

## Acceptance criteria

### Product

- Workflow co the hoan thanh ma khong dung chat lam UI chinh.
- UI luon hien thi artifact/task can xu ly.
- Reviewer co the request changes va xem provenance.
- Time saved duoc do theo protocol trong evaluation contract.

### Architecture

- PostgreSQL la source of truth.
- Domain event publish qua outbox.
- Moi job idempotent va resume sau restart.
- Moi Qdrant query filter theo project.
- Evidence citation song sot qua rechunk/reindex.
- Khong approved claim nao thieu verified evidence.

### AI quality

- Dat cac quality gate trong `09-evaluation-contract.md`.
- Invalid structured output khong fallback thanh prose im lang.
- Citation verifier phan biet support, contradiction va irrelevant.

## Demo is not done when

- Search chi la danh sach tam thoi khong luu query/provenance.
- Citation chi tro den chunk ID.
- Human approval chi la mot nut khong co version/audit.
- Worker bao completed khi parse/index chua xong.
- Draft co citation that nhung citation khong support claim.
- KPI chi la latency hoac so answer chatbot.
