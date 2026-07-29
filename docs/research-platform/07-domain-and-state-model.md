# Domain and State Model

## Domain boundaries

| Context | Ownership |
|---|---|
| Identity and Access | User, membership, project role |
| Project and Scope | Project lifecycle, scope version, criteria |
| Discovery | Search strategy, query, run, raw result |
| Screening | Candidate state, decision, reason, conflict |
| Paper Corpus | Canonical paper, provider record, full-text version |
| Evidence | Document block, extraction run, evidence item |
| Synthesis | Theme, claim, claim-evidence link, draft |
| Review | Task, approval, comment, artifact transition |
| Workflow | Run, step, outbox, idempotency, recovery |
| Evaluation | Dataset, annotation, run, metric, cost |

Day la code/schema boundary trong modular monolith, khong phai danh sach
microservice.

## Aggregate invariants

- Search Strategy chi duoc run khi scope version da approved.
- Search Run khong thay doi query/filter sau khi bat dau.
- Screening Decision luon tham chieu candidate va criteria version.
- Paper Version la immutable sau khi parse artifact duoc publish.
- Evidence Item tham chieu exact document span cua mot paper version.
- Claim approved phai co it nhat mot verified evidence link.
- Draft approved khong chua unsupported empirical claim.
- Artifact superseded khong duoc dung cho generation moi.

## State machines

### Scope

```text
draft -> pending_review -> approved -> superseded
  ^           |
  +-- changes_requested
```

### Search run

```text
queued -> running -> completed
                  -> completed_with_warnings
                  -> failed
                  -> cancelled
```

### Candidate paper

```text
discovered -> duplicate
          -> awaiting_screening -> included
                                -> excluded
                                -> uncertain -> included | excluded
```

### Full text

```text
not_requested -> acquisition_pending -> acquired -> parsing -> parsed -> indexing -> searchable
                     |                   |           |          |
                     +-> unavailable     +-> failed  +-> failed +-> failed
```

### Evidence

```text
proposed -> needs_review -> verified -> superseded
                       -> rejected
```

### Claim

```text
draft -> verification_pending -> supported
                              -> weakly_supported
                              -> contradicted
                              -> unsupported
supported -> approved | changes_requested
```

### Draft version

```text
draft -> in_review -> changes_requested -> draft
                   -> approved -> exported
```

## Evidence location

```text
document_blocks
- id UUID
- paper_version_id UUID
- block_type
- section_path
- page_index
- printed_page_label
- bounding_box JSONB
- text_content
- text_hash
- ordinal

evidence_items
- id UUID
- paper_version_id UUID
- document_block_id UUID
- char_start
- char_end
- verbatim_quote
- field_name
- normalized_value JSONB
- source_content_hash
- model_self_confidence
- validator_score
- verification_status
- verified_by
- verified_at
```

Neu parser/rechunk thay doi, tao paper/document version moi. Khong sua span cu.

## Paper identity

Phan biet canonical scholarly work voi record tu provider va cac manifestation:

```text
papers
paper_records
paper_identifiers
paper_relations
dedup_candidates
```

Dedup uu tien DOI/provider ID deterministic, sau do title-year-author heuristic.
Preprint va journal version co the lien ket `is_version_of` thay vi merge mat
lich su. Pair confidence thap phai vao human review queue.
