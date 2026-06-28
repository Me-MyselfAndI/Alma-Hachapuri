# Staff pages & layout plan (Track B)

> **Status:** Planning only — no code. Implements confirmed decisions from [WEBAPP_IMPLEMENTATION_PLAN.md](WEBAPP_IMPLEMENTATION_PLAN.md) (Q-W1–Q-W12). Public pages are Track A; this doc covers **staff routes only**.

**Routes in scope:** `/login`, `/leads`, `/leads/[id]`

**Entity references:** [lead.md](entities/lead.md), [account.md](entities/account.md), [permission.md](entities/permission.md)

---

## 1. Staff shell

The staff shell wraps all authenticated routes (`/leads`, `/leads/[id]`). `/login` uses a **minimal layout** (no nav) so unauthenticated users never see staff chrome.

### 1.1 Layout structure

```text
┌─────────────────────────────────────────────────────────────┐
│  HEADER (sticky top, full width, border-b)                    │
│  ┌──────────────┐  ┌─────────────────────┐  ┌────────────┐  │
│  │ Hachapuri    │  │  Leads (nav link)     │  │ user@… ▾   │  │
│  │ (brand)      │  │  (active on /leads*) │  │  Log out   │  │
│  └──────────────┘  └─────────────────────┘  └────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  MAIN (max-w-7xl mx-auto px-4 py-6)                         │
│  {page content}                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Header elements


| Element         | Source                                          | Behavior                                                            |
| --------------- | ----------------------------------------------- | ------------------------------------------------------------------- |
| **Brand**       | **Hachapuri** (confirmed 2026-06-27) — not "Alma" (assessment sender only) | Links to `/leads` when authenticated |
| **Primary nav** | v1: single item **Leads** → `/leads`            | Active state when pathname starts with `/leads`                     |
| **User email**  | `AccountMe.email` from session bootstrap (Q-W2) | Display only; truncate on narrow screens                            |
| **Logout**      | Button or dropdown item                         | `POST /api/auth/logout` → clear HttpOnly cookie → redirect `/login` |


### 1.3 Responsive behavior


| Breakpoint       | Layout                                                                                                                                                         |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **≥ md (768px)** | Horizontal header: brand left, nav center-left, user + logout right                                                                                            |
| **< md**         | Brand left; hamburger or compact row stacks user email above logout; nav collapses to icon + "Leads" text link under brand, or single nav link in a second row |


**Rules:**

- Header stays **sticky** (`sticky top-0 z-50`) with subtle background (`bg-background/95 backdrop-blur`).
- Main content scrolls independently; no sidebar in v1.
- Touch targets ≥ 44px on mobile for logout and nav.

### 1.4 Layout files (implementer reference)

```text
webapp/app/
├── login/
│   └── page.tsx              # no StaffShell — centered card only
└── leads/
    ├── layout.tsx            # wraps children in StaffShell
    ├── page.tsx
    └── [id]/page.tsx
