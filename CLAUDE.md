# AI Dev Team Operating Guide

This repository uses a structured AI workflow managed by `.ai/bin/ai_run.py`.

You (Claude) are invoked at specific stages of a ticket workflow. Each stage generates a prompt file that you read and act on, then write output files directly to the repository.

---

## Architecture

@.ai/vault/architecture/system-overview.md

---

# 🗂️ Directory Structure

```
.ai/
  bin/
    ai_run.py              # Workflow runner entry point + re-export facade
    ai_runner/             # Runner implementation modules (paths, state, prompts, stages, routing, wezterm, cli)
    ai_wrap.py             # Read-only routing sidecar for the Claude wrapper
  agents/
    architect.md           # Role instructions for Architect
    developer.md           # Role instructions for Developer
    reviewer.md            # Role instructions for Reviewer
    qa.md                  # Role instructions for QA
    epic_analyst.md        # Role instructions for Epic Analyst
    epic_designer.md       # Role instructions for Epic Designer
    epic_reviewer.md       # Role instructions for Epic Reviewer (design)
    epic_analysis_reviewer.md   # Role instructions for Epic Analysis Reviewer
    epic_breakdown_reviewer.md  # Role instructions for Epic Breakdown Reviewer
    epic_planner.md        # Role instructions for Epic Planner (breakdown)
  templates/               # Optional shared templates
  project_config.json      # Project name, domain config, base branch, skills
  step_models.json         # Per-step Claude model + effort (project-owned)
  runs/
    <TICKET>/
      status.json          # Stage tracker (auto-managed)
      input/
        input.md           # Initial requirement
      architect/
        architect_prompt.md
        task_spec.md
        design_note.md
        acceptance_criteria.md
        assumptions.md
      dev/
        dev_prompt.md
        implementation_report.md
      fix/
        dev_fix_prompt.md
        review_fix_context.md  # Auto-generated from review_report.json
        qa_fix_context.md      # Auto-generated from qa_report.json
        previous_review_report.json
        previous_qa_report.json
      review/
        review_prompt.md
        review_report.json
      qa/
        qa_prompt.md
        qa_report.json
  epics/
    <EPIC>/
      status.json          # Stage tracker (auto-managed)
      input/
        epic_input.md      # Written by epic-init
      analysis/
        epic_analysis_prompt.md
        epic_analysis.md
      design/
        epic_design_prompt.md
        epic_design.md
      review/
        epic_review_prompt.md
        epic_review.json
        epic_analysis_review_prompt.md
        epic_analysis_review.json
        epic_breakdown_review_prompt.md
        epic_breakdown_review.json
      fix/
        epic_design_fix_prompt.md
        epic_review_fix_context.md  # Built from epic_review.json
        previous_epic_review.json   # Archived before fix round
        epic_analysis_fix_prompt.md
        epic_analysis_review_fix_context.md
        previous_epic_analysis_review.json
        epic_breakdown_fix_prompt.md
        epic_breakdown_review_fix_context.md
        previous_epic_breakdown_review.json
      breakdown/
        epic_breakdown_prompt.md
        epic_story_map.md
        epic_story_status.md
        tickets/
          EPIC-001-US-001-<slug>.md
          EPIC-001-US-002-<slug>.md
          ...
```

---

# 🔁 Core Workflow

Each stage follows a **prepare → act → complete** pattern:

1. **prepare** — `ai_run.py` generates a prompt file
2. **act** — You (Claude) read the prompt file and write output files directly to the repo
3. **complete** — `ai_run.py` verifies that required output files are non-empty

Use `python .ai/bin/ai_run.py next <TICKET> --run` to auto-advance through stages.

Use `python .ai/bin/ai_run.py next <TICKET> --run-auto` to auto-advance **and** automatically open Claude in a new WezTerm tab with the generated prompt pre-loaded. After the prepare step runs, the script spawns a new WezTerm pane, launches `claude --dangerously-skip-permissions`, waits for it to load, then sends the prompt text into the pane. You still need to press Enter in the new Claude session to submit.

## Stages in order

