# AI Dev Team Operating Guide

This repository uses a structured AI workflow managed by `.ai/bin/ai_run.py`.

You (Claude) are invoked at specific stages of a ticket workflow. Each stage generates a prompt file that you read and act on, then write output files directly to the repository.

---

# 🗂️ Directory Structure

```
.ai/
  bin/
    ai_run.py              # Workflow runner
  agents/
    architect.md           # Role instructions for Architect
    developer.md           # Role instructions for Developer
    reviewer.md            # Role instructions for Reviewer
    qa.md                  # Role instructions for QA
  templates/               # Optional shared templates
  project_config.json      # Project name, domain config, base branch, skills
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

---

# 🖥️ WezTerm Auto-Spawn

When `--run-auto` is passed to `next`, the runner automatically:

1. Runs the prepare step (generates the prompt file)
2. Spawns a new WezTerm pane via `wezterm cli spawn` with `claude --dangerously-skip-permissions`
3. Waits ~4 seconds for Claude to load
4. Sends the full prompt text into the pane via `wezterm cli send-text`

You then press Enter in the new Claude session to submit the prompt.

This only triggers for prepare steps: `architect-prepare`, `dev-prepare`, `dev-fix-prepare`, `review-prepare`, `qa-prepare`. Complete steps (`*-complete`) run unattended and do not open a new pane.

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
