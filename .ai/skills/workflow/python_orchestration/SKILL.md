# Skill: Python Orchestration (ai_run.py)

Use this skill for:

- modifying or extending the workflow runner (`ai_run.py`)
- adding new stages, commands, or prepare/complete cycles
- changing how prompts are generated and injected with skills/context
- modifying WezTerm integration or terminal spawning logic
- changing status tracking (`status.json`) behavior
- updating how domains, paths, and skill files are loaded from `project_config.json`

---

## Goals

- Keep the runner script simple and predictable
- Each stage must follow the prepare → act → complete pattern
- Status transitions must be explicit and auditable via `status.json`
- Prompt generation must be deterministic and file-driven

---

## Architecture

The workflow is structured as:

- **Commands** — CLI subcommands mapped to functions (e.g., `init`, `architect-prepare`, `dev-complete`)
- **Prepare functions** — generate prompt files; optionally spawn WezTerm pane
- **Complete functions** — verify required output files are non-empty; advance status
- **Status tracker** — `status.json` records current stage, completed stages, and artifact paths
- **Skill loader** — reads `project_config.json` to inject domain-specific skill files into prompts
- **Context builder** — assembles git diff, file tree, and relevant paths for each role

---

## Implementation Rules

1. Each new stage needs a paired `<stage>-prepare` and `<stage>-complete` command
2. Prepare functions must write a prompt file to `runs/<TICKET>/<stage>/`
3. Complete functions must verify required output files exist and are non-empty
4. WezTerm spawning only triggers on prepare steps, never complete steps
5. `status.json` must be updated atomically at each transition
6. Skill files are injected verbatim — do not summarize or transform them
7. Prompt templates must include: role context, skill sections, input files, and output paths
8. Keep `ai_run.py` as a single-file script — do not split into packages unless clearly necessary

---

## Prompt Construction Checklist

When building a new agent prompt, include:

- role description (from `agents/<role>.md`)
- project context (name, domain, relevant paths)
- loaded skill file contents
- input file references (what to read)
- output file targets (what to write)
- acceptance criteria or spec (where relevant)
- git diff or file context (for developer/reviewer stages)

---

## Status Tracking

`status.json` shape:

```json
{
  "ticket": "TICKET-ID",
  "stage": "current-stage",
  "completed": ["stage1", "stage2"],
  "artifacts": {
    "task_spec": ".ai/runs/TICKET/architect/task_spec.md"
  }
}
```

Transitions must only move forward, never backward, unless explicitly implementing a fix loop.

---

## Avoid

- generating prompts that include file content not relevant to the current domain
- spawning WezTerm on complete steps
- silently skipping file verification on complete steps
- hardcoding domain logic into the runner — keep it config-driven
- adding complex Python dependencies; prefer stdlib where possible
