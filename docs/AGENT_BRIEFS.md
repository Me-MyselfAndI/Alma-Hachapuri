# Agent briefs (parallel tracks)

> Coordinator launches one agent per row. Each agent reads its brief + linked docs; reports done with smoke-test notes.

| Track | Agent goal | Output | Brief |
|-------|------------|--------|-------|
| **A · Public pages** | Implement prospect-facing UI (no staff auth) | Code in `webapp/` + `docs/WEBAPP_PUBLIC_PAGES.md` | [§ A below](#track-a--public-pages-non-employee) |
| **B · Staff layout plan** | Plan employee pages shell & layout only — **no code** | `docs/WEBAPP_STAFF_LAYOUT_PLAN.md` | [§ B below](#track-b--staff-pages--layout-plan) |
| **C · Dev commands** | Unified build / test / run CLI for api + webapp | `scripts/dev.py`, root `package.json`, docs | [§ C below](#track-c--dev-commands) |
| **D · Login + auth** | S1–S3: cookie auth, middleware, `/login` | Code in `webapp/` | [§ D below](#track-d--login--auth-s1s3) |
| **E · Lead list** | S4: `/leads` table, filters, pagination | Code in `webapp/` | [§ E below](#track-e--lead-list-s4) |
| **F · Lead detail** | S5–S7: `/leads/[id]`, resume proxy, polish | Code in `webapp/` | [§ F below](#track-f--lead-detail-s5s7) |

**Staff build order:** **D → E → F** (sequential — shared auth shell). Brand: **Hachapuri** per [WEBAPP_STAFF_LAYOUT_PLAN.md](WEBAPP_STAFF_LAYOUT_PLAN.md) §9.

**Shared decisions:** [WEBAPP_IMPLEMENTATION_PLAN.md](WEBAPP_IMPLEMENTATION_PLAN.md) (Q-W1–Q-W12 all confirmed).

**Coordination rules:**
- Track **A** may add `next.config` rewrites, shadcn init, `lib/api-client.ts` — staff implementer reuses later.
- Track **B** is planning only; does not edit `webapp/`.
- Track **C** edits `scripts/`, root `package.json`, README/RUN_LOCALLY — not feature UI.

---

## Track A · Public pages (non-employee)

**Scope:** Prospect / public routes only — **not** staff login or leads UI.

### Routes to implement

| Route | Decision | API |
|-------|----------|-----|
| `/` | Q-W4 **C** — landing with links to Submit + Staff login | — |
| `/submit` | Multipart form (L1a) | `POST /api/v1/leads/verification-requests` |
| `/verify` | Q-W7 **C** — POST verify, GET fallback | `POST` / `GET /api/v1/leads/verify` |

### Decisions (document in `docs/WEBAPP_PUBLIC_PAGES.md` — do not re-debate)

| Topic | Choice |
|-------|--------|
| API access | Q-W5 **B** — browser calls same-origin `/api/v1/...`; Next rewrites/proxies to FastAPI |
| Styling | Q-W12 **B** — Tailwind + shadcn/ui (`npx shadcn@latest init` if not done) |
| Public layout | Minimal header/footer; **no** staff session; link "Staff login" → `/login` (page may 404 until staff track builds it) |
| Submit form fields | `first_name`, `last_name`, `email`, optional `source`, `resume` — per [entities/lead.md](entities/lead.md) |
| Submit success | **202** → static "Check your email…" (echo email from response) |
| Submit errors | **400/422/502** → `formatApiError` inline alert |
| Verify | Read `?token=` client-side; try POST `{ token }` first; on failure try GET `?token=` |
| Verify outcomes | **201** thank-you + lead id; **404/410/409** friendly copy; **400** missing token |
| Auth | **None** on these routes — no Bearer, no cookie |

### Files (expected)

```text
webapp/
├── app/
│   ├── page.tsx              # landing (Q-W4 C)
│   ├── submit/page.tsx
│   └── verify/page.tsx
├── components/public/        # SubmitForm, VerifyResult, etc.
├── lib/
│   ├── api-client.ts         # publicFetch, formatApiError
│   └── types.ts              # minimal public types
├── next.config.ts            # rewrites: /api/v1/:path* → API_URL
└── docs/WEBAPP_PUBLIC_PAGES.md  # this track's decision log (copy table above + any implementation notes)
```

### Acceptance (manual)

1. `npm run dev` in webapp (API on :8000) — landing renders with two links  
2. `/submit` — valid PDF → 202 message  
3. Mailpit verify link → `/verify?token=...` → success → lead created  

### Out of scope for this agent

- `/login`, `/leads`, middleware, HttpOnly cookie auth (staff track)
- Resume download proxy (Q-W6 — staff detail page)

---

## Track B · Staff pages & layout plan

**Scope:** **Planning document only.** No code changes.

### Deliverable

Create **`docs/WEBAPP_STAFF_LAYOUT_PLAN.md`** covering:

1. **Staff shell** — header (app name, user email, logout), nav, responsive behavior  
2. **Route map** — `/login`, `/leads`, `/leads/[id]` with wireframe-level description  
3. **Auth UX** — Q-W1 B cookie, Q-W2 A bootstrap, Q-W3 B middleware (what middleware checks, redirect rules)  
4. **Login page** — form, error states, `?next=` redirect  
5. **Lead list** — table columns, pagination, Q-W11 filters (state + mine), empty state  
6. **Lead detail** — sections: summary, state + `state_changed_at`, Q-W8 transition buttons, resume download (Q-W6 B route), permission errors Q-W9 B  
7. **shadcn components** — which primitives per page (Button, Table, Select, Alert, etc.)  
8. **Component tree** — folder layout under `webapp/components/staff/`  
9. **Implementation slices** — ordered steps for a future staff implementer (W2–W5 equivalent)  
10. **Open questions** — only if something is genuinely unresolved; otherwise reference Q-W decisions

### Inputs (must read)

- [WEBAPP_IMPLEMENTATION_PLAN.md](WEBAPP_IMPLEMENTATION_PLAN.md) — all Q-W confirmed  
- [entities/lead.md](entities/lead.md), [entities/account.md](entities/account.md)  
- [permission.md](entities/permission.md) — Q-W9 friendly 403 copy  

### Out of scope

- Writing React/TS code  
- Changing API backend  

---

## Track C · Dev commands

**Scope:** Monorepo CLI for **build**, **test**, and **run** with a `--target` flag.

### Deliverable

1. **`scripts/dev.py`** (or refactor `start.py` + shared module) with subcommands:

```text
python scripts/dev.py run   --target {api|webapp|both} [--skip-docker] [--skip-migrate]
python scripts/dev.py test  --target {api|webapp|all}
python scripts/dev.py build --target {api|webapp|all}
```

2. **Root `package.json`** npm aliases, e.g.:

```json
"dev": "python scripts/dev.py run --target both",
"dev:api": "python scripts/dev.py run --target api",
"dev:web": "python scripts/dev.py run --target webapp",
"test": "python scripts/dev.py test --target all",
"build": "python scripts/dev.py build --target all"
```

3. **Docs** — update [RUN_LOCALLY.md](RUN_LOCALLY.md) and root README with new commands. Keep `scripts/setup.py` as one-time setup.

### Behavior spec

| Command | api | webapp | both |
|---------|-----|--------|------|
| **run** | docker (optional skip) + migrate (optional skip) + uvicorn :8000 | `npm run dev` in webapp | both processes; Ctrl+C stops all |
| **test** | `pytest tst/ -q` from api venv | `npm run lint` + `next build` (or add `test` script if needed) | run both sequentially; exit non-zero if either fails |
| **build** | no-op or `pip install -r requirements.txt` check | `npm run build` | both |

- Resolve paths from repo root (reuse pattern from `scripts/start.py`, `api/src/core/paths.py`).
- Windows-compatible (`npm.cmd`, venv Scripts path).
- **`run --target api`** ≡ current `start.py --skip-webapp`.
- **`run --target both`** ≡ current `start.py` default.
- Deprecate nothing — `start.py` may delegate to `dev.py run` or stay as alias.

### Acceptance

- From repo root after setup: `python scripts/dev.py test --target api` passes  
- `python scripts/dev.py run --target api` starts API only  
- `npm test` runs full test suite per package.json  

### Out of scope

- CI/CD pipelines  
- Production deploy  
- Webapp feature pages  

---

## Track D · Login + auth (S1–S3)

**Page:** `/login` (+ auth infrastructure used by all staff routes)

**Must read:** [WEBAPP_STAFF_LAYOUT_PLAN.md](WEBAPP_STAFF_LAYOUT_PLAN.md) §1–3, §6.2, §7 (auth + shell + login)

### Implement

| Item | Files |
|------|-------|
| Cookie auth routes | `app/api/auth/login/route.ts`, `logout/route.ts`, `me/route.ts` |
| Server fetch | `lib/api.ts` — read `alma_access_token` cookie, forward Bearer to `API_URL` |
| Cookie constants | `lib/auth-cookie.ts` — name, options (HttpOnly, SameSite=Lax) |
| Middleware | `middleware.ts` — `/leads/*` requires cookie; redirect `/login?next=` |
| Session | `components/auth/SessionProvider.tsx` — bootstrap `GET /api/auth/me` |
| Staff shell | `components/staff/shell/StaffShell.tsx`, `StaffHeader.tsx`, `UserMenu.tsx` |
| Login UI | `app/login/page.tsx`, `components/staff/login/LoginForm.tsx` |
| Leads layout | `app/leads/layout.tsx` — wraps children in SessionProvider + StaffShell |

**Brand:** Hachapuri in header.

**Acceptance:**
- `attorney@example.com` / `attorney123` → `/leads` (may 404 until Track E)
- Bad password → inline error
- `/leads` without cookie → `/login?next=/leads`
- Cookie not in `document.cookie`

**Out of scope:** Lead list/detail UI (Tracks E/F)

---

## Track E · Lead list (S4)

**Page:** `/leads`

**Depends on:** Track D (auth + StaffShell)

**Must read:** [WEBAPP_STAFF_LAYOUT_PLAN.md](WEBAPP_STAFF_LAYOUT_PLAN.md) §2.2, §4, §6.3, §9 (Waiting since column)

### Implement

| Item | Files |
|------|-------|
| List page | `app/leads/page.tsx` |
| Components | `LeadListPage.tsx`, `LeadTable.tsx`, `LeadTableRow.tsx`, `LeadFilters.tsx`, `LeadPagination.tsx`, `LeadStateBadge.tsx` |
| Staff fetch | `lib/staff-api.ts` — `staffFetch` with `credentials: 'include'` via `/api/v1/...` |
| Types | Extend `lib/types.ts` — `AccountMe`, `LeadListItem`, `Paginated<T>` |

**Columns:** Name, Email, State, Assignee, Submitted, **Waiting since** (`state_changed_at` relative).

**Filters:** state select + "My leads only" (`mine=true`); URL sync `?state=&mine=&page=`.

**Acceptance:** Table loads seed leads; filters update URL; pagination works; empty state.

**Out of scope:** Detail page, resume download, stretch features §9.1

---

## Track F · Lead detail (S5–S7)

**Page:** `/leads/[id]`

**Depends on:** Tracks D + E

**Must read:** [WEBAPP_STAFF_LAYOUT_PLAN.md](WEBAPP_STAFF_LAYOUT_PLAN.md) §2.3, §5, §6.4, §9 (immediate transitions, friendly 403)

### Implement

| Item | Files |
|------|-------|
| Detail page | `app/leads/[id]/page.tsx` |
| Components | `LeadDetailPage.tsx`, `LeadDetailHeader.tsx`, `LeadDetailCards.tsx`, `LeadTransitionPanel.tsx`, `ResumeDownloadLink.tsx` |
| Helpers | `lib/lead-transitions.ts`, `lib/permission-messages.ts` |
| Resume proxy | `app/api/leads/[id]/resume/route.ts` (Q-W6 B) |
| shadcn adds | `table`, `select`, `checkbox`, `badge`, `card`, `textarea`, `skeleton` if missing |

**Transitions:** Allowed buttons only; **immediate** POST (no confirm modal). Optional note.

**403:** User-friendly permission messages per plan §5.3.

**Acceptance:** PENDING→REACHED_OUT works; resume downloads; readonly gets friendly 403 on transition; logout flow works.

**Out of scope:** §9.1 deferred features (history, email log, export, assignee UI, admin)

**Manual smoke:** Plan §8 manual test steps 1–6.
