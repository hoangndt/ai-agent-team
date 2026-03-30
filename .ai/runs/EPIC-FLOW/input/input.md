Implement Epic-level workflow support in the AI agent system.

The current system supports ticket-level workflow (architect → dev → review → qa). Extend it to support epic-level planning workflow, with the goal of generating structured user stories/tickets as markdown files for external tools (e.g., Jira, Shortcut).

---

# Objective

Add a new Epic workflow that allows:

- Input of a high-level requirement
- Analysis and design at system level
- Review of design
- Breakdown into multiple user stories/tickets
- Output as markdown files (one file per ticket)

Epic flow must NOT execute code or reuse ticket execution pipeline directly. It is a planning pipeline only.

---

# Scope

## 1. New CLI commands

Add a parallel command set for epic:

- epic-init <EPIC> "<requirement>"
- epic-analysis-prepare / epic-analysis-complete
- epic-design-prepare / epic-design-complete
- epic-review-prepare / epic-review-complete
- epic-design-fix-prepare / epic-design-fix-complete
- epic-breakdown-prepare / epic-breakdown-complete
- epic-status
- epic-next (--run / --run-auto)

Behavior should mirror ticket flow (prepare → act → complete → next).

---

## 2. Directory structure

Create a new root:

.ai/epics/<EPIC>/

Structure:

.ai/epics/<EPIC>/
status.json

input/
epic_input.md

analysis/
epic_analysis_prompt.md
epic_analysis.md

design/
epic_design_prompt.md
epic_design.md

review/
epic_review_prompt.md
epic_review.json

fix/
epic_design_fix_prompt.md
epic_review_fix_context.md
previous_epic_review.json

breakdown/
epic_breakdown_prompt.md
epic_story_map.md
tickets/
<multiple markdown files>

Each stage must read/write ONLY within its own folder.

---

## 3. Epic flow logic

Flow:

analysis → design → review

If review = approve:
→ breakdown → done

If review = request_changes or block:
→ design-fix → review again

No dev/review/qa loop like ticket flow.

---

## 4. Output artifacts

### epic_analysis.md

- problem statement
- business goal
- scope / out of scope
- dependencies
- risks
- assumptions

### epic_design.md

- solution approach
- architecture / modules impacted
- data/API changes
- rollout / migration strategy
- sequencing

### epic_review.json

{
"decision": "approve|request_changes|block",
"issues": [
{
"severity": "high|medium|low",
"area": "scope|architecture|dependency|sequencing|risk|rollout",
"message": "..."
}
],
"summary": "..."
}

### epic_story_map.md

- workstreams
- grouped tickets
- dependencies
- suggested order

### breakdown/tickets/\*.md

Each file = one user story/ticket

---

## 5. Ticket markdown format

Each generated file must follow:

# <ID> - <Title>

## Summary

...

## Goal

...

## Scope

...

## Out of Scope

...

## Acceptance Criteria

- ...
- ...

## Dependencies

- ...

## Suggested Order

<number>

## Domain

backend|frontend|...

## Notes

...

---

## 6. Naming convention

Ticket files:

breakdown/tickets/
US-001-<slug>.md
US-002-<slug>.md

Optional prefixes:

- US-
- TASK-
- SPIKE-

---

## 7. Agent roles (new)

Add new agent prompts:

.ai/agents/
epic_analyst.md
epic_designer.md
epic_reviewer.md
epic_planner.md

Roles:

- epic_analyst → analysis
- epic_designer → design
- epic_reviewer → review design
- epic_planner → breakdown into tickets

Reuse existing skills via project_config.json.

---

## 8. Prompt behavior

All epic prompts must:

- Read files from epic folder only
- Write output files directly (no chat-only output)
- Be structured and deterministic
- Avoid implementation-level detail (no code)

Breakdown step must:

- Generate multiple ticket markdown files
- Ensure tickets are:
  - small enough to execute
  - non-overlapping
  - dependency-aware

---

## 9. next() behavior

Implement epic-next similar to ticket-next:

- Determine next stage based on:
  - missing files
  - current_stage
  - review decision

Support:

- --run
- --run-auto (reuse WezTerm logic)

---

## 10. Non-goals

Do NOT implement:

- automatic creation of ticket runs from epic
- JSON ticket export
- Jira/Shortcut API integration

---

# Acceptance Criteria

- Can run full epic flow from init → breakdown using epic-next
- Each stage produces correct files in correct folders
- Review loop works (design → review → fix → review)
- Breakdown produces:
  - epic_story_map.md
  - multiple ticket markdown files
- Output ticket files are readable and usable directly in Jira/Shortcut
- No impact to existing ticket workflow

---

# Notes

- Follow the same coding patterns as current ai_run.py
- Reuse helper functions where possible
- Keep epic logic isolated from ticket logic
- Ensure paths are clean and readable
