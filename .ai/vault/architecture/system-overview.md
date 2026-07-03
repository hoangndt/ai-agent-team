# System Overview

Fixed headings below (Components, Data Flows, Invariants / Constraints, ADR Index) are a contract read by later tooling (distill, cap checks). Do not rename or reorder them.

## Components

| Component | Responsibility | Entry point | Module doc |
|---|---|---|---|
| Workflow Runner | Single-file CLI that drives the ticket and epic prepare/act/complete pipeline, owns `status.json` transitions, prompt assembly, and routing | `.ai/bin/ai_run.py` | modules/workflow.md |
| Agent Role Files | Per-role instructions (architect, developer, reviewer, qa, epic_*, arch_init) injected verbatim into generated prompts | `.ai/agents/*.md` | modules/workflow.md |
| Domain Config | `project_config.json` — project name, base branch, per-domain paths, and per-role skill file lists | `.ai/project_config.json` | modules/workflow.md |
| Domain Skills | Skill files injected into role prompts, keyed by domain + role | `.ai/skills/<domain>/<skill>/SKILL.md` | modules/workflow.md |
| Architecture Vault | Living architecture docs (system overview, per-domain modules, ADRs) injected into architect/developer/epic prompts as context | `.ai/vault/` | modules/workflow.md |
| Run State | Per-ticket and per-epic working directories holding prompts, reports, and JSON review/QA outputs | `.ai/runs/<TICKET>/`, `.ai/epics/<EPIC>/` | modules/workflow.md |
| WezTerm Bridge | Spawns a WezTerm pane and launches an AI engine (Claude/Codex) to auto-paste generated prompts and poll for a completion sentinel | `spawn_ai_wezterm`, `wait_for_sentinel` in `.ai/bin/ai_run.py` | modules/workflow.md |

## Data Flows

1. Ticket workflow: `init` → Architect (design artifacts) → Architect Reviewer (approve/request_changes/block) → \[fix loop\] → Developer (code + implementation report, commits) → Reviewer (review_report.json) → QA (qa_report.json) → done. Each stage is `prepare` (Python writes a prompt file) → `act` (agent writes output files) → `complete` (Python verifies non-empty outputs and advances `status.json`).
2. Epic workflow: `epic-init` → Epic Analyst (epic_analysis.md) → Epic Designer (epic_design.md) → Epic Reviewer (epic_review.json, approve/request_changes/block) → \[design fix loop\] → Epic Planner (story map + per-story ticket files) → `epic-generate-tickets` seeds each ticket into the ticket workflow above.
3. arch-init workflow (project-level, ticket-less, sentinel id `_arch-init`): `arch-init-prepare` → Arch-Init agent (Phase 1: bootstrap `project_config.json` domains if missing; Phase 2: sweep code + migrate CLAUDE.md architecture prose into this vault, rewire root `CLAUDE.md` to `@`-import `system-overview.md`) → `arch-init-complete` verifies outputs.
4. Prompt assembly: `build_role_prompt` / `build_epic_role_prompt` compose Role Instruction + Project Context + Architecture (Vault) context + Domain Skills + (optional) Figma context + Task Instruction into a single prompt file written to the run directory.

## Invariants / Constraints

- The runner never runs `git add`/`commit`/`push` itself — all code/config/doc edits from any stage land only as working-tree changes for human review.
- Every stage follows prepare → act → complete; `*-complete` functions verify required output files are non-empty (`ensure_non_empty_files`) before advancing `status.json`, and never spawn a WezTerm pane.
- `status.json` transitions are forward-only except for explicit fix loops (dev fix, architect fix, epic design fix).
- Ticket-less/project-level commands (currently only `arch-init`) reuse the same per-ticket status/prompt helpers via a fixed sentinel id (`_arch-init`) rather than forking ticket-less helper variants.
- Skill file content is injected verbatim into prompts — never summarized or transformed by the runner.
- This `system-overview.md`'s headings (Components, Data Flows, Invariants / Constraints, ADR Index) must keep their exact names and order — other tooling (distill, cap checks) reads this file structurally.

## ADR Index

| ADR | Title | Status |
|---|---|---|
| — | No architecture decisions recorded yet | — |
