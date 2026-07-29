# Product Vision

## Pain point

Nghien cuu vien khong chi mat thoi gian doc PDF. Ho mat thoi gian o toan bo
chuoi cong viec: dinh nghia scope, tim bai, loai trung, screening, trich xuat
evidence, so sanh, tong hop, viet draft va kiem tra citation.

Workflow hien tai thuong bi chia nho giua academic search engine, Zotero,
spreadsheet, note, PDF reader va word processor. Quyet dinh include/exclude va
evidence thuong khong duoc truy vet day du, lam review kho tai lap va kho giao
cho reviewer.

Chatbot RAG hien tai chi toi uu mot buoc nho:

```text
Upload PDF -> dat cau hoi -> nhan answer co citation
```

No chua biet research project dang o giai doan nao, paper nao da duoc duyet,
evidence nao da xac minh, claim nao con yeu va artifact nao la version hien tai.

## Job to be done

Khi bat dau mot de tai, nghien cuu vien muon di tu research question den mot
first acceptable draft co the kiem chung, trong khi van giu quyen quyet dinh
scope, paper selection, evidence va noi dung cuoi.

Reviewer muon tap trung vao cac diem co rui ro cao: screening uncertain,
evidence mau thuan, claim thieu support va thay doi giua cac draft version.

## Product boundary

### Doi tuong va methodology MVP

- Researcher va reviewer trong mot nhom nghien cuu nho.
- Rapid review hoac scoping review co Human-in-the-Loop.
- Mot project co mot active scope version va corpus rieng.
- Khong tuyen bo tu dong hoa systematic review hoac meta-analysis.

### San pham la

- Workspace quan ly literature review theo project.
- Evidence system lien ket paper, evidence span, claim va draft.
- Workflow co Human-in-the-Loop va audit trail.
- Copilot ho tro tung thao tac trong workflow.

### San pham khong la

- Chatbot tong quat cho moi cau hoi nghien cuu.
- Cong cu tu dong viet literature review ma khong can review.
- He thong tu dong tuyen bo mot research gap la su that toan cau.
- Citation generator dua tren metadata ma khong kiem tra evidence.

## Primary workflow

```text
Create Project
  -> Define and approve scope
  -> Search academic sources
  -> Deduplicate candidates
  -> Screen title and abstract
  -> Acquire and parse full text
  -> Extract structured evidence
  -> Verify evidence
  -> Build comparison matrix
  -> Synthesize themes and contradictions
  -> Verify claims and citations
  -> Generate and review draft
  -> Export approved version
```

## Primary artifacts

- Research Scope
- Search Strategy and Search Run
- Candidate Paper Set
- Screening Decision
- Paper and Full-text Version
- Evidence Item
- Comparison Matrix
- Theme
- Synthesis Claim
- Claim-Evidence Link
- Draft Version
- Approval, Comment and Audit Event

## Product KPI

- Time to first acceptable draft giam >= 50%.
- Structured extraction acceptance >= 80%.
- Citation precision >= 90%.
- Unsupported empirical claim rate <= 5%.
- 100% approved claim co provenance den paper va evidence span.
- 100% search run gan voi scope version va query da luu.

So tin nhan, cache hit va so answer khong phai product KPI chinh.

`Information accuracy >= 80%` khong duoc dung nhu mot con so tong hop mo ho.
No duoc tach thanh cac gate cho screening, extraction, evidence location,
faithfulness va citation trong [09-evaluation-contract.md](09-evaluation-contract.md).
