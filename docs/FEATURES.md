# Feature Backlog

Kanban-style board: **features down the left**, **stages across the top**. Mark the current stage with ●. See [Feature details](#feature-details) for notes.

---

## Stages

| PLAN | Not started | In Progress | Tested | Deployed | Closed |
|------|-------------|-------------|--------|----------|--------|
| Needs scoping / design | Planned, not started | Being built | Verified locally | In target environment | Done |

```text
PLAN → Not started → In Progress → Tested → Deployed → Closed
```

---

## Epics

| Epic | Description |
|------|-------------|
| E1 | Public lead intake (form, validation, file upload) |
| E2 | Lead & prospect persistence |
| E3 | Email notifications (prospect + attorney) |
| E4 | Internal auth & account management |
| E5 | Internal leads UI (list, detail, state updates) |
| E6 | Attorney management, assignment & permissions |
| E7 | AI resume enrichment (custom fields) |

---

## Board

| Feature | PLAN | Not started | In Progress | Tested | Deployed | Closed |
|---------|:----:|:-----------:|:-----------:|:------:|:--------:|:------:|
| **F0.1** · Project scaffold (E1–E7) | | | ● | | | |
| **F2.0** · Entity schema design (E2) | | ● | | | | |
| **F2.1** · Lead state lifecycle (E2) | ● | | | | | |
| **F2.2** · Prospect–lead linking (E2) | | ● | | | | |
| **F3.1** · Attorney notification routing (E3) | ● | | | | | |
| **F6.1** · Lead assignment (E6) | ● | | | | | |
| **F6.2** · Roles & permission matrix (E6) | ● | | | | | |
| **F7.1** · LLM resume enrichment (E7) | | ● | | | | |

<!-- Core assignment features (E1–E5 breakdown) added as rows once PLAN items move to Not started. -->

---

## Feature details

| ID | Summary | Notes |
|----|---------|-------|
| F0.1 | Monorepo scaffold: FastAPI, Next.js, docker-compose, README | **In Progress** — health route works; DB/models/routes next. |
| F2.0 | Entity schemas & relationships | Draft in `docs/entities/`. |
| F2.1 | Full state machine beyond `PENDING` / `REACHED_OUT` | Brief minimum only; may need qualified, declined, etc. Blocks state history. |
| F2.2 | 1 prospect → N leads on submit (match by email) | **Not started** — decision confirmed (A2). Find-or-create prospect by email; always new lead. |
| F3.1 | Who gets new-lead email | Tied to F6.1 assignment. |
| F6.1 | Auto-assign attorney on create; override | **PLAN** — auto-assign + override + `assigned_attorney_id`. Read/write rules open; see F6.2. |
| F6.2 | Permission types & role model (exact ACL matrix deferred) | **PLAN** — `roles`, `permissions`, `role_permissions` entities defined; seed mapping later. |
| F7.1 | `custom_fields` JSON from resume via LLM | **Not started** — per A8: feature flag, async, non-blocking. |

---

## Out of scope (for now)

| Item | Reason |
|------|--------|
| Campaign / mass outreach | Individual intake, not bulk lead gen |
| Case / matter management | Post-retention workflow — see `ARCHITECTURE.md` |
| Multi-tenant / multi-firm | Single org assumed (A1) |
