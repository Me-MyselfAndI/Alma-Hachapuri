# Requirements

Original assignment brief. Scope additions and design decisions live in other docs (`ARCHITECTURE.md`, `ASSUMPTIONS.md`, `FEATURES.md`).

---

## Assignment Overview

Develop an application to support creating, getting, and updating leads.

---

## Functional Requirements

### Lead Form (Public)

A lead is a form **publicly available** for prospects to fill in.

**Required fields:**

- First name
- Last name
- Email
- Resume / CV

### Lead Submission Flow

Once the lead is submitted by a prospect, the application will send emails to:

1. The prospect
2. An attorney inside the company

### Internal UI (Authenticated)

The application powers an internal UI guarded by auth to render a list of leads with all the information filled in by the prospect.

### Lead State

Each lead has a state:

| State | Description |
|-------|-------------|
| `PENDING` | Initial state when a lead is submitted |
| `REACHED_OUT` | Set manually by an attorney after they reach out to the prospect |

---

## Tech Requirements

- Create a **system design** to fulfill the above requirements
- Develop the web app and APIs **end-to-end**
- **APIs:** FastAPI
- **Web app:** Next.js
- **Storage:** Persist data
- **Email:** Integrate with an email service
- **Code quality:** Structure the code similar to a production-level repo

---

## Submission Guidance

### Code & Repository

- Submit code to a **publicly available GitHub repo**
- Include a document on **how to run the application locally** (in the same repo)
- Include a **design document** explaining why/how design choices were made (in the same repo)

### Coding-Agent Usage Documentation

Heavy use of coding agents is encouraged — evaluation focuses on **how** agents are used, not whether.

**Required deliverables:**

1. **Short writeup (½ page max):**
   - Which tools were used
   - What was delegated vs. written manually, and why
   - One place the agent produced wrong or subtly bad code — how it was caught and fixed

2. **Representative prompt logs or session transcripts** (excerpts are fine)

3. **Attribution** in commits or a `NOTES` file marking agent-generated vs. hand-written code

### Final Deliverables

- Upload the **GitHub link** in the assignment document within **6 hours** of starting the exercise
- Upload a **short screen recording** (e.g., Loom) showing the E2E workflow
