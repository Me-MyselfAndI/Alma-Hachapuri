# Alma Lead Intake (Hachapuri)

A local demo of **lead intake for a law firm**. This README is written so you can **clone, run, and try every main feature yourself** — no walkthrough from the author required.

**Repository:** [github.com/Me-MyselfAndI/Alma-Hachapuri](https://github.com/Me-MyselfAndI/Alma-Hachapuri)

---

## What you are trying out

| Persona | What they do |
|---------|----------------|
| **Prospect** (public) | Submit name, email, and resume → confirm via email link → lead is created |
| **Staff** (internal) | Log in → browse and filter leads → open a lead → download resume → update status |

Behind the scenes: **Next.js** webapp, **FastAPI** API, **PostgreSQL** database, **local file storage** for resumes. Email is caught by **Mailpit** on your machine — nothing is sent to real inboxes in local dev.

---

## Before you begin

### Install once

| Tool | Why | Check |
|------|-----|-------|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | Database + fake email inbox | `docker --version` |
| [Python 3.13+](https://www.python.org/downloads/) | API | `python --version` |
| [Node.js 18+](https://nodejs.org/) | Webapp | `node --version` |

Start **Docker Desktop** and wait until it is fully running before continuing.

### Get the code

```powershell
git clone https://github.com/Me-MyselfAndI/Alma-Hachapuri.git
cd Alma-Hachapuri
```

### One-time setup

From the repo root (folder with `webapp/`, `api/`, `docker-compose.yml`):

```powershell
python scripts/setup.py
```

Or: `npm run setup`

This creates `api/.venv`, installs dependencies, and writes `.env` / `webapp/.env.local`.

### Start the app

```powershell
python scripts/dev.py run --target all
```

Or: `npm run dev`

Leave this terminal open. Press **Ctrl+C** when finished.

| Service | URL |
|---------|-----|
| **Webapp** (start here) | http://localhost:3000 |
| **Mailpit** (all email) | http://localhost:8025 |
| API docs (optional) | http://localhost:8000/docs |

---

## Walkthrough — try the full flow (~15 minutes)

Use **three browser tabs**: webapp, Mailpit, and (optional) a second webapp session for staff.

### Part 1 — Prospect submits a lead

1. Open http://localhost:3000
2. Click **Submit a lead**
3. Fill in:
   - First / last name — any values
   - Email — use something unique you can search for in Mailpit, e.g. `you+test1@example.com`
   - Resume — any **PDF, DOC, or DOCX** under 10 MB
   - Source — optional
4. Click submit

**You should see:** a “Check your email” message. It may link to Mailpit — use that link.

**Important:** verification email does **not** go to Gmail or Outlook. It only appears in **Mailpit** at http://localhost:8025.

5. In Mailpit, find the message to your test email (search by address if the inbox is busy)
6. Open the **Verify your email** message and click the verification link (or copy the link into the browser)

**You should see:** a success / thank-you page. The lead now exists in the database.

**Also check Mailpit** — two more emails should appear:
- **Prospect:** “We received your submission” (confirmation)
- **Attorney:** “New lead: …” alert to `attorney@example.com`

The lead is **not** created until step 6. Submitting the form alone only starts verification.

---

### Part 2 — Staff reviews the lead

1. Open http://localhost:3000/login (or click **Staff login** from the home page)
2. Sign in as the default assignee:

   | Email | Password |
   |-------|----------|
   | `attorney@example.com` | `attorney123` |

3. You land on **Leads** with a table: name, email, state, assignee, submitted date, **waiting since**

**Try the filters:**
- **State** — e.g. show only `Pending` (new verified leads start here)
- **My leads only** — shows leads assigned to you (`attorney@example.com` is the default assignee)

4. Click the row for the lead you just created

**On the detail page:**
- Prospect name, email, current **state** badge, assignee, resume download
- **Send email** card — pick a template, click **Send email**, then check **Mailpit** (not your real inbox)
- **Change status** card — pick a new status from the dropdown, optionally add a note, click **Change status**

5. Go **Back to leads** — the state column should reflect your change

---

### Part 3 — Lead lifecycle (status model)

Leads move through a simple “whose turn is it?” workflow:

| State | Meaning |
|-------|---------|
| **Pending** | Our turn — new lead or prospect replied; staff owe the next action |
| **Reached out** | Their turn — we contacted them; waiting on the prospect |
| **Qualified** / **Disqualified** | Fit decision (from Pending or Reached out) |
| **Closed** | Terminal — after Qualified or Disqualified |

Typical ping-pong: **Pending** ↔ **Reached out** until staff mark **Qualified** or **Disqualified**, then **Closed**.

From the detail page, only **valid** next states appear as buttons (invalid transitions are blocked by the API).

---

### Part 4 — Roles and permissions (optional, ~3 min)

Log out (top-right), then try other demo accounts:

| Email | Password | What to expect |
|-------|----------|----------------|
| `intake@example.com` | `intake123` | Can view and update leads like intake staff |
| `admin@example.com` | `admin123` | Full admin access |
| `readonly@example.com` | `readonly123` | Can **view** leads; status buttons should fail with a clear permission message |

Use **readonly** on a lead detail page and attempt a status change — you should see a friendly “you don’t have permission” message, not a blank error.

---

## Demo accounts (local dev only)

All four are created automatically the first time the API starts:

| Email | Password | Role |
|-------|----------|------|
| `attorney@example.com` | `attorney123` | Attorney — default assignee for new leads |
| `intake@example.com` | `intake123` | Intake coordinator |
| `admin@example.com` | `admin123` | Admin |
| `readonly@example.com` | `readonly123` | Read-only |

---

## Mailpit — how local email works

Open http://localhost:8025 anytime.

| When | What appears |
|------|----------------|
| After form submit | Verification link email |
| After clicking verify | Prospect confirmation + attorney “new lead” alert |
| After staff **Send email** on lead detail | Follow-up template to prospect |

If you “never got email,” you are almost certainly looking at a real inbox. **Always use Mailpit** in local dev.

---

## Quick checklist

Use this to confirm everything works:

- [ ] http://localhost:3000 loads the Hachapuri home page
- [ ] Submit form → “Check your email” message
- [ ] Verification link in Mailpit → success page
- [ ] Staff login → leads list shows your test lead
- [ ] Lead detail → resume downloads correctly
- [ ] Status change → list and detail show new state
- [ ] Readonly user → cannot change status (clear error)

---

## Troubleshooting

| Problem | What to do |
|---------|------------|
| Docker / compose errors | Start Docker Desktop, wait until ready, run `python scripts/dev.py run --target all` again |
| Port 3000 or 8000 in use | Stop other dev servers (`Ctrl+C` in old terminals); `netstat -ano \| findstr :8000` on Windows |
| No verification email | Open Mailpit at http://localhost:8025; search by the email you typed in the form |
| Login fails | Check http://localhost:8000/health shows `{"status":"ok"}`; restart the dev command |
| Lead list empty after verify | Confirm you completed verification (Part 1 step 6); try state filter “Pending” |
| PowerShell blocks scripts | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |

More startup detail: [docs/RUN_LOCALLY.md](docs/RUN_LOCALLY.md)

---

## Daily use (after first setup)

```powershell
python scripts/dev.py run --target all
```

No need to run `setup.py` again unless dependencies changed.

---

## Explore the API (optional)

Swagger UI at http://localhost:8000/docs — useful for inspecting endpoints (auth, leads, email templates, state history). Staff endpoints require a Bearer token from `POST /api/v1/auth/token` (use **Authorize** in Swagger with demo credentials).

The web UI covers the main reviewer path; the API docs show the full backend surface.

---

## Project layout

```text
webapp/              Next.js — public pages + staff dashboard
api/                 FastAPI — business logic, auth, email
db/                  PostgreSQL migrations (Alembic)
storage/uploads/     Resume files on disk
scripts/             setup.py, dev.py
docs/                Architecture, requirements, feature status
```

---

## Further reading

| Doc | Contents |
|-----|----------|
| [docs/RUN_LOCALLY.md](docs/RUN_LOCALLY.md) | Manual startup, migrations, API smoke commands |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Flow diagrams and design |
| [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) | Original brief |
| [docs/FEATURES.md](docs/FEATURES.md) | What is built vs deferred |
| [docs/AGENT_USAGE_SUBMISSION.md](docs/AGENT_USAGE_SUBMISSION.md) | Coding-agent usage writeup (assessment) |
| [NOTES.md](NOTES.md) | Agent-generated vs hand-written code attribution |

<details>
<summary>For developers — automated checks</summary>

```powershell
python scripts/dev.py test --target all   # API pytest + webapp lint + build
```

API tests use in-memory SQLite and do not require Docker. Full manual walkthrough above requires the running stack.

</details>
