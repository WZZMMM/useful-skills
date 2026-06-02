---
name: do-agent-brainstorm
description: "Use this skill when the user asks to '/do-agent-brainstorm'. Combines do-agent's output control with multi-agent-brainstorming's structured review process. Runs a multi-stage brainstorming workflow with full file-based tracking: plans, role reviews, decision logs, and final deliverables all saved to a temporary working directory."
version: 0.1.0
source: WZM
---
# Do-Agent Brainstorm

> Structured Brainstorming with Output Control

## Purpose

Combine **do-agent's file-based execution tracking** with **multi-agent-brainstorming's structured review roles** to produce a robust, auditable brainstorming process where every step is persisted to disk.

This skill:

- Generates and stress-tests designs through constrained review roles
- Persists all plans, reviews, decisions, and deliverables to a temporary directory; other outputs if asked by the user
- Enforces do-agent's output discipline (sub-agents save locally, main agent receives only summaries)
- Terminates only when all exit criteria are met

---

## Execution Mode

```
explore → design → review (sequential) → arbitrate → revise → deliver
```

---

## Working Directory Setup

1. Get current date/time (Beijing time)
2. Create temporary working directory:
   ```
   agent_tasks/{short_task_description}_yyyyMMddhh/
   ```

   If directory already exists, append a numeric suffix to avoid overwriting.

### Required Files in Working Directory

| File                     | Created By                      | Purpose                                |
| ------------------------ | ------------------------------- | -------------------------------------- |
| `plan.md`              | Main Agent                      | Execution plan and task tracking       |
| `design.md`            | Primary Designer                | The design under review                |
| `review_skeptic.md`    | Skeptic Agent                   | Challenge and risk analysis            |
| `review_constraint.md` | Constraint Guardian             | Non-functional constraint validation   |
| `review_user.md`       | User Advocate                   | Usability and user-perspective review  |
| `decision_log.md`      | Main Agent (updated throughout) | All decisions, objections, resolutions |
| `arbitration.md`       | Arbiter Agent                   | Final裁决 and disposition              |
| `deliverable.md`       | Main Agent                      | Final approved output                  |

---

## Agent Roles

Each agent operates under a **hard scope limit**. No agent may exceed its mandate.

### Primary Designer

**Owns:** The design itself

**May:**

- Ask clarification questions
- Propose designs and alternatives
- Revise designs based on reviewer feedback

**May NOT:**

- Self-approve the final design
- Ignore reviewer objections
- Invent requirements after understanding lock

**Output:** Saves design to `design.md`

---

### Skeptic / Challenger

**Assumption:** The design will fail. Why?

**May:**

- Question assumptions
- Identify edge cases and failure modes
- Highlight ambiguity or overconfidence
- Flag YAGNI violations

**May NOT:**

- Propose new features
- Redesign the system
- Offer alternative architectures

**Output:** Saves analysis to `review_skeptic.md`

---

### Constraint Guardian

**Focus:** Non-functional and real-world constraints

**Scope:**

- Performance
- Scalability
- Reliability
- Security & privacy
- Maintainability
- Operational cost

**May:**

- Reject designs that violate constraints
- Request clarification of limits

**May NOT:**

- Debate product goals
- Suggest feature changes
- Optimize beyond stated requirements

**Output:** Saves analysis to `review_constraint.md`

---

### User Advocate

**Focus:** End-user perspective

**Scope:**

- Cognitive load
- Usability
- Clarity of flows
- Error handling from user perspective
- Mismatch between intent and experience

**May:**

- Identify confusing or misleading aspects
- Flag poor defaults or unclear behavior

**May NOT:**

- Redesign architecture
- Add features
- Override stated user goals

**Output:** Saves analysis to `review_user.md`

---

### Integrator / Arbiter

**Owns:** Final裁决

**May:**

- Accept or reject objections
- Require design revisions
- Declare the design complete

**May NOT:**

- Invent new ideas
- Add requirements
- Reopen locked decisions without cause

