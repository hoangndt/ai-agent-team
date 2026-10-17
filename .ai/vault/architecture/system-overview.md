# System Overview

Fixed headings below (Components, Data Flows, Invariants / Constraints, ADR Index) are a contract read by later tooling (distill, cap checks). Do not rename or reorder them.

## Components

| Component | Responsibility | Entry point | Module doc |
|---|---|---|---|
| Workflow Runner | CLI that drives the ticket and epic prepare/act/complete pipeline, owns `status.json` transitions, prompt assembly, and routing. `ai_run.py` is entry point + re-export facade over the `ai_runner/` package (constants, paths, state, context, prompts, architect/dev_qa/distill/arch/epic stages, steps, routing, wezterm, autoflow, cli) | `.ai/bin/ai_run.py`, `.ai/bin/ai_runner/` | modules/workflow.md |
| Agent Role Files | Per-role instructions (architect, developer, reviewer, qa, epic_*, arch_init) injected verbatim into generated prompts | `.ai/agents/*.md` | modules/workflow.md |
| Domain Config | `project_config.json` — project name, base branch, per-domain paths, and per-role skill file lists | `.ai/project_config.json` | modules/workflow.md |
| Domain Skills | Skill files injected into role prompts, keyed by domain + role | `.ai/skills/<domain>/<skill>/SKILL.md` | modules/workflow.md |
| Architecture Vault | Living architecture docs (system overview, per-domain modules, ADRs) injected into architect/developer/epic prompts as context | `.ai/vault/` | modules/workflow.md |
| Run State | Per-ticket and per-epic working directories holding prompts, reports, and JSON review/QA outputs | `.ai/runs/<TICKET>/`, `.ai/epics/<EPIC>/` | modules/workflow.md |
| Claude Wrapper | Optional Claude Code orchestration layer: slash commands drive a ticket/epic loop, one fresh sub-agent per stage with a Report gate (QUESTIONS/ASSUMPTIONS/BLOCKERS final-report contract); `install.py` ships it via explicit `CLAUDE_MANAGED_FILES` | `.claude/commands/*.md`, `.claude/agents/workflow-step*.md` | modules/workflow.md |
| Workflow Sidecar | Read-only routing helper: emits next-step JSON (step, kind, prompt path, model/effort, status echo) via `ai_run.next_action`/`epic_next_action`; `validate-id` | `.ai/bin/ai_wrap.py` | modules/workflow.md |
| Step Model Config | Project-owned `step_models.json` mapping each `*-prepare` step to model + effort; scaffolded by `install.py` from `.ai/templates/step_models.template.json`; read via `get_step_model` by WezTerm Bridge and `ai_wrap.py` | `.ai/step_models.json`, `ai_runner/steps.py` | modules/workflow.md |
| WezTerm Bridge | Spawns a WezTerm pane and launches an AI engine (Claude/Codex) to auto-paste generated prompts and poll for a completion sentinel | `spawn_ai_wezterm`, `wait_for_sentinel` in `.ai/bin/ai_runner/wezterm.py` | modules/workflow.md |

## Data Flows

1. Ticket workflow: `init` → Architect (design artifacts) → Architect Reviewer (approve/request_changes/block) → \[fix loop\] → Developer (code + implementation report, commits) → Reviewer (review_report.json) → QA (qa_report.json) → Distill (refreshes system-overview.md/module doc) → done. Each stage is `prepare` (Python writes a prompt file) → `act` (agent writes output files) → `complete` (Python verifies non-empty outputs and advances `status.json`).
2. Epic workflow: `epic-init` → Epic Analyst (epic_analysis.md) → Epic Designer (epic_design.md) → Epic Reviewer (epic_review.json, approve/request_changes/block) → \[design fix loop\] → Epic Planner (story map + per-story ticket files) → `epic-generate-tickets` seeds each ticket into the ticket workflow above.
3. arch-init workflow (project-level, ticket-less, sentinel id `_arch-init`): `arch-init-prepare` → Arch-Init agent (Phase 1: bootstrap `project_config.json` domains if missing; Phase 2: sweep code + migrate CLAUDE.md architecture prose into this vault, rewire root `CLAUDE.md` to `@`-import `system-overview.md`) → `arch-init-complete` verifies outputs.
4. Prompt assembly: `build_role_prompt` / `build_epic_role_prompt` compose Role Instruction + Project Context + Architecture (Vault) context + Domain Skills + (optional) Figma context + Task Instruction into a single prompt file written to the run directory.
5. Claude-wrapper orchestration (`/start-ticket`, `/start-epic`; runner flows above unchanged): loop = `ai_wrap.py next --json` → explicit `ai_run.py <prepare>` → fresh sub-agent on the prompt file → Report gate (print gate line; runs before JSON decision gates) → explicit `ai_run.py <complete>` → confirm success from `status.json`.
6. Step model resolution: model/effort per step resolve at call time from `.ai/step_models.json` (missing file: warn + sonnet/high; invalid: `StepConfigError` -> `[ERROR]`; `preflight_step_models` checks before a prepare mutates state in `--run-auto`/autoflow).

## Invariants / Constraints

- The runner never runs `git add`/`commit`/`push` itself — all code/config/doc edits from any stage land only as working-tree changes for human review.
- Every stage follows prepare → act → complete; `*-complete` functions verify required output files are non-empty (`ensure_non_empty_files`) before advancing `status.json`, and never spawn a WezTerm pane.
- `status.json` transitions are forward-only except for explicit fix loops (dev fix, architect fix, epic design fix).
- Ticket-less/project-level commands (currently only `arch-init`) reuse the same per-ticket status/prompt helpers via a fixed sentinel id (`_arch-init`) rather than forking ticket-less helper variants.
- Skill file content is injected verbatim into prompts — never summarized or transformed by the runner.
- Claude orchestrator never writes under `.ai/runs/` or `.ai/epics/`, never commits, never uses `next --run`; every `*-complete` is confirmed from `status.json` (exit 0 insufficient — distill retry/BLOCK exit 0).
- Report gate: orchestrator pauses on any non-`none` QUESTIONS/ASSUMPTIONS/BLOCKERS or malformed report at every sub-agent return; only the operator can waive an item (ASSUMPTIONS pause too).
- `ai_wrap.py` is read-only (no state mutation, though it calls `ai_run.get_step_model`); `ai_run.py` is not modified by the wrapper layer.
- `ai_run.py` stays logic-free (facade + `main`); `ai_runner` modules keep an acyclic import order; every moved name stays re-exported from `ai_run`. `step_models.json` keys must be real `*-prepare` step names (`KNOWN_PREPARE_STEPS` == routing tables, test-enforced).
- This `system-overview.md`'s headings (Components, Data Flows, Invariants / Constraints, ADR Index) must keep their exact names and order — other tooling (distill, cap checks) reads this file structurally.

## ADR Index

| ADR | Title | Status |
|---|---|---|
| ADR-001 | Claude-layer orchestration via read-only sidecar | proposed |
| ADR-002 | Split runner into `ai_runner` package behind `ai_run` facade; per-step models in project-owned `step_models.json` | proposed |
