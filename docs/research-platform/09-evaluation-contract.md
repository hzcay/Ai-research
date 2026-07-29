# Evaluation Contract

## Why

`Information accuracy >= 80%` qua mo ho de lam acceptance criterion. Accuracy
duoc tach theo capability; metric rui ro cao khong duoc bu tru boi metric de.

## MVP quality gates

| Capability | Metric | Target |
|---|---|---:|
| Scope proposal | Schema validity | >= 99% |
| Screening | Macro-F1 | >= 0.80 |
| Key evidence fields | Field accuracy/F1 | >= 0.80 |
| Evidence provenance | Correct block/page/span | >= 0.90 |
| Citation | Precision | >= 0.90 |
| Citation | Completeness | >= 0.85 |
| Claim | Unsupported empirical claim rate | <= 0.05 |
| Workflow | Approved claim with provenance | 100% |

## Dataset model

```text
evaluation_datasets
evaluation_cases
rubric_versions
human_annotations
evaluation_runs
evaluation_predictions
evaluation_metrics
```

Evaluation run luu Git commit, dataset version, prompt/schema/model version,
embedding/index version, parameters, output, metric, latency va cost.

## Test sets

- Scope: 30-50 research questions co scope/criteria do researcher gan nhan.
- Screening: title/abstract pairs co include/exclude/uncertain va rationale.
- Extraction: paper co key fields va exact evidence spans.
- Citation: claim-evidence pairs gom support, contradiction va irrelevant.
- End-to-end: 2-5 pilot review tasks co rubric chung.

Khong dung cung mot model lam generator va judge duy nhat. LLM-as-judge chi la
supplement; can human-labeled subset va inter-annotator agreement.

## Time-saved protocol

So sanh cung loai task va rubric giua manual workflow va platform workflow.

Do:

- Active researcher minutes.
- Reviewer correction minutes.
- Wall-clock time den first acceptable draft.
- Output quality theo blinded rubric.
- So unsupported claim/citation error.

`First acceptable draft` la draft dat nguong rubric do reviewer doc lap cham,
khong phai draft dau tien agent sinh ra.

## Cost evaluation

Bao cao theo project va workflow:

- Provider/API calls.
- Input/output token.
- Embedding volume.
- Parse/worker duration.
- Cache reuse.
- USD per included paper.
- USD per verified evidence item.
- USD per acceptable draft.

## Release gate

Khong release capability AI moi neu chua co:

1. Dataset/rubric version.
2. Baseline.
3. Quality threshold.
4. Failure analysis.
5. Cost budget.
6. Human fallback.
