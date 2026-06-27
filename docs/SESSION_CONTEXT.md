# Session context snapshot

Checkpoint of what is documented vs still only in chat. Use before compacting a session to see if anything needs persisting.

**Last updated:** 2026-06-27 — auth/DB/files promoted; stack scaffolded.

---

## Fully captured in repo docs

| Topic | Location |
|-------|----------|
| Original brief | `REQUIREMENTS.md` |
| Assumptions + decision log | `ASSUMPTIONS.md` |
| Architecture (incl. decided auth/DB/files) | `ARCHITECTURE.md` |
| Feature backlog & PLAN tickets | `FEATURES.md` |
| Questions log | `QUESTIONS_LOG.md` |
| Entity schemas | `docs/entities/*.md` |
| Agent corrections | `AGENT_CORRECTIONS.md` |
| Run instructions | `README.md` |

---

## Scaffolded (minimal — not feature-complete)

| Piece | Location |
|-------|----------|
| FastAPI app + health route | `backend/app/main.py` |
| Config / deps list | `backend/app/core/config.py`, `requirements.txt` |
| Next.js app | `frontend/` |
| API client stub | `frontend/lib/api.ts` |
| Docker compose (Postgres + Mailpit) | `docker-compose.yml` |
| Env templates | `.env.example`, `frontend/.env.local.example` |

---

## Still open

| Topic | Status |
|-------|--------|
| F6.2 role→permission seed data | PLAN |
| F2.1 extended lead states | PLAN |
| F3.1 email recipient routing | PLAN |
| Email / LLM provider keys | Mailpit local; Resend/OpenAI when needed |
| GitHub remote | User will add when complete |
| Entity models / routes / UI | Not started |

---

## Verdict

**Safe to compact** — planning, decisions, entity design, stack scaffold, and README are in repo.
