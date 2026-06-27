# Questions Log

Single timeline of questions asked during the assessment. Each row is classified by **category · scope**.

**Updated after every question.**

**Timestamps:**

```powershell
Get-Date -Format 'yyyy-MM-dd HH:mm K'
```

Run at **end** of each response (after the answer), then append the new row. Entries **#1–17** approximated evenly between session start **12:10** and **#18** at `13:26 -07:00`.

**Category types:** `planning` · `definition` · `architecture` · `implementation` · `debugging` · `tooling` · `submission` · `meta`

| # | When | Category | Question | Notes |
|---|------|----------|----------|-------|
| 1 | 2026-06-27 12:10 -07:00 | planning · general project | Start with requirements doc only — don't implement yet | Created `docs/REQUIREMENTS.md` from assignment brief. |
| 2 | 2026-06-27 12:15 -07:00 | planning · general project | Put all documentation in a dedicated folder | Moved requirements to `docs/`. |
| 3 | 2026-06-27 12:19 -07:00 | definition · domain terms | What do leads and prospects mean? | Prospect = person; lead = persisted submission record. |
| 4 | 2026-06-27 12:24 -07:00 | meta · docs | One timeline log with classified questions | Single table; category · scope format. |
| 5 | 2026-06-27 12:29 -07:00 | planning · general project | Feature backlog sprint-style with extra PLAN stage | Created `docs/FEATURES.md`. |
| 6 | 2026-06-27 12:33 -07:00 | planning · domain model | Entities, assumptions, LLM custom fields, attorneys & roles | Created `docs/ASSUMPTIONS.md`, entity draft, F7.1. |
| 7 | 2026-06-27 12:38 -07:00 | planning · docs | Split requirements vs assumptions vs architecture | `ARCHITECTURE.md` created; PLAN tickets for open design. |
| 8 | 2026-06-27 12:43 -07:00 | definition · domain terms | Confirm leads/prospects with mattress-store analogy | Prospect = customer; lead = saved submission. |
| 9 | 2026-06-27 12:48 -07:00 | meta · docs | Horizontal kanban board (features × stages) | Restructured `FEATURES.md` board. |
| 10 | 2026-06-27 12:52 -07:00 | architecture · domain | Case/matter — why out of scope? | Lead = intake; case/matter = post-retention. Agreed not v1. |
| 11 | 2026-06-27 12:57 -07:00 | architecture · stack | Does FastAPI + Next.js imply everything runs locally? | No — split client/server; local = dev/demo. |
| 12 | 2026-06-27 13:02 -07:00 | architecture · repo | Proposed monorepo layout | Added to `ARCHITECTURE.md`. |
| 13 | 2026-06-27 13:06 -07:00 | meta · docs | Keep log updated; F2.2 status; DB/hosting open? | F2.2 → Ready. |
| 14 | 2026-06-27 13:11 -07:00 | planning · features | Anything decided but still in PLAN? | F7.1 → Ready; F6.1 partial. |
| 15 | 2026-06-27 13:16 -07:00 | meta · docs | Log protocol; permissions defer; git repo; AWS mapping | Git init; F6.2 scope refined; AWS section added. |
| 16 | 2026-06-27 13:20 -07:00 | meta · docs | Timestamps without PowerShell | Superseded — use approved shell command. |
| 17 | 2026-06-27 13:25 -07:00 | architecture · stack | Best auth, DB, S3 replacement for fastest implementation | Recommend JWT/FastAPI, Postgres docker, local uploads. |
| 18 | 2026-06-27 13:26 -07:00 | meta · docs | Run approved timestamp command every time; stop hallucinating times | Protocol fixed. |
| 19 | 2026-06-27 13:28 -07:00 | architecture · stack | Is Postgres “just APIs”? Can local uploads work on their own? | No — both are backend infrastructure; only FastAPI exposes HTTP API to Next.js. |
| 20 | 2026-06-27 13:30 -07:00 | architecture · stack | How does FastAPI “use” Postgres/uploads? What exactly is being built? | FastAPI = Python HTTP handlers; SQLAlchemy → Postgres; file I/O → uploads; Next.js only fetches API. |
| 21 | 2026-06-27 13:32 -07:00 | architecture · stack | Where is data stored physically? Local vs AWS | DB = Docker volume / RDS disk; files = ./uploads on SSD / S3; FastAPI = process on machine, not storage. |
| 22 | 2026-06-27 13:39 -07:00 | planning · entities | Rename Ready→Not started; create docs/entities schemas | F2.0 added; 7 entity schema docs; board column renamed. |
| 23 | 2026-06-27 13:41 -07:00 | planning · entities | Role should be an entity too | Added `role.md`, `permission.md`, `role_permissions`; account uses `role_id` FK. |
| 24 | 2026-06-27 13:44 -07:00 | meta · docs / tooling | Agent corrections file; session compact readiness; Next/FastAPI setup | Added `AGENT_CORRECTIONS.md`, `SESSION_CONTEXT.md`; frameworks are local install, no registration. |
| 25 | 2026-06-27 13:49 -07:00 | planning · stack | Promote auth/DB/files decisions; scaffold local stack | Decisions locked; `backend/`, `frontend/`, docker-compose, README; Docker not on machine yet. |
| 26 | 2026-06-27 13:53 -07:00 | implementation · stack | Run setup steps 1–4; how to compact session | Step 2 done; 3–4 running; Docker blocked; compact via Cursor chat. |
