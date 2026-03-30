# Skill: Agent Prompts and Role Definitions

Use this skill for:

- writing or editing agent instruction files (`.ai/agents/*.md`)
- creating or updating skill files (`SKILL.md`)
- updating template files (`.ai/templates/*.md`)
- designing new agent roles (e.g., epic_analyst, epic_designer)
- adjusting how roles interpret inputs and produce outputs

---

## Goals

- Each agent role must be unambiguous about what it reads, what it writes, and how it decides
- Skills are additive context injected into role prompts — they must be self-contained
- Templates define the expected shape of output documents

---

## Agent File Structure

Each `agents/<role>.md` file must include:

1. **Role identity** — who is the agent and what is its purpose
2. **Input** — exact file paths the agent reads
3. **Output** — exact file paths the agent writes
4. **What to produce** — structured breakdown of expected output content
5. **Rules** — explicit constraints on behavior (what NOT to do)
6. **Success criteria** — how the agent knows it did the job correctly

---

## Skill File Structure

Each `SKILL.md` file must include:

1. **Use this skill for** — specific scenarios where this skill applies
2. **Goals** — what good behavior looks like in this domain
3. **Rules or checklist** — concrete implementation or review guidance
4. **Avoid** — anti-patterns explicitly prohibited

Skills must be:
- self-contained (no references to other skills by name)
- domain-specific (not generic advice)
- actionable (not aspirational)

---

## Template File Structure

Templates define the expected output shape for architect documents:

- `task_spec.md` — requirement summary, technical scope, out of scope, impacted modules
- `design_note.md` — proposed approach, main flow, data/API considerations, risks/trade-offs
- `acceptance_criteria.md` — functional criteria, validation cases, failure cases
- `assumptions.md` — known unknowns, inferred constraints, clarifications needed

Templates should use clear section headers and placeholder text to guide the agent.

---

## Writing Rules

1. Use imperative, direct language — tell the agent what to do, not what to consider
2. Use explicit file paths — do not say "the spec file", say `.ai/runs/<TICKET>/architect/task_spec.md`
3. Output sections must match what `ai_run.py` verifies in complete steps
4. Do not add steps that `ai_run.py` doesn't support unless the runner is being extended too
5. Keep role files focused — do not mix concerns across roles in one file
6. Each skill file should be usable independently without assuming other skills are loaded

---

## Role Behavioral Constraints

| Role       | Writes code? | Writes JSON? | Writes markdown? |
|------------|-------------|--------------|------------------|
| Architect  | No          | No           | Yes              |
| Developer  | Yes         | No           | Yes (report)     |
| Reviewer   | No          | Yes          | No               |
| QA         | No          | Yes          | No               |

Enforce these boundaries in role files — agents must not cross them.

---

## Avoid

- vague instructions like "do your best" or "consider the context"
- role files that describe what the agent might see instead of what it must do
- skills that restate general software engineering best practices with no project specificity
- templates with no structure guidance (blank files are not templates)
