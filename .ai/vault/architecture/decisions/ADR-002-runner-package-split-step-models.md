---
id: ADR-002
status: proposed
epic: ""
tickets: [refactor-ai-run-config-split]
supersedes: ""
---

## Context

`ai_run.py` had grown into one large file with per-step model/effort hardcoded in Python.

## Decision

Split the runner into the `.ai/bin/ai_runner/` package behind a stable `ai_run.py` re-export facade (acyclic imports, logic-free `ai_run.py`). Move per-step model/effort to project-owned `.ai/step_models.json` read via `get_step_model`: strict validation (`StepConfigError`), soft fallback (warn + sonnet/high) when the file is missing, `preflight_step_models` before state mutation.

## Alternatives

- Keep single file: rejected — unmaintainable size.
- Hardcode models in Python: rejected — not project-tunable.

## Consequences

Old names/patch targets keep working via the facade; patches must target the defining module. `step_models.json` keys must track `KNOWN_PREPARE_STEPS`.
