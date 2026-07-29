# Agent Workflows

## Agent contract

Agent khong duoc la mot chatbot nhan prompt tu do va tu ghi ket qua. Moi graph
phai khai bao:

- Node va ownership.
- Typed input/output.
- State persistence.
- Confidence va validator.
- Stop condition.
- Retry policy.
- Human checkpoint.
- Evaluation dataset va metric.

AI output mac dinh la `proposal`, khong phai artifact da approve.

## Risk-based action policy

| Action | Vi du | Policy |
|---|---|---|
| Deterministic, reversible | Normalize DOI | Auto-apply va audit |
| Low-risk proposal | Query expansion | Preview hoac batch review |
| Research decision | Exclude paper | Human approval |
| Scientific claim | Gap/causal claim | Mandatory verification |
| Operational recovery | Retry parser | System policy |

Moi output deu co provenance, nhung khong bat nguoi dung click approve moi thao
tac ky thuat.

## Scope Definition Assistant

```text
load_project
-> validate_question
-> classify_review_framework
-> propose_structured_scope
-> propose_criteria
-> check_ambiguity
   +-> ambiguity_high: request_human_clarification
   +-> ambiguity_low: create_scope_preview
-> human_review
   +-> revise: propose_structured_scope
   +-> approve: persist_scope_version
-> stop
```

Structured output toi thieu:

```json
{
  "research_question": "",
  "framework": "PICO",
  "population": [],
  "intervention_or_exposure": [],
  "comparison": [],
  "outcomes": [],
  "study_types": [],
  "date_range": {"from": null, "to": null},
  "languages": [],
  "inclusion_criteria": [],
  "exclusion_criteria": [],
  "ambiguities": [],
  "assumptions": [],
  "confidence": 0.0
}
```

Agent khong duoc tu chon date range, population hoac study type khi nguoi dung
chua cung cap. Assumption phai hien thi va can human approval.

## Planned workflow graphs

### Search

```text
approved_scope -> build_queries -> human_query_review -> search_providers
-> normalize_metadata -> deduplicate -> persist_search_run
```

Stop condition gom provider exhausted, max result/page, budget cap, cancellation
hoac rate-limit pause. Agent khong duoc tu search vo han vi "chua du paper".

### Screening

```text
candidate -> apply_deterministic_rules -> classify_title_abstract
-> validate_reason -> route(include | exclude | uncertain) -> human_review
```

### Evidence extraction

```text
paper_version -> select_sections -> extract_typed_fields
-> locate_evidence_spans -> validate_locations -> detect_conflicts
-> human_evidence_review
```

### Synthesis

```text
verified_evidence -> cluster_candidate_themes -> human_theme_review
-> generate_claims -> link_claim_evidence -> entailment_check
-> contradiction_check -> human_claim_review -> draft_section
```

## Citation guardrails

1. Metadata validity: DOI/title/author/year khop nguon hoc thuat.
2. Source existence: paper nam trong project corpus.
3. Location validity: page/section/chunk ton tai.
4. Entailment: evidence support claim, khong chi cung keyword.
5. Completeness: empirical claim can co source.
6. Contradiction: nguon phan bac phai duoc danh dau.
7. Human status: verified, needs-review hoac disputed.

Model self-confidence, validator score, entailment score va human status la cac
truong rieng. UI khong duoc gom chung thanh mot phan tram confidence gia tao.

Document/PDF la untrusted input. Instruction nam trong paper khong co quyen thay
doi system prompt, tool permission hoac workflow state.

## Gap detection rule

Khong sinh claim "chua co nghien cuu nao". Chi duoc tao candidate gap co scope:

```text
Trong N paper tim thay va M paper included theo search strategy/version X,
he thong chua quan sat thay evidence ve ...
```

Output phai kem database, query, date range, paper counts, confidence va search
limitations.

## Evaluation

- Schema validity va retry rate.
- Human acceptance/edit distance.
- Screening precision, recall va F1.
- Evidence field accuracy va source-location accuracy.
- Claim faithfulness, citation precision va completeness.
- Unsupported claim rate va contradiction detection accuracy.