| Step               | CLI command                     | Your job                                                       |
| ------------------ | ------------------------------- | -------------------------------------------------------------- |
| Init               | `init <TICKET> "<requirement>"` | (automated)                                                    |
| Architect Prepare  | `architect-prepare <TICKET>`    | (generates prompt)                                             |
| **Architect**      | _(paste prompt)_                | Write task_spec, design_note, acceptance_criteria, assumptions |
| Architect Complete | `architect-complete <TICKET>`   | (verifies files)                                               |
| Dev Prepare        | `dev-prepare <TICKET>`          | (generates prompt)                                             |
| **Developer**      | _(paste prompt)_                | Implement code, write implementation_report.md                 |
| Dev Complete       | `dev-complete <TICKET>`         | (verifies files)                                               |
| Review Prepare     | `review-prepare <TICKET>`       | (generates prompt)                                             |
| **Reviewer**       | _(paste prompt)_                | Write review_report.json                                       |
| Review Complete    | `review-complete <TICKET>`      | (verifies + builds fix context)                                |
| QA Prepare         | `qa-prepare <TICKET>`           | (generates prompt)                                             |
| **QA**             | _(paste prompt)_                | Write qa_report.json                                           |
| QA Complete        | `qa-complete <TICKET>`          | (verifies + builds qa fix context)                             |
| Distill Prepare    | `distill-prepare <TICKET>`      | (auto-triggered on QA pass; generates prompt)                  |
| **Distiller**      | _(paste prompt)_                | Refresh system-overview.md + modules/&lt;domain&gt;.md          |
| Distill Complete   | `distill-complete <TICKET>`     | (verifies vault line caps; bounded retry, see Fix Loop)         |

---

# 💬 Claude Slash Commands (optional wrapper)

`.claude/commands/` + `.claude/agents/workflow-step*.md` let one Claude session drive the same workflow: `/create-ticket`, `/start-ticket`, `/ticket-status`, `/create-epic`, `/start-epic`, `/epic-status`. Each stage runs in a fresh sub-agent that reads the same generated prompt file; `ai_run.py` still owns state. `.ai/bin/ai_wrap.py` is a read-only helper (`next|epic-next <ID> --json`, `validate-id`). The orchestrator never edits files under `.ai/runs/` or `.ai/epics/` and never commits. The WezTerm flow above is unchanged.

---

# 🖥️ WezTerm Auto-Spawn

When `--run-auto` is passed to `next`, the runner automatically:

1. Runs the prepare step (generates the prompt file)
2. Spawns a new WezTerm pane via `wezterm cli spawn` with `claude --dangerously-skip-permissions`
3. Waits ~4 seconds for Claude to load
4. Sends the full prompt text into the pane via `wezterm cli send-text`

You then press Enter in the new Claude session to submit the prompt.

This only triggers for prepare steps: `architect-prepare`, `dev-prepare`, `dev-fix-prepare`, `review-prepare`, `qa-prepare` and their epic equivalents: `epic-analysis-prepare`, `epic-analysis-review-prepare`, `epic-analysis-fix-prepare`, `epic-design-prepare`, `epic-design-fix-prepare`, `epic-review-prepare`, `epic-breakdown-prepare`, `epic-breakdown-review-prepare`, `epic-breakdown-fix-prepare`. Complete steps (`*-complete`) run unattended and do not open a new pane.

**Requirements:** WezTerm must be installed and `wezterm` must be in `$PATH`. If the spawn fails, the runner prints a warning and exits gracefully — no prompt is sent.

---

# 🔄 Fix Loop

If the Reviewer returns `request_changes` or `block`, or QA returns `fail`, the workflow enters a fix cycle:

| Step                     | CLI command                 | Your job                                                                   |
| ------------------------ | --------------------------- | -------------------------------------------------------------------------- |
| Dev Fix Prepare          | `dev-fix-prepare <TICKET>`  | (generates fix prompt with review/qa context)                              |
| **Developer**            | _(paste prompt)_            | Fix issues, **append** a new fix-round section to implementation_report.md |
| Dev Fix Complete         | `dev-fix-complete <TICKET>` | (verifies report)                                                          |
| → back to Review Prepare |                             |                                                                            |

Previous reports are archived to `fix/previous_review_report.json` and `fix/previous_qa_report.json`. Follow-up reviews check whether prior issues were resolved.

The workflow is **done** when review decision is `approve` and QA decision is `pass`.

---

# 🏔️ Epic Workflow

An **epic** is a higher-level planning pipeline that produces an analysis, a design, reviews of each, and a breakdown into feature-slice user stories/tickets. It lives under `.ai/epics/<EPIC>/` and contains **no code execution** — it is planning only.

Use `python .ai/bin/ai_run.py epic-next <EPIC> --run` to auto-advance through stages.
Use `python .ai/bin/ai_run.py epic-next <EPIC> --run-auto` to also spawn a WezTerm pane.

## Epic stages in order

