# Agent mistakes & corrections

Log of places the agent was wrong or misleading and how it was caught and fixed. Required for assignment agent-usage writeup.

Format: **What went wrong** → **User correction** → **Fix**

---

| # | When | Area | What went wrong | User correction | Fix |
|---|------|------|-----------------|-----------------|-----|
| 1 | 2026-06-27 ~13:26 | Questions log | Fabricated timestamps with no source | Pointed out times were hallucinated | Switched to approved `Get-Date` command; marked #1–17 unrecorded, then approximated from 12:10 PT anchor |
| 2 | 2026-06-27 ~13:28 | Questions log | Still approximated times instead of running shell command | Asked to run approved command every time for exact value | Run `Get-Date -Format 'yyyy-MM-dd HH:mm K'` each entry; exact from #18+ |
| 3 | 2026-06-27 ~13:30 | Questions log | Ran timestamp at start of reply | Run at **end** so user can read while command runs | Moved command to end of each response |
| 4 | 2026-06-27 (early) | Assumptions doc | Treated brief requirements as assumptions (A13 FastAPI/Next.js) | Requirements vs assumptions are different | Removed; kept in `REQUIREMENTS.md` / `ARCHITECTURE.md` |
| 5 | 2026-06-27 (early) | Assumptions doc | Treated tech choices (Postgres, email, async LLM) as assumptions | Same — assumptions are unspecified truths, not stack picks | Moved to `ARCHITECTURE.md` → Technical choices |
| 6 | 2026-06-27 (early) | Assumptions doc | Put entity model inside assumptions | Entities belong in architecture | Moved to `ARCHITECTURE.md`; later to `docs/entities/` |
| 7 | 2026-06-27 (early) | Assumptions doc | Marked A6 (two states only) as confirmed | State lifecycle needs more design | Moved to PLAN ticket F2.1 |
| 8 | 2026-06-27 (early) | Assumptions doc | A12 attorney notification routing as assumption | It's design work to plan | Moved to PLAN ticket F3.1 |
| 9 | 2026-06-27 (early) | Domain terms | Overconfident lead/prospect split; didn't address user's CRM mental model | User thought lead = customer, prospect = campaign | Elaborated with mattress-store analogy; clarified assignment wording vs implementation |
| 10 | 2026-06-27 ~13:39 | Feature board | Column named **Ready** — confusing vs “planned but not started” | Rename to **Not started** | Updated `FEATURES.md` workflow and board |
| 11 | 2026-06-27 ~13:28 | Architecture explanation | Implied Postgres / local uploads are “APIs you just use” | User asked how FastAPI “uses” them — aren't standalone | Added “Who talks to what”; clarified FastAPI owns all backend I/O |
| 12 | 2026-06-27 ~13:41 | Entity design | `role` as string enum on `accounts` | Role should be an entity | Added `role.md`, `permission.md`, `role_permissions`; `accounts.role_id` FK |
| 13 | 2026-06-27 (ongoing) | Questions log | Did not update log every question early in session | Asked to update after every question + confirm feature changes | Protocol restated at top of each reply |

---

## Patterns to avoid

- Do not invent timestamps, IDs, or “confirmed” statuses without user or shell evidence
- Keep **requirements**, **assumptions**, **architecture choices**, and **PLAN tickets** in separate docs
- Distinguish **decision made** vs **direction set but still PLAN** on feature board
- Frameworks (Postgres, disk) are infrastructure FastAPI integrates — not browser-facing APIs

---

## For submission writeup (draft bullet)

**Example mistake for ½-page agent doc:** Hallucinated question-log timestamps twice; user required an approved shell command. Fix: `Get-Date` at end of every reply, `#1–17` marked unrecorded/approximated, no guessed times after that.
