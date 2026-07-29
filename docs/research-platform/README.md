# AI Research Platform Design

Bo tai lieu nay ghi lai huong chuyen doi du an tu chatbot RAG thanh mot
Research Workspace phuc vu Literature Review. Day la product va solution
architecture target, khong phai mo ta trang thai implementation hien tai.

## Dinh vi

San pham khong duoc dinh vi la "chat voi PDF". RAG chi la retrieval engine.
San pham chinh la mot evidence-grounded literature review workspace, giup
nghien cuu vien di tu research question den first review draft co the kiem
chung va duoc reviewer phe duyet.

Primary UI la Research Workspace. Chat chi la Copilot theo context cua trang,
paper, evidence hoac draft dang mo.

## Muc tieu

- Giam it nhat 50% thoi gian tao first acceptable draft.
- Dat it nhat 80% information accuracy tren bo du lieu danh gia co nhan.
- Moi empirical claim phai truy vet duoc den evidence trong paper that.
- Cac quyet dinh quan trong phai co Human-in-the-Loop.
- Search, screening, extraction va synthesis phai reproducible.
- Theo doi duoc chi phi theo project, workflow va model.

## Nguyen tac bat bien

1. Project va artifact la trung tam, khong phai conversation.
2. PostgreSQL la source of truth cho workflow state va provenance.
3. Agent tao proposal; domain service va con nguoi quyet dinh artifact chinh thuc.
4. Khong them feature neu khong tac dong den accuracy, time saved hoac risk.
5. Khong coi DOI ton tai la bang chung claim duoc support.
6. Khong ket luan "research gap" ngoai pham vi corpus da tim va da screen.
7. Moi workflow AI phai co schema, state, retry, stop condition va evaluation.

## Tai lieu

- [01-product-vision.md](01-product-vision.md): pain point, JTBD, product boundary va UX.
- [02-workspace-design.md](02-workspace-design.md): Research Project Workspace chi tiet.
- [03-platform-architecture.md](03-platform-architecture.md): kien truc, storage, schema va reliability.
- [04-agent-workflows.md](04-agent-workflows.md): graph, structured output va guardrails.
- [05-roadmap-and-evaluation.md](05-roadmap-and-evaluation.md): MVP, roadmap, KPI va acceptance criteria.
- [06-decision-log.md](06-decision-log.md): cac quyet dinh da thong nhat va nhung viec chua lam.
- [07-domain-and-state-model.md](07-domain-and-state-model.md): bounded context, aggregate va state machine.
- [08-reliability-and-security.md](08-reliability-and-security.md): consistency, outbox, retry, authorization va privacy.
- [09-evaluation-contract.md](09-evaluation-contract.md): dinh nghia KPI, dataset va evaluation gate.
- [10-mvp-vertical-slice.md](10-mvp-vertical-slice.md): pham vi MVP co the trien khai va demo end-to-end.

## Thu tu feature theo dependency

1. Sua ingestion/retrieval hien tai thanh RAG substrate tin cay.
2. Identity, Project Workspace va scope versioning.
3. OpenAlex Search Run, metadata ingestion va deduplication.
4. Screening va human approval.
5. Full-text ingestion va mot evidence schema co dinh.
6. Evidence Matrix va evidence verification.
7. Mot thematic synthesis section co Claim-Evidence Verification.
8. Citation Audit va Markdown export.

Sau MVP moi mo rong sang nhieu provider, full draft, gap detection, project
portfolio va data-analysis sandbox.

Khong chuyen sang feature sau chi vi UI feature truoc da xong. Moi phase phai
dat acceptance criteria ve data model, provenance, reliability va evaluation.

## MVP target

MVP ho tro AI-assisted rapid/scoping review cho mot nhom nghien cuu nho. MVP
khong tuyen bo thay the systematic review chuan PRISMA va khong ho tro moi loai
review methodology.
