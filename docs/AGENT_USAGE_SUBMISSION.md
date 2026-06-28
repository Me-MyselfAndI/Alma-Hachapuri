# Coding agent usage — submission

> Alma assessment deliverable. Repo: [Me-MyselfAndI/Alma-Hachapuri](https://github.com/Me-MyselfAndI/Alma-Hachapuri)

---

### Tools


| Tool                        | Role                                                                                                   |
| --------------------------- | ------------------------------------------------------------------------------------------------------ |
| **Cursor IDE (Agent mode)** | Primary environment — chat coordinator, inline edits, terminal, multi-file refactors                   |
| **Cursor Task / subagents** | Parallel workers for entity API slices, e2e flow tests, webapp tracks (public pages, staff UI, polish) |
| **Shell + Docker**          | Postgres, Mailpit, migrations, pytest, `scripts/dev.py` smoke runs                                     |


### What I delegated vs. did myself

**I did primarily myself:** most of the planning and all high-level decisions, as well as decisions on how to orchestrate the development process. I spent ~1/3 of the expended time writing the design doc. While LLM was involved too it was used only as a method to identify gaps I could have missed. This way, I wrote out most entities to be interacted with (such as leads, attorneys, etc) and the full set of API signatures that they were expected to behave by, access roles, etc. I also hevaily policed the agent on how it distributed work between sub-agents to make it most efficient. Last, I manually looked through the code to identify potential bugs and security conserns.

**I delegated (to agents):** Almost all code implementation; once the signatures of all APIs and mutual relationships of all relevant components were written out, I directed Cursor to spin out subagents to independently develop each component. I made Cursor write a Kanban board-like document to further help agents coordinate. I also very closely interacted with a separate Cursor session to identify bugs I may have missed myself and help me decide on how to fix them.

**Why:** Overall, I find it most efficient to define a very strict set of requirements, resolve the maximum possible amount of issues before implementation starts and have a concrete set of documents for LLMs to use. This way, I can afford having minimal involvement with the code itself, which in real-life projects, would prevent excessive deploys and debug time. Additionally, I have not used Next.js in three years and FastAPI any time before in my career. This distribution of labor ensures that most arising issues happen before code is developed, meaning I can reason about them without having to understand unfamiliar frameworks. 

### One wrong / subtly bad output — catch and fix

As a result of my approach, much fewer bugs happened than could have - the code worked right from the second test run, and the rest of the changes were about polishing minor issues. Out of code bugs that did arise, the most major was related to sending duplicate leads into the system:

**Bug:** Two simultaneous lead requests (such as a double-click) could create duplicate leads

**Cause:** Application is sent at the time when customer's email is verified. If the prospect quickly double-clicked the verification link or otherwise sends the request too fast more than once, this would cause double leads. 

**Caught:** investigation of potential security concerns with a bugfix agent revealed this problem.

**Fix:** Added a pending lead id as a deduplication mechanism for such situations.

---

## Representative prompt excerpts

From the coordinator and bugfix sessions

### 1 — Doc taxonomy (early planning)

> Great job overall. Some points  
>
> - A6 is not right, we'll later need to think through it. Put it in PLAN  
> - A12 is not an assumption, it is a thing to plan  
> - Not sure why ENTITIES is in the assumptions doc — it should be in the architecture doc  
> - FastAPI and NextJS in requirements — why did A14–16 appear? These aren't assumptions…

### 2 — Entity model simplification

> Account vs Attorney — there is no other non-attorney users? If there are admins vs attorneys, we could just have these with different access roles and the acct type would be an immutable field.  
> We can do accts.role, i prefer that

### 3 — Parallel agent coordination

> Create an agent for each entity. For now, each agent should evaluate reasonable necessary pre-conditions for running each entity's task and relay back to you. That includes things like states of items, permissions, roles, etc.

### 4 — Webapp build tracks

> Set up agents as follows:  
>
> - Send email (public page) — simple, just document decisions  
> - Another agent to plan the employee pages and layout  
> - Another agent to make commands that build everything, run all tests and locally spin up backend, frontend or both

### **5** — **Triage in batches: fix now, defer later, track the rest**

> *"I am gonna ask for actions, some of which will say it is meant to be implemented later — create a file for next steps to elaborate on these all. Perform the actions in regards to these points: 1 - … 4 - we will later … 5 - Make it a 422 …"*

### **6** — **Propose a fix, stress-test it, then approve implementation**

> *"Would it be an adequate solution for l1b to have timestamp-based verification — make, say, a 5 min timeout. If a request is not processed in a timeout duration, but they both come from the same email, the second one overrides the first"*  
> *→ later: "implement that pls"*

---

## Code attribution

Virtually all code was written by agents; attribution notes would not be relevant