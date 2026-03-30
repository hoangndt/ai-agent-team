# Skill: Workflow Reviewer

Use this skill for:

- reviewing changes to `ai_run.py` (the workflow orchestration script)
- reviewing new or modified agent role files (`.ai/agents/*.md`)
- reviewing new or modified skill files (`SKILL.md`)
- reviewing `project_config.json` changes
- reviewing template file changes
- validating that workflow stages and outputs remain consistent

---

## Review Priorities

Review in this order:

1. correctness — does the change work as intended?
2. workflow integrity — are stage contracts (prepare/complete pairs) intact?
3. acceptance criteria fit — does the change address the ticket's stated goal?
4. config consistency — do `project_config.json` skill paths resolve to real files?
5. agent coherence — are role files unambiguous and correctly scoped?
6. maintainability — is the change minimal and localized?

---

## Review Checklist

### Python orchestration (`ai_run.py`)

- are new stages paired (prepare + complete)?
- does the complete step verify expected output files?
- does prompt generation include all required sections (role, skills, input, output)?
- does WezTerm spawn only on prepare steps?
- does `status.json` update correctly at each transition?
- are skill files loaded from `project_config.json`, not hardcoded?

### Agent prompt files (`.ai/agents/*.md`)

- does the file clearly state what the agent reads and writes?
- are file paths explicit (no ambiguous references)?
- does the output section match what `ai_run.py` verifies?
- are constraints clear about what the agent must NOT do?

### Skill files (`SKILL.md`)

- is the skill self-contained (no external dependencies)?
- is it domain-specific and actionable, not generic?
- does it include an explicit "Avoid" section?
- is it scoped to specific scenarios (not catch-all advice)?

### `project_config.json`

- do all skill paths resolve to real `SKILL.md` files?
- are domain paths correct and meaningful?
- is the base branch correct?
- is the default domain appropriate?

### Template files

- do section headers match what agent prompts expect agents to produce?
- is placeholder text clear enough to guide output format?

---

## Decision Guidance

- approve:
  - no meaningful issues; workflow integrity is maintained
- request_changes:
  - fixable issues: missing complete step, broken skill path, vague agent instructions
- block:
  - stage contract broken (prepare with no complete, or vice versa)
  - skill paths reference non-existent files
  - status.json transitions would leave workflow in invalid state
  - agent files contradict each other in ways that break the handoff chain

---

## Issue Writing Guidance

Each issue must be:

- tied to a specific file and line or section
- actionable (explain what to fix)
- concrete (not "this could be clearer")

Prefer:
- "`.ai/project_config.json` references `.ai/skills/workflow/nonexistent/SKILL.md` which does not exist"

Over:
- "skill paths should be checked"
