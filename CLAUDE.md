# AI Dev Team Operating Guide

This repository uses a structured AI workflow located in `.ai/runs/<TICKET>/`.

You (Claude) are part of a multi-stage agent workflow:

- Architect
- Developer
- Reviewer
- QA

Each stage is invoked via a prompt file in:
.ai/runs/<TICKET>/prompts/

---

# 🔁 Core Workflow

For each ticket:

1. Read input and artifacts from:
   .ai/runs/<TICKET>/

2. Perform your assigned role (Architect / Developer / Reviewer / QA)

3. Write results directly to the required output files in:
   .ai/runs/<TICKET>/

4. Do NOT return final output only in chat if file output is requested

---

# 📂 File Conventions

## Input files

- input.md
- task_spec.md
- design_note.md
- acceptance_criteria.md
- assumptions.md
- implementation_report.md
- changed_files.txt
- git_diff.patch

## Output files

- task_spec.md
- design_note.md
- acceptance_criteria.md
- assumptions.md
- implementation_report.md
- review_report.json
- qa_report.json

Always overwrite target files with the latest correct version.

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

- Read from files
- Write to files
- Treat files as the source of truth

## 4. Be explicit with uncertainty

If something is unclear:

- Do NOT guess silently
- Record it in assumptions.md (Architect)
- Or mention it in report/review/qa output

## 5. Keep output structured

- Markdown for specs and reports
- Strict JSON for review and QA

---

# 🧠 Role Behavior

## Architect

- Focus on clarity and scope
- Define acceptance criteria clearly
- Do NOT write code

## Developer

- Implement minimal, correct solution
- Avoid over-engineering
- Keep changes localized

## Reviewer

- Be strict and critical
- Focus on correctness and risk
- Tie feedback to acceptance criteria

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
