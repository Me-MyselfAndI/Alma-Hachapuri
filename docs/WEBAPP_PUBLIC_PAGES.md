# Public pages (Track A)

> Decision log for prospect-facing routes. Locked per [AGENT_BRIEFS.md](AGENT_BRIEFS.md) Track A and [WEBAPP_IMPLEMENTATION_PLAN.md](WEBAPP_IMPLEMENTATION_PLAN.md) Q-W4–Q-W7, Q-W12. **Do not re-debate.**

**Scope:** `/`, `/submit`, `/verify` only. No staff auth, no `/login` implementation, no `/leads`.

---

## Routes

| Route | Decision | API |
|-------|----------|-----|
| `/` | Q-W4 **C** — landing with links to Submit + Staff login | — |
| `/submit` | Multipart form (L1a) | `POST /api/v1/leads/verification-requests` |
| `/verify` | Q-W7 **C** — POST verify, GET fallback | `POST` / `GET /api/v1/leads/verify` |

---

## Decisions

| Topic | Choice |
|-------|--------|
| API access | Q-W5 **B** — browser calls same-origin `/api/v1/...`; Next rewrites/proxies to FastAPI |
| Styling | Q-W12 **B** — Tailwind + shadcn/ui |
| Public layout | Minimal header/footer; **no** staff session; link "Staff login" → `/login` (404 until staff track) |
| Submit form fields | `first_name`, `last_name`, `email`, optional `source`, `resume` — per [entities/lead.md](entities/lead.md) |
| Submit success | **202** → static "Check your email…" (echo `email` from response) |
| Submit errors | **400/422/502** → `formatApiError` inline alert |
| Verify | Read `?token=` client-side; try POST `{ token }` first; on failure try GET `?token=` |
| Verify outcomes | **201** thank-you + lead id; **404/410/409** friendly copy; **400** missing token |
| Auth | **None** on these routes — no Bearer, no cookie |
| Brand | **Hachapuri** — header, footer, page title (see [WEBAPP_STAFF_LAYOUT_PLAN.md](WEBAPP_STAFF_LAYOUT_PLAN.md) §9) |

---

## Implementation notes

### API proxy (`next.config.ts`)

- Rewrite: `/api/v1/:path*` → `${API_URL}/api/v1/:path*`
- Default target: `http://localhost:8000`
- Set `API_URL` in `webapp/.env.local` (server-side only; not exposed to browser)

### Client fetch (`lib/api-client.ts`)

- `publicFetch<T>(path, { method, formData, json })` — always same-origin paths (e.g. `/api/v1/leads/verify`)
- `formatApiError(status, body)` — parses FastAPI `detail` (string or validation array); maps 502/503 to email-send failure copy

### Types (`lib/types.ts`)

Minimal public types mirroring `api/src/domains/lead/schemas.py`:

- `LeadVerificationRequestResponse` — `{ message, email }`
- `LeadVerifyRequest` — `{ token }`
- `LeadCreateResponse` — `{ id, state, message }`
- `LeadState` — `PENDING | REACHED_OUT | QUALIFIED | DISQUALIFIED | CLOSED`

### Components

| Component | Role |
|-----------|------|
| `PublicShell` | Header (app name, Staff login link), footer, centered content |
| `SubmitForm` | Client form → multipart POST; success/error states |
| `VerifyClient` | Reads `?token=`; POST then GET fallback; renders outcome |

### Verify friendly copy

| Status | User message |
|--------|--------------|
| 201 | API `message` + lead reference id |
| 400 | "Verification link is missing or invalid." |
| 404 | "This verification link is not valid." |
| 409 | "This link has already been used." |
| 410 | "This verification link has expired. Please submit the form again." |

Uses API `detail` when present; table above is fallback.

### shadcn/ui primitives used

Button, Input, Label, Alert — installed via `npx shadcn@latest init` + `add input label alert`.

---

## Manual acceptance

1. `npm run dev` in webapp (API on :8000) — landing renders with Submit + Staff login links
2. `/submit` — valid PDF → 202 check-email message
3. Mailpit verify link → `/verify?token=...` → success → lead created

---

## Out of scope (this track)

- `/login`, `/leads`, middleware, HttpOnly cookie auth
- Resume download proxy (Q-W6 — staff detail page)