```

`StaffShell` receives `user: AccountMe` from session context (see §3).

---

## 2. Route map & wireframes

### 2.1 `/login`

**Purpose:** Staff sign-in; sets HttpOnly session cookie (Q-W1 B).

**Layout:** Full-viewport centered card; no staff header. Optional small link back to `/` ("← Back to home").

```text
┌─────────────────────────────────────┐
│         Staff sign in               │
│  ┌───────────────────────────────┐  │
│  │ Email                         │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │ Password                      │  │
│  └───────────────────────────────┘  │
│  [ Alert — inline error if any ]    │
│  ┌───────────────────────────────┐  │
│  │        Sign in                │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```


| State          | UI                                                                                                                                             |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| **Idle**       | Empty form; Sign in enabled                                                                                                                    |
| **Submitting** | Button shows spinner + "Signing in…"; fields disabled                                                                                          |
| **401 / 403**  | Destructive Alert: "Invalid email or password" (401) or "Your account has been deactivated" (403) — do not distinguish wrong email vs password |
| **422**        | Alert with validation message                                                                                                                  |
| **Success**    | Redirect to `?next=` param if present and safe (same-origin path starting with `/`), else `/leads`                                             |


**Form fields:** `email` (type email), `password` (type password).

**API path:** Browser `POST /api/auth/login` with JSON `{ email, password }` → Next route calls FastAPI `POST /api/v1/auth/token` (OAuth2 form: `username`, `password`) → sets cookie `alma_access_token` (HttpOnly, SameSite=Lax, Secure=false in local dev).

**Query param:** `?next=/leads/abc-uuid` — middleware may append this when redirecting unauthenticated users (§3.3).

---

### 2.2 `/leads`

**Purpose:** Paginated lead table with filters (Q-W10 A client fetch, Q-W11 B+C filters).

```text
┌──────────────────────────────────────────────────────────────┐
│  Leads                                    (page title, h1)   │
├──────────────────────────────────────────────────────────────┤
│  [ State ▾ All states ]     [ ☐ My leads only ]              │
│                    (filters row — flex wrap on mobile)       │
├──────────────────────────────────────────────────────────────┤
│  ┌────┬──────────┬─────────────────┬──────────┬──────────┐ │
│  │Name│ Email    │ State           │ Assignee │ Submitted│ │
│  ├────┼──────────┼─────────────────┼──────────┼──────────┤ │
│  │…   │ …        │ Pending (badge) │ John S.  │ Jun 27   │ │
│  │…   │ …        │ Reached out     │ Jane D.  │ Jun 26   │ │
│  └────┴──────────┴─────────────────┴──────────┴──────────┘ │
│  (rows link to /leads/[id] — entire row clickable)          │
├──────────────────────────────────────────────────────────────┤
│  Showing 1–20 of 42        [ Previous ]  Page 1  [ Next ]   │
└──────────────────────────────────────────────────────────────┘
```

#### Table columns


| Column        | API field                 | Display                                |
| ------------- | ------------------------- | -------------------------------------- |
| **Name**      | `first_name`, `last_name` | `"Jane Doe"`                           |
| **Email**     | `email`                   | Truncate with tooltip on overflow      |
| **State**     | `state`                   | Human label + color badge (see §2.2.1) |
| **Assignee**  | `assigned_account_name`   | Name or "—" if null                    |
| **Submitted** | `created_at`              | Locale date (e.g. `Jun 27, 2026`)      |
| **Waiting since** | `state_changed_at`    | Relative time (e.g. "3 days") — **v1** |


**Waiting since column (confirmed v1):** relative time from `state_changed_at` (e.g. "3 days") — helps "going cold" signal per [lead.md](entities/lead.md).

Row click navigates to `/leads/{id}`.

#### 2.2.1 State badge labels


| API value      | Label        | Suggested badge variant |
| -------------- | ------------ | ----------------------- |
| `PENDING`      | Pending      | default / yellow        |
| `REACHED_OUT`  | Reached out  | secondary / blue        |
| `QUALIFIED`    | Qualified    | outline / green         |
| `DISQUALIFIED` | Disqualified | outline / orange        |
| `CLOSED`       | Closed       | muted / gray            |


#### Filters (Q-W11 B + C)


| Control           | Query param | Default         | Behavior                                                            |
| ----------------- | ----------- | --------------- | ------------------------------------------------------------------- |
| **State select**  | `state`     | *(empty = all)* | Options: All, Pending, Reached out, Qualified, Disqualified, Closed |
| **My leads only** | `mine=true` | off             | Checkbox; filters to `assigned_account_id` = current user           |


Filter changes reset to **page 1**. Sync filter + page state to URL search params (`?state=PENDING&mine=true&page=2`) so refresh and share work.

#### Pagination


| Param       | Default | UI                                         |
| ----------- | ------- | ------------------------------------------ |
| `page`      | 1       | Previous / Next buttons; disable at bounds |
| `page_size` | 20      | Fixed in v1 (API default)                  |


Footer copy: `Showing {start}–{end} of {total}`.

#### Loading & empty states


| State                   | UI                                                                               |
| ----------------------- | -------------------------------------------------------------------------------- |
| **Loading**             | Skeleton rows (5) or centered Spinner + "Loading leads…"                         |
| **Empty (no rows)**     | Card/Alert: "No leads match your filters." + link to clear filters if any active |
| **401**                 | Redirect to `/login?next=/leads`                                                 |
| **403**                 | Full-page Alert using `read_leads` message (§5.3)                                |
| **Error (5xx/network)** | Destructive Alert + "Retry" button                                               |


#### Data fetch (Q-W10 A)

Client component pattern:

1. Read `searchParams` for `state`, `mine`, `page`.
2. `useEffect` → authenticated fetch `GET /api/v1/leads?...` via staff `apiFetch` helper (cookie sent same-origin; Next proxy adds Bearer server-side or BFF route).
3. Store `{ items, total, page, page_size }` in `useState`; manage loading/error locally.

---

### 2.3 `/leads/[id]`

**Purpose:** Lead detail, state transitions (Q-W8 A), resume download (Q-W6 B).

```text
┌──────────────────────────────────────────────────────────────┐
│  ← Back to leads                                             │
├──────────────────────────────────────────────────────────────┤
│  Jane Doe                              [ Pending ] (badge)   │
│  jane@example.com                                            │
│  Submitted Jun 27, 2026 · Waiting since 2 days               │
├──────────────────────────────────────────────────────────────┤
│  DETAILS (card)                                              │
│  Assignee:     John Smith                                    │
│  Source:       LinkedIn                                      │
│  Prospect ID:  … (monospace, copy optional — stretch)      │
│  Archived:     banner if archived_at set                     │
├──────────────────────────────────────────────────────────────┤
│  RESUME (card)                                               │
│  cv.pdf · 12 KB                    [ Download resume ]       │
├──────────────────────────────────────────────────────────────┤
│  UPDATE STATUS (card)                                        │
│  [ Reached out ] [ Qualified ] [ Disqualified ]              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Optional note (textarea)                                │ │
│  └─────────────────────────────────────────────────────────┘ │
│  [ Alert — transition error / 403 message ]                  │
└──────────────────────────────────────────────────────────────┘
```

#### Sections


| Section          | Content                                                                                  | API                                   |
| ---------------- | ---------------------------------------------------------------------------------------- | ------------------------------------- |
| **Header**       | Full name, email, state badge, `created_at`, relative `state_changed_at`                 | `GET /api/v1/leads/{id}`              |
| **Details card** | Assignee (`assigned_account`), `source`, `prospect_id`; archived banner if `archived_at` | same                                  |
| **Resume card**  | `resume.original_filename`, formatted `size_bytes`; download button                      | `LeadRead.resume`; download via §5.2  |
| **Status card**  | Allowed transition buttons + optional note                                               | `POST /api/v1/leads/{id}/transitions` |


**Back link:** `/leads` preserving list filters if passed via `?from=` or browser history (implementer: `router.back()` fallback to `/leads`).

#### Transition buttons (Q-W8 A)

Show **only allowed next states** for current `lead.state`. Hide section entirely when `CLOSED` (terminal).


| Current state  | Buttons shown                        |
| -------------- | ------------------------------------ |
| `PENDING`      | Reached out, Qualified, Disqualified |
| `REACHED_OUT`  | Pending, Qualified, Disqualified     |
| `QUALIFIED`    | Closed                               |
| `DISQUALIFIED` | Closed                               |
| `CLOSED`       | *(none)*                             |


Each button POSTs `{ to_state, note? }` **immediately on click** — no confirm dialog (confirmed 2026-06-27). On success, refresh lead in place (re-fetch detail). On **400**, show API detail ("Invalid transition"). On **403**, show friendly message (§5.3) including attorney scope copy when applicable.

**Note field:** Optional textarea; maps to `LeadTransitionRequest.note`.

#### Loading & error states


| State               | UI                                      |
| ------------------- | --------------------------------------- |
| **Loading**         | Skeleton blocks matching section layout |
| **404**             | "Lead not found" + link to list         |
| **401**             | Redirect `/login?next=/leads/{id}`      |
| **403 (page load)** | Alert with `read_leads` message         |


---

## 3. Auth flow

All staff auth follows Q-W1 **B**, Q-W2 **A**, Q-W3 **B**.

### 3.1 Session storage (Q-W1 B — HttpOnly cookie)

```text
Browser                    Next.js                         FastAPI
   │                          │                                │
   │ POST /api/auth/login     │                                │
   │ { email, password }      │ POST /api/v1/auth/token        │
   │ ───────────────────────► │ (username, password)           │
   │                          │ ──────────────────────────────►│
   │                          │ ◄── access_token ──────────────│
   │ Set-Cookie:              │                                │
   │ alma_access_token=…      │                                │
   │ HttpOnly; SameSite=Lax   │                                │
   │ ◄─────────────────────── │                                │
