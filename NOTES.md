# Code attribution — agent vs hand-written

This file satisfies the assessment requirement to mark **agent-generated** vs **hand-written** code.  
All git commits are authored by **gpodoksik3**; that reflects review/commit responsibility, not solo authorship.

**Default:** Unless noted below, source was **drafted by Cursor agents** (coordinator or Task subagents) from specs in `docs/entities/`, `docs/ARCHITECTURE.md`, and user prompts. The human role was **product owner + coordinator**: decisions, corrections, smoke testing, and what to merge.

---

## Summary

| Category | Share (approx.) | How it was produced |
|----------|-----------------|---------------------|
| `api/src/` | ~95% agent | Parallel entity-slice agents + coordinator fixes |
| `api/tst/` | ~95% agent | Same agents + e2e flow smoke scripts |
| `webapp/` | ~90% agent | Track agents (public, auth, leads, admin, polish) |
| `db/alembic/` | ~95% agent | Coordinator + migration agent |
| `scripts/` | ~90% agent | Dev/setup CLI agent |
| `docs/entities/`, `ARCHITECTURE.md` | ~85% agent | Coordinator planning; **heavily edited** after user corrections |
| `README.md` | ~70% agent | Agent drafts; user directed evaluator-walkthrough shape |
| Process logs (`QUESTIONS_LOG`, `AGENT_CORRECTIONS`, etc.) | Mixed | Agent-maintained per protocol; **corrections content is user-driven** |

---

## By directory

### Agent-generated (implementation)

| Path | Notes |
|------|--------|
| `api/src/domains/*/` | Routers, services, schemas, models, preconditions — one package per entity (account, lead, prospect, email, resume_file, state_history) |
| `api/src/core/` | Config, permissions matrix, DB session, auth helpers |
| `api/src/main.py` | App wiring, seed demo accounts |
| `api/tst/` | Domain unit/route tests; flow smoke helpers |
| `db/alembic/versions/` | Schema migrations |
| `webapp/app/` | Next.js App Router pages (public, staff, admin, API proxies) |
| `webapp/components/` | UI components (shadcn-based) |
| `webapp/lib/` | Client fetch helpers, types, transitions |
| `webapp/middleware.ts` | Staff route protection |
| `scripts/setup.py`, `scripts/dev.py` | Bootstrap and unified run/test/build |
| `docker-compose.yml`, `.env.example` | Local stack template |

### Agent-generated (planning docs — user-corrected)

| Path | Human input |
|------|-------------|
| `docs/entities/*.md` | User approved API catalog, merged account/attorney model, code-only IAM |
| `docs/ARCHITECTURE.md` | Multiple diagram/readability correction passes |
| `docs/WEBAPP_*` | User confirmed Q-W1–W12; brand Hachapuri |
| `docs/REQUIREMENTS.md` | Brief text + agent formatting |

### Primarily human-driven (decisions & review)

| Item | Notes |
|------|--------|
| Feature priorities & state machine semantics | User confirmed extended states, triggers, attorneys-only assignment |
| `docs/AGENT_CORRECTIONS.md` | User corrections catalog (64 entries); top 10 ranked for submission |
| Git remote / auth troubleshooting | User + agent; pushes to `Me-MyselfAndI/Alma-Hachapuri` |
| Removing internal docs from remote | User request — `git rm --cached` on session logs |
| Commit messages | Human-written summaries of agent work batches |

---

## By commit era (representative)

| Commit (short) | Agent role | Human role |
|----------------|------------|------------|
| `ea52877` Initial | Scaffold structure | Scope from assignment brief |
| `d1d622b`–`97e00c3` | API layer + DB module | Entity/API contract approval |
| `5474bf6`–`0b754ab` | Tests, L1b race fix | Flow e2e review; caught missing commit (#37) |
| `f92deba`–`907b96a` | Public + staff webapp | UX feedback (Mailpit hint, split panels) |
| `ac6a245`–`9c0bb33` | Admin attorneys, reassignment | Route collision fix (#55), role filter |
| `308e753` | — | Remove gitignored docs from GitHub |

---

## Fixes traced to user catch

Documented in `docs/AGENT_CORRECTIONS.md`. Examples that changed code:

- **#37** — `db.commit()` after S7 notifications (`api/src/domains/lead/service.py`)
- **#39** — Reverted erroneous `GRANT_ALL_STAFF_PERMISSIONS` (`api/src/core/permissions.py`)
- **#55** — Assignable accounts via `?for_assignment=true` (`api/src/domains/account/router.py`)
- **#48–51** — Email panel Select + template preview (`webapp/components/staff/leads/LeadEmailPanel.tsx`)

---

## Submission pointer

Full writeup + prompt excerpts: **[docs/AGENT_USAGE_SUBMISSION.md](docs/AGENT_USAGE_SUBMISSION.md)**