**Output:** Saves裁决 to `arbitration.md`

---

## Process (4 Phases)

### Phase 1 — Explore & Design

1. Main Agent explores the problem space and creates `plan.md`
2. Primary Designer produces initial design, saves to `design.md`
3. Understanding Lock is confirmed (no requirement changes after this point)
4. Decision Log initialized in `decision_log.md`

**Parallel opportunity:** If the problem requires research, spawn parallel research sub-agents (each saves findings to `research_{topic}.md` in the working directory).

---

### Phase 2 — Structured Review (Sequential)

Reviewers are invoked **one at a time**, in this order:

1. **Skeptic / Challenger** → `review_skeptic.md`
2. **Constraint Guardian** → `review_constraint.md`
3. **User Advocate** → `review_user.md`

For each reviewer:

- Read `design.md` and `decision_log.md`
- Produce explicit, scoped feedback
- Objections must reference specific assumptions or decisions
- No new features may be introduced

After each review:

- Main Agent reads the review file
- Primary Designer revises `design.md` if required
- Main Agent updates `decision_log.md` with objection and resolution

---

### Phase 3 — Arbitration

The Arbiter reviews:

- `design.md` (final revised version)
- `decision_log.md` (all objections and resolutions)
- All three review files

The Arbiter must explicitly decide:

- Which objections are **accepted** (design must be revised)
- Which objections are **rejected** (with rationale)
- Whether the design is **APPROVED**, requires **REVISE**, or is **REJECTED**

Saves裁决 to `arbitration.md`.

**If REVISE:** Return to Phase 2 with specific revision instructions. Primary Designer updates `design.md`, re-run affected reviews.

**If REJECTED:** Document rationale in `decision_log.md`, process ends.

---

### Phase 4 — Deliver

Only if Arbiter declares **APPROVED**:

1. Main Agent produces final `deliverable.md` incorporating all approved changes
2. Update `plan.md` with completion status
3. Report final disposition: **APPROVED** with summary

---

## Output Control Rules (from do-agent)

1. **Every agent must save its own output to a local file immediately.** Do not return full output to the main agent.
2. **Sub-agents return only a status summary** (e.g., "Review complete. 3 objections raised, 2 critical, 1 minor. Saved to review_skeptic.md").
3. **Main Agent context is scarce** — read files on demand, do not load all outputs into context at once.
4. **All Read + Write + Bash tools must be allowed** for all sub-agents.

---

## Decision Log Format

`decision_log.md` must use this structure:

```markdown
# Decision Log

## Decision 1: [Title]
- **Decision:** [What was decided]
- **Alternatives:** [What else was considered]
- **Objections:** [Who objected and why]
- **Resolution:** [Accepted/Rejected and rationale]
- **Status:** Resolved / Pending

## Decision 2: [Title]
...
```

---

## Exit Criteria (Hard Stop)

You may exit this skill **only when ALL are true**:

- [ ] Understanding Lock was completed
- [ ] All three reviewer agents have been invoked
- [ ] All objections are resolved or explicitly rejected in `decision_log.md`
- [ ] Arbiter has declared the design **APPROVED**
- [ ] `deliverable.md` has been produced
- [ ] `plan.md` shows all tasks completed

If any criterion is unmet:

- Continue the process
- Do NOT proceed to implementation

---

## Final Disposition Report

When the process completes, report:

```
DISPOSITION: [APPROVED | REVISE | REJECT]
RATIONALE: [One sentence summary]
ARTIFACTS: [List of files in working directory]
```

---

## Failure Modes This Skill Prevents

- Idea swarm chaos
- Hallucinated consensus
- Overconfident single-agent designs
- Hidden assumptions
- Premature implementation
- Endless debate
- Lost context (all decisions persisted to disk)

---

## When to Use

Use this skill when:

- You need to brainstorm AND want a full audit trail
- The design is complex enough to warrant multi-perspective review
- You want do-agent's output discipline applied to a brainstorming process
- The user asks to "/do-agent-brainstorm"