```


| Cookie attribute | Value                                               |
| ---------------- | --------------------------------------------------- |
| Name             | `alma_access_token`                                 |
| HttpOnly         | `true`                                              |
| SameSite         | `Lax`                                               |
| Secure           | `false` (local dev); `true` in production           |
| Path             | `/`                                                 |
| Max-Age          | Match JWT expiry (or session cookie if short-lived) |


JavaScript **must not** read the JWT. Staff API calls use Next BFF/proxy that reads the cookie server-side and forwards `Authorization: Bearer …`.

**Logout:** `POST /api/auth/logout` clears cookie (Max-Age=0) → redirect `/login`.

### 3.2 Session bootstrap (Q-W2 A — `/auth/me` on load)

On every full load of staff routes, validate session before rendering protected content.

```text
Staff layout mounts
       │
       ▼
GET /api/auth/me  (Next route reads cookie → proxies GET /api/v1/auth/me)
       │
       ├── 200 → store AccountMe in SessionProvider context
       │         render StaffShell with user.email
       │
       └── 401 → redirect /login?next={currentPath}
```

**Bootstrap UI:** While pending, show full-page spinner or skeleton inside staff layout (avoid flash of empty header).

**AccountMe fields used in UI:**


| Field                     | Use                                                                       |
| ------------------------- | ------------------------------------------------------------------------- |
| `id`                      | "My leads" filter scope check                                             |
| `email`                   | Header display                                                            |
| `first_name`, `last_name` | Optional greeting (stretch)                                               |
| `role`                    | Debug/demo only in v1                                                     |
| `permissions`             | Available for future Q-W9 A-style gating; v1 shows all actions per Q-W9 B |


Re-fetch `/auth/me` after login success before redirect.

### 3.3 Route protection (Q-W3 B — middleware)

**File:** `webapp/middleware.ts`

**Matcher:** `/leads/:path`*, optionally `/api/auth/me` passthrough.


| Condition                                                    | Action                                                                   |
| ------------------------------------------------------------ | ------------------------------------------------------------------------ |
| Request to `/leads/*` **without** `alma_access_token` cookie | Redirect `302` → `/login?next={pathname+search}`                         |
| Cookie present                                               | Allow request (full validation deferred to bootstrap + API)              |
| Request to `/login` **with** valid cookie                    | Optional: redirect to `/leads` (avoid login page when already signed in) |


**Middleware does not** call FastAPI on every request in v1 (keep fast). Presence of cookie is sufficient for edge gate; `/auth/me` bootstrap catches expired/invalid tokens.

**Unauthenticated access to `/login`:** Always allowed.

---

## 4. Lead list — implementation notes

Consolidates Q-W10 A and Q-W11 B+C.

### 4.1 API contract

```
GET /api/v1/leads?state={LeadState}&mine={bool}&page={int}&page_size=20
Authorization: Bearer … (via proxy)
```

Response: `Paginated[LeadListItem]` per [lead.md](entities/lead.md#L2).

### 4.2 Client fetch helper

Extend shared `lib/api-client.ts` (from Track A) or add `lib/staff-api.ts`:

```typescript
staffFetch<T>(path, options?)  // same-origin /api/v1/…; credentials: 'include'
```

Next rewrite/proxy (Q-W5 B) attaches Bearer from cookie on server-side forward.

### 4.3 URL state matrix


| User action               | URL change                       |
| ------------------------- | -------------------------------- |
| Select state "Pending"    | `?state=PENDING&page=1`          |
| Toggle "My leads only" on | `?mine=true&page=1`              |
| Next page                 | `?page=2` (+ preserve filters)   |
| Clear filters             | Remove `state`, `mine`; `page=1` |


---

## 5. Lead detail — transitions, resume, permissions

### 5.1 State transitions (Q-W8 A)

**Endpoint:** `POST /api/v1/leads/{id}/transitions`

**Body:**

```json
{ "to_state": "REACHED_OUT", "note": "optional" }
```

**Client transition map** (must match API — [WEBAPP_IMPLEMENTATION_PLAN.md](WEBAPP_IMPLEMENTATION_PLAN.md#allowed-transitions-client-hint-map)):


| Current        | Allowed `to_state`                         |
| -------------- | ------------------------------------------ |
| `PENDING`      | `REACHED_OUT`, `QUALIFIED`, `DISQUALIFIED` |
| `REACHED_OUT`  | `PENDING`, `QUALIFIED`, `DISQUALIFIED`     |
| `QUALIFIED`    | `CLOSED`                                   |
| `DISQUALIFIED` | `CLOSED`                                   |
| `CLOSED`       | *(none)*                                   |


Button label map: `REACHED_OUT` → "Reached out", etc.

### 5.2 Resume download (Q-W6 B — Next proxy)

Direct link to FastAPI `/api/v1/leads/{id}/resume` **will 401** in browser (no Bearer on navigation).

**Implement:**

```text
User clicks "Download resume"
       │
       ▼
GET /api/leads/[id]/resume   (Next Route Handler)
       │ reads alma_access_token cookie
       │ serverFetch GET /api/v1/leads/{id}/resume + Bearer
       ▼
Stream binary to browser with Content-Disposition from upstream
```

**UI:** `<Button asChild><a href={`/api/leads/${id}/resume`} download>Download resume</a></Button>` or button that navigates to same URL.

Handle **404** (no resume), **403** (permission), **401** (session expired → redirect login).

### 5.3 Permission errors (Q-W9 B)

**Policy:** Show all actions; do **not** hide buttons by role in v1. On **403**, display user-friendly copy — not raw `"Insufficient permissions"`.

**Implement in:** `webapp/lib/permission-messages.ts`

Map action context → permission key → message. Full table from [WEBAPP_IMPLEMENTATION_PLAN.md § Q-W9](WEBAPP_IMPLEMENTATION_PLAN.md#q-w9--permission-denied-messages-implementation-spec):


| Permission key  | User-facing message                                                                     |
| --------------- | --------------------------------------------------------------------------------------- |
| `read_leads`    | You don't have permission to view leads. Your role needs the **read leads** capability. |
| `write_lead`    | You don't have permission to update this lead. Your role needs **write lead** access.   |
| `assign_lead`   | You can't change assignment. Your role needs **assign lead** access.                    |
| `read_prospect` | You can't view prospect details. Your role needs **read prospect** access.              |
| `send_email`    | You can't send email from here. Your role needs **send email** access.                  |
| `read_emails`   | You can't view the email log. Your role needs **read emails** access.                   |
| `export_leads`  | You can't export leads. Your role needs **export leads** access.                        |
| `manage_users`  | You can't manage accounts. Your role needs **manage users** access.                     |


**Attorney assignee scope** ([permission.md](entities/permission.md) — assignment-scoped `write_lead`):

When transition or update returns **403** and the action was `write_lead` on the detail page, **also show:**

> You can only update leads assigned to you.

Use this in addition to (or instead of) the generic `write_lead` message when the UI knows the current user is an attorney and `lead.assigned_account_id !== user.id`.

**Staff page mappings:**


| Page / action      | Permission key on 403                   |
| ------------------ | --------------------------------------- |
| Load `/leads`      | `read_leads`                            |
| Load `/leads/[id]` | `read_leads`                            |
| Transition button  | `write_lead` (+ attorney scope message) |
| Download resume    | `read_leads`                            |


---

## 6. shadcn/ui components per page

Per Q-W12 B. Install via `npx shadcn@latest init` in `webapp/` (Track A / W0 may already do this).

### 6.1 Shared / shell


| Component                  | Use                                       |
| -------------------------- | ----------------------------------------- |
| `Button`                   | Logout, pagination, transitions, download |
| `DropdownMenu`             | Optional compact user menu (mobile)       |
| `Separator`                | Header border                             |
| `Skeleton`                 | Loading states                            |
| `Spinner` / `Loader2` icon | Inline loading                            |


### 6.2 `/login`


| Component                                                      | Use                  |
| -------------------------------------------------------------- | -------------------- |
| `Card`, `CardHeader`, `CardTitle`, `CardContent`, `CardFooter` | Login form container |
| `Input`                                                        | Email, password      |
| `Label`                                                        | Field labels         |
| `Button`                                                       | Submit               |
| `Alert`, `AlertDescription`                                    | Auth errors          |


### 6.3 `/leads`


| Component                                                                 | Use                  |
| ------------------------------------------------------------------------- | -------------------- |
| `Table`, `TableHeader`, `TableBody`, `TableRow`, `TableHead`, `TableCell` | Lead table           |
| `Select`, `SelectTrigger`, `SelectValue`, `SelectContent`, `SelectItem`   | State filter         |
| `Checkbox`                                                                | "My leads only"      |
| `Badge`                                                                   | State column         |
| `Alert`                                                                   | Empty/error states   |
| `Button`                                                                  | Pagination prev/next |
| `Skeleton`                                                                | Table loading        |


### 6.4 `/leads/[id]`


| Component                                        | Use                                     |
| ------------------------------------------------ | --------------------------------------- |
| `Card`, `CardHeader`, `CardTitle`, `CardContent` | Detail sections                         |
| `Badge`                                          | Current state in header                 |
| `Button`                                         | Transition actions, download, back link |
| `Textarea`                                       | Transition note                         |
| `Alert`                                          | Errors, archived banner, 403 messages   |
| `Skeleton`                                       | Detail loading                          |


---

## 7. Component folder tree

All staff-specific UI lives under `webapp/components/staff/`. Shared auth session wrapper under `components/auth/`. shadcn primitives under `components/ui/`.

```text
webapp/components/
├── auth/
│   └── SessionProvider.tsx       # Q-W2 bootstrap context
├── staff/
│   ├── shell/
│   │   ├── StaffShell.tsx        # header + nav + main slot
│   │   ├── StaffHeader.tsx
│   │   ├── StaffNav.tsx
│   │   └── UserMenu.tsx          # email + logout
│   ├── login/
│   │   └── LoginForm.tsx
│   ├── leads/
│   │   ├── LeadListPage.tsx      # client page orchestrator
│   │   ├── LeadTable.tsx
│   │   ├── LeadTableRow.tsx
│   │   ├── LeadFilters.tsx       # state select + mine checkbox
│   │   ├── LeadPagination.tsx
│   │   ├── LeadStateBadge.tsx    # shared with detail
│   │   ├── LeadDetailPage.tsx
│   │   ├── LeadDetailHeader.tsx
│   │   ├── LeadDetailCards.tsx   # details + resume sections
│   │   ├── LeadTransitionPanel.tsx
│   │   └── ResumeDownloadLink.tsx
│   └── shared/
│       ├── LoadingSkeleton.tsx
│       └── ErrorAlert.tsx
└── ui/                           # shadcn generated
    ├── button.tsx
    ├── card.tsx
    …
```

**Lib helpers (not components):**

```text
webapp/lib/
├── api.ts                        # serverFetch — cookie → Bearer (Route Handlers)
├── api-client.ts                 # staffFetch / publicFetch (extends Track A)
├── permission-messages.ts        # Q-W9 copy + getPermissionMessage()
├── lead-transitions.ts           # ALLOWED_TRANSITIONS map
└── types.ts                      # AccountMe, LeadListItem, LeadRead, Paginated, LeadState
```

**Route handlers:**

```text
webapp/app/api/
├── auth/
│   ├── login/route.ts
│   ├── logout/route.ts
│   └── me/route.ts               # bootstrap proxy
└── leads/
    └── [id]/
        └── resume/route.ts       # Q-W6 B stream proxy
```

---

## 8. Implementation slices (staff coding agent)

Ordered steps for a future implementer. Depends on **W0 scaffold** (Next + shadcn + `next.config` rewrites) from [WEBAPP_IMPLEMENTATION_PLAN.md](WEBAPP_IMPLEMENTATION_PLAN.md); Track A may deliver `api-client.ts` and rewrites first.


| Slice                              | Owns                                                                                                             | Depends on | Acceptance                                                                                                                                         |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| **S1 · Auth infrastructure**       | `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`, `lib/api.ts` server fetch, cookie constants | W0         | Login via curl/Postman sets HttpOnly cookie; cookie not readable from `document.cookie`                                                            |
| **S2 · Middleware + session**      | `middleware.ts` matcher for `/leads/`*, `SessionProvider`, `StaffShell` skeleton                                 | S1         | Unauthenticated `/leads` → `/login?next=…`; bootstrap shows spinner then user email                                                                |
| **S3 · Login page**                | `/login`, `LoginForm`, error states, `?next=` redirect                                                           | S2         | Valid seed attorney → lands on `/leads`; bad password → inline error; logout returns to login                                                      |
| **S4 · Lead list**                 | `/leads`, table, pagination, state filter, mine toggle, URL sync, client fetch                                   | S3         | List renders seed leads; filters change URL; pagination works; empty state shows                                                                   |
| **S5 · Lead detail + transitions** | `/leads/[id]`, detail sections, `LeadTransitionPanel`, `lib/lead-transitions.ts`, 400/403 handling               | S4         | PENDING → REACHED_OUT succeeds; illegal button not shown; 403 shows friendly message                                                               |
| **S6 · Resume download**           | `GET /api/leads/[id]/resume` proxy, `ResumeDownloadLink`                                                         | S5         | Click downloads PDF with correct filename; 401 redirects to login                                                                                  |
| **S7 · Polish**                    | Responsive header, skeleton polish, `permission-messages.ts` wired everywhere, manual test script                | S6         | Full staff flow in [WEBAPP_IMPLEMENTATION_PLAN.md manual test](WEBAPP_IMPLEMENTATION_PLAN.md#manual-test-script-definition-of-done) steps 3–5 pass |


**Parallelism:** S1–S7 are sequential. Public pages (Track A) can run in parallel after W0.

**Manual smoke test (staff subset):**

1. `/login` — attorney credentials → `/leads`
2. Filter by Pending + toggle My leads — URL updates, table filters
3. Open lead — transition to Reached out with note — state badge updates
4. Download resume — file saves
5. Logout — `/leads` redirects to login
6. Sign in as readonly — list works; transition click → friendly 403

---

## 9. Product decisions (confirmed 2026-06-27)

| # | Topic | Decision |
|---|-------|----------|
| 1 | **Brand name** | **Hachapuri** — use in staff shell, public shell, page titles. "Alma" is the assessment company only; not shown in product UI. |
| 2 | **List column "Waiting since"** | **Include in v1** — relative time from `state_changed_at`. |
| 3 | **State transition UX** | **Immediate** — button click POSTs transition; no confirmation modal. |
| 4 | **Stretch features** | **Deferred** — document only; not in v1 scope (see §9.1). |

### 9.1 Deferred to later (not v1 — no implementation time now)

| Feature | API exists | Notes |
|---------|------------|-------|
| State history timeline on detail | `GET /leads/{id}/state-history` | Add timeline card when time allows |
| Email log on detail | `GET /leads/{id}/emails` | Audit list for staff |
| Staff send follow-up email | `POST /leads/{id}/emails` + templates | Intake/admin workflow |
| CSV export button | `GET /leads/export` | Header action when `export_leads` |
| Assignee dropdown / reassignment UI | PATCH lead + `assign_lead` | Beyond read-only assignee display |
| Admin account management | `/api/v1/accounts/*` | Separate admin area |

---

## 10. Open questions

All staff UX decisions are **locked** in Q-W1–Q-W12 and §9 above. No open questions for this track.


| Topic             | Resolution                          |
| ----------------- | ----------------------------------- |
| Brand             | **Hachapuri** (§9)                  |
| Session storage   | Q-W1 **B** — HttpOnly cookie        |
| Bootstrap         | Q-W2 **A** — `/auth/me`             |
| Route guard       | Q-W3 **B** — middleware             |
| Resume download   | Q-W6 **B** — Next route proxy       |
| Transition UI     | Q-W8 **A** — allowed buttons; **immediate** click (§9) |
| Permission UX     | Q-W9 **B** — show all; friendly 403 |
| List data loading | Q-W10 **A** — client fetch          |
| List filters      | Q-W11 **B+C** — state + mine        |
| Waiting since col | **v1** (§9)                         |
| Styling           | Q-W12 **B** — shadcn/ui             |

**Deferred (§9.1 — later, not v1):** state history, email log, staff send email, CSV export, assignee UI, admin accounts.

---

## Related docs

- [WEBAPP_IMPLEMENTATION_PLAN.md](WEBAPP_IMPLEMENTATION_PLAN.md) — master plan, Q-W decisions, W0–W8 slices
- [AGENT_BRIEFS.md](AGENT_BRIEFS.md) — Track B scope
- [RUN_LOCALLY.md](RUN_LOCALLY.md) — dev stack
- [entities/API_CATALOG.md](entities/API_CATALOG.md) — route index

