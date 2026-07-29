# Research Project Workspace

## Product Analysis

Workspace giai quyet viec literature review khong co mot noi luu project state,
artifact, quyet dinh va tien do. Day la feature MVP bat buoc; Search hay Agent
khong co project boundary se chi tao ra cac thao tac roi rac.

## UI information architecture

```text
Projects
└── Project Workspace
    ├── Plan
    ├── Discover
    ├── Review Papers
    ├── Evidence
    └── Synthesize
```

`Plan` chua scope va criteria. `Discover` chua search run va candidate set.
`Review Papers` chua screening va full-text status. `Synthesize` chua theme,
claim, draft va citation audit. Activity, task va Copilot la side panel thay vi
them tab chinh.

Overview hien thi workflow progress, task cho nguoi dung, paper counts,
verified evidence, claim co citation yeu, chi phi va thoi gian. No khong phai
dashboard trang tri.

Copilot nam o side panel va nhan context cua artifact dang mo. Moi de xuat thay
doi phai co preview/diff va nut apply; Copilot khong ghi truc tiep vao artifact
da duyet.

## Roles

### Owner

- Quan ly project va membership.
- Co quyen cua researcher va reviewer.

### Researcher

- Dinh nghia scope va search strategy.
- Screen paper, sua evidence, tao synthesis va draft.
- Gui artifact cho reviewer.

### Reviewer

- Approve, reject hoac request changes.
- Kiem tra evidence, claim va citation.
- Xem audit history va draft diff.

## Project lifecycle

```text
draft -> active -> paused -> completed -> archived
```

Khong dung mot `current_stage` duy nhat lam source of truth. Tien do duoc tinh tu
state cua scope, search run, candidate, full text, evidence, claim, draft va
review task. UI co the sinh `recommended_next_action`, nhung day chi la read
model va khong duoc agent tu dong thay doi.

## Scope workflow

Research Scope can co version va khong overwrite sau khi da duoc dung:

```text
draft -> pending_review -> approved -> superseded
```

Scope luu research question, framework PICO/SPIDER/freeform, population,
intervention/exposure, comparison, outcomes, study types, date range, language
va inclusion/exclusion criteria.

Khi sua scope da approve, he thong tao version moi va canh bao search/screening
cu co the khong con hop le. Search run cu van tham chieu scope version cu.

## Human checkpoints

- Approve research scope va eligibility criteria.
- Resolve screening decision `uncertain`.
- Approve extracted evidence truoc khi dung cho high-confidence synthesis.
- Review claim co contradiction hoac entailment thap.
- Approve draft version truoc export chinh thuc.

Khong bat human approve deterministic/reversible action nhu normalize DOI hoac
retry parse. Checkpoint duoc dat theo risk de tranh click fatigue.

## Acceptance criteria

- Tao project va scope khong can dung chat.
- Researcher gui scope cho reviewer va nhan request changes.
- Khong mat scope version cu khi sua.
- UI luon cho biet task tiep theo va artifact nao dang cho review.
- Moi mutation quan trong co actor, timestamp va audit event.
- Unauthorized user khong doc hoac sua duoc project.