| Step                     | CLI command                          | Your job                                                              |
| ------------------------ | ------------------------------------ | --------------------------------------------------------------------- |
| Epic Init                | `epic-init <EPIC> "<requirement>"`   | (automated)                                                           |
| Analysis Prepare         | `epic-analysis-prepare <EPIC>`       | (generates prompt)                                                    |
| **Epic Analyst**         | _(paste prompt)_                     | Write `epic_analysis.md`                                              |
| Analysis Complete        | `epic-analysis-complete <EPIC>`      | (verifies file)                                                       |
| Analysis Review Prepare  | `epic-analysis-review-prepare <EPIC>`| (generates prompt)                                                    |
| **Epic Analysis Reviewer** | _(paste prompt)_                   | Write `epic_analysis_review.json`                                     |
| Analysis Review Complete | `epic-analysis-review-complete <EPIC>` | (verifies + builds fix context)                                     |
| Design Prepare           | `epic-design-prepare <EPIC>`         | (generates prompt)                                                    |
| **Epic Designer**        | _(paste prompt)_                     | Write `epic_design.md`                                                |
| Design Complete          | `epic-design-complete <EPIC>`        | (verifies file)                                                       |
| Review Prepare           | `epic-review-prepare <EPIC>`         | (generates prompt; design review)                                     |
| **Epic Reviewer**        | _(paste prompt)_                     | Write `epic_review.json`                                              |
| Review Complete          | `epic-review-complete <EPIC>`        | (verifies + builds fix context)                                       |
| Breakdown Prepare        | `epic-breakdown-prepare <EPIC>`      | (generates prompt, only after approved review)                        |
| **Epic Planner**         | _(paste prompt)_                     | Write `epic_story_map.md` + individual ticket files in `tickets/`     |
| Breakdown Complete       | `epic-breakdown-complete <EPIC>`     | (verifies story map, status tracker, ticket shape and tracker ids)    |
| Breakdown Review Prepare | `epic-breakdown-review-prepare <EPIC>` | (generates prompt)                                                  |
| **Epic Breakdown Reviewer** | _(paste prompt)_                  | Write `epic_breakdown_review.json`                                    |
| Breakdown Review Complete | `epic-breakdown-review-complete <EPIC>` | (verifies + builds fix context)                                   |

## Epic fix loop

If the Epic Reviewer returns `request_changes` or `block`, the workflow enters a design fix cycle (the analysis and breakdown reviews have the same shape, see below):

| Step                     | CLI command                          | Your job                                                              |
| ------------------------ | ------------------------------------ | --------------------------------------------------------------------- |
| Design Fix Prepare       | `epic-design-fix-prepare <EPIC>`     | (generates fix prompt with review context)                            |
| **Epic Designer**        | _(paste prompt)_                     | Fix issues in `epic_design.md`, update fix notes                      |
| Design Fix Complete      | `epic-design-fix-complete <EPIC>`    | (verifies design)                                                     |
| → back to Review Prepare |                                      |                                                                       |

The previous `epic_review.json` is archived to `fix/previous_epic_review.json` before each fix round.

The analysis and breakdown gates use the same loop with their own steps and files:

| Gate      | Fix steps (`-prepare` / `-complete`)                              | Fixer            | Review file                | Archived to                                  |
| --------- | ----------------------------------------------------------------- | ---------------- | -------------------------- | -------------------------------------------- |
| Analysis  | `epic-analysis-fix-prepare` / `epic-analysis-fix-complete`        | Epic Analyst     | `epic_analysis_review.json`  | `fix/previous_epic_analysis_review.json`     |
| Breakdown | `epic-breakdown-fix-prepare` / `epic-breakdown-fix-complete`      | Epic Planner     | `epic_breakdown_review.json` | `fix/previous_epic_breakdown_review.json`    |

Pipeline order: analysis -> analysis review (fix loop) -> design -> design review (fix loop) -> ADR distill -> breakdown -> breakdown review (fix loop) -> `epic-generate-tickets`. A fresh review file written by the reviewer is always routed to its `*-review-complete` before any decision is acted on. The epic workflow is **done** when the breakdown review decision is `approve`. `epic-generate-tickets` refuses (exit 1) while a breakdown review/fix exists and the current review is not `approve`; with no breakdown review recorded it only warns. If ticket runs were already seeded, `epic-breakdown-review-prepare` and `epic-breakdown-fix-prepare` warn, seeded runs are never overwritten, and `epic-generate-tickets` reports `[STALE]` for a ticket file that changed after seeding.

## Epic agent file responsibilities

### Epic Analyst writes
- `analysis/epic_analysis.md` — scope, goals, stakeholders, constraints, open questions

### Epic Designer writes
- `design/epic_design.md` — system design, component breakdown, data/API flows, trade-offs
  - On fix rounds: overwrite with corrected version

### Epic Reviewer writes
- `review/epic_review.json` (design review), `review/epic_analysis_review.json` (Epic Analysis Reviewer) and `review/epic_breakdown_review.json` (Epic Breakdown Reviewer) — strict JSON:
  ```json
  {
    "decision": "approve|request_changes|block",
    "issues": [
      { "severity": "high|medium|low", "area": "...", "message": "..." }
    ],
    "summary": "..."
  }
  ```

### Epic Planner writes
- `breakdown/epic_story_map.md` — ordered list of user stories with descriptions
- `breakdown/epic_story_status.md` — story status tracker; every ticket file has exactly one row and vice versa
- `breakdown/tickets/<EPIC-NNN-US-NNN-slug>.md` — one file per feature-slice ticket (at least one required)
  - A ticket is one independently verifiable feature/outcome spanning every domain it needs; never split by domain or layer
  - Required sections include `## Domains` (primary first), `## Domain Checklist` (a `### <domain>` subsection with `- [ ]` items per domain, required when more than one domain), and `## Verification` (manager-runnable steps on dev/stage)
  - Multi-domain ticket runs are seeded with `domain` (primary) and `domains` (all); prompts carry every listed domain's paths, skills and vault modules. Distill refreshes only the primary domain's module doc.
  - On fix rounds (breakdown fixer): revise story map, tracker and tickets in place

---

# 📂 File Responsibilities

## Architect writes

- `architect/task_spec.md` — technical restatement of requirement, scope, impacted modules
- `architect/design_note.md` — implementation approach, data/API flow, trade-offs
- `architect/acceptance_criteria.md` — testable success, validation, and failure cases
- `architect/assumptions.md` — explicit unknowns and ambiguities

## Developer writes

- Code changes directly in the repo
- `dev/implementation_report.md` — summary, files modified, decisions, tests run
  - On initial dev: write the full report
  - On each fix round: **append** a new `## Fix Round N` section; never erase previous rounds

## Reviewer writes

- `review/review_report.json` — strict JSON:
  ```json
  {
    "decision": "approve|request_changes|block",
    "issues": [
      { "severity": "high|medium|low", "file": "...", "message": "..." }
    ],
    "summary": "..."
  }
  ```

## QA writes

- `qa/qa_report.json` — strict JSON:
  ```json
  {
    "decision": "pass|fail",
    "missing_tests": [],
    "risks": [],
    "summary": "..."
  }
  ```

Always overwrite target files with the latest correct version.

---

# ⚙️ Configuration

`.ai/project_config.json` controls:

- `project_name` — used in prompts
- `git.base_branch` — branch to diff against (default: `main`)
- `default_domain` — fallback domain if not specified at init
- `domains.<name>.paths` — relevant paths shown in project context
- `domains.<name>.skills.<role>` — list of skill file paths loaded into role prompts

---

# ⚠️ Critical Rules

## 1. Do not break scope

- Only work within the current ticket
- Do not refactor unrelated modules
- Do not introduce large design changes unless explicitly required

## 2. Prefer existing patterns

- Follow current project architecture
- Reuse existing services, repositories, utilities
- Do not introduce new frameworks or patterns unless necessary

## 3. Be file-driven, not chat-driven

- Read from the prompt file
- Write output directly to the specified files
- Do NOT return final output only in chat when file output is requested

## 4. Be explicit with uncertainty

- Do NOT guess silently
- Record unknowns in `assumptions.md` (Architect)
- Or note them in the report/review/qa output

## 5. Keep output structured

- Markdown for specs and reports
- Strict JSON for `review_report.json` and `qa_report.json`

---

# 🧠 Role Behavior

## Architect

- Focus on clarity and scope
- Define acceptance criteria clearly
- Do NOT write code

## Developer

- Implement minimal, correct solution
- Avoid over-engineering
- Keep changes localized to the ticket

## Reviewer

- Be strict and critical
- Focus on correctness, risk, and acceptance criteria
- In follow-up reviews: verify prior issues are resolved, do not repeat fixed ones

## QA

- Focus on missing cases and risks
- Think in terms of failure scenarios
- Validate completeness, not style

---

# 🚫 What NOT to do

- Do not dump large explanations unrelated to the task
- Do not modify files outside the ticket scope without reason
- Do not invent requirements
- Do not skip writing required output files

---

# ✅ Success Criteria

You are successful when:

- Required files are created or updated correctly
- Outputs follow the expected format
- Changes are minimal, correct, and aligned with the repository
- The next agent in the workflow can proceed without confusion
