# Workflow

## Responsibility

Owns the entire structured AI dev-team pipeline: ticket and epic run-state tracking, prompt
generation for every agent role, output verification, and stage routing. Everything under
`.ai/bin/`, `.ai/agents/`, `.ai/templates/`, and `examples/` belongs to this domain.

## Key Components

- `.ai/bin/ai_run.py` — CLI entry point + re-export facade (`main`); no logic (ADR-002).
- `.ai/bin/ai_runner/` — logic package: constants, paths, state, context, prompts, stage modules
  (architect, dev_qa, distill, arch, epic, `epic_review_stages` = analysis/breakdown review + fix gates, `epic_breakdown_checks` = `validate_breakdown`, domain parsing, review-started/seeded-run helpers), steps, routing, wezterm, autoflow, cli.
- `.ai/step_models.json` — project-owned per-`*-prepare`-step model/effort; scaffolded by `install.py`
  from `.ai/templates/step_models.template.json`; read by `get_step_model` (`ai_runner/steps.py`).
- `.ai/agents/*.md` — role instruction files (architect, architect_reviewer, developer, reviewer,
  qa, epic_analyst, epic_analysis_reviewer, epic_designer, epic_reviewer, epic_planner, epic_breakdown_reviewer, arch_init) injected verbatim into
  generated prompts.
- `.ai/project_config.json` — project name, base branch, engine default, vault settings, and
  `domains.<name>.{paths, skills}` used to scope prompts per domain/role.
- `.ai/skills/<domain>/<skill>/SKILL.md` — domain skill files wired into role prompts via
  `project_config.json`'s `skills` lists.
- `.ai/templates/` — example architect artifact/report templates (not injected automatically).
- `.ai/bin/ai_wrap.py` — read-only sidecar: `next|epic-next <ID> --json` (step, kind, prompt_path,
  model/effort, next_complete, fix_round, missing_outputs, status.json echo) and `validate-id`;
  imports `ai_run.next_action`/`epic_next_action`; never mutates state.
- `.claude/commands/*.md`, `.claude/agents/workflow-step*.md` — Claude Code wrapper: `/create-*`,
  `/start-*`, `/*-status` orchestrators plus generic per-stage worker agents (medium/high tiers); both carry the Report gate / final-report contract.
  Installed by `install.py` via explicit `CLAUDE_MANAGED_FILES` (not whole-dir).
- `examples/` — reference fixture projects (`mi-portal`, `pclab`, `shopify-jp`) used for manual
  validation of runner changes.

## How It Works

Every ticket/epic stage follows the same prepare → act → complete shape:

1. `<stage>-prepare` (Python) reads required input files, builds a prompt via
   `build_role_prompt` / `build_epic_role_prompt` (Role Instruction + Project Context +
   Architecture Vault context + Domain Skills + Task Instruction), writes it to
   `.ai/runs/<TICKET>/<stage>/..._prompt.md`, and advances `status.json`.
2. **act** (human pastes the prompt into an AI agent, or `--run-auto`/`--auto-flow` spawns a
   WezTerm pane and pastes it automatically) — the agent writes output files directly into the
   repo.
3. `<stage>-complete` (Python) verifies the expected output files are non-empty
   (`ensure_non_empty_files`), parses/re-serializes JSON reports where applicable, builds fix
   context files from review/QA findings, and advances `status.json`.

`next_action` / `epic_next_action` inspect `status.json` plus the presence/decision of review and
QA/report files to compute the next step, so `next --run` / `epic-next --run` can drive the whole
pipeline, including fix loops (architect fix, dev fix, epic design fix) triggered by
`request_changes`/`block`/`fail` decisions.

Epic flow (ADR-003, proposed): Analyst → Analysis Reviewer → Designer → Design Reviewer → ADR distill → Planner → Breakdown Reviewer, each with a fix loop. `epic-generate-tickets` seeds `domain` + optional `domains` into ticket `status.json`; ticket prompts union paths/skills/vault modules across domains. Tickets are feature slices (`## Domains`, `## Verification`, `## Domain Checklist` if multi-domain).

The `arch-init` command is the one project-level, ticket-less exception: it reuses this same
prepare/act/complete + status.json machinery via a fixed sentinel ticket id (`_arch-init`,
`.ai/runs/_arch-init/`) instead of forking ticket-less helper variants.

Step models: `get_step_model` reads `step_models.json` at call time; missing file warns and falls back to sonnet/high, invalid file raises `StepConfigError` (`[ERROR]`); `preflight_step_models` runs before a prepare mutates state in `--run-auto`/autoflow.

Claude-wrapper path (ADR-001, proposed): `/start-ticket|/start-epic` loop runs
`ai_wrap.py next --json` → explicit `ai_run.py <prepare>` → fresh `workflow-step` sub-agent on
`prompt_path` → Report gate (pause on non-`none` QUESTIONS/ASSUMPTIONS/BLOCKERS or malformed report; before JSON decision gates) → explicit `ai_run.py <complete>` → confirm from `status.json`. Fix-round counts come
from `status.json` history (cap 2, then ask operator).

## Entry Points

- CLI: `python .ai/bin/ai_run.py <subcommand> ...` (see `KNOWN_SUBCOMMANDS`, `build_parser` in `ai_runner/cli.py`;
  `main` in `ai_run.py`).
- Positional shortcut: `python .ai/bin/ai_run.py <TICKET> [inline_req]` (auto-inits or advances).
- `next` / `epic-next` — print or execute the next pipeline step for a ticket/epic.
- `ticket --auto-flow` / `epic --auto-flow` — run the full pipeline unattended via WezTerm +
  sentinel polling.
- `arch-init-prepare` / `arch-init-complete` — project-level bootstrap, no ticket id.
- `/create-ticket`, `/start-ticket`, `/ticket-status`, `/create-epic`, `/start-epic`, `/epic-status` — Claude slash commands; `python .ai/bin/ai_wrap.py next|epic-next|validate-id`.

## Dependencies

- Architecture Vault (`.ai/vault/`) — read by `build_vault_context` for architect/developer/
  epic_analyst/epic_designer prompts (and `arch_init` via the `architect` skill alias), written by
  `arch-init` and (line-cap enforcement) `distill`.
- Domain Skills (`.ai/skills/`) — read via `get_effective_role_skills` / `get_epic_role_skills`.
- External: `wezterm` CLI (auto-spawn), `git` (base-branch diffs, never committed by the runner
  itself), `claude` / `codex` CLI engines (`ENGINE_REGISTRY`).

## Gotchas / Invariants

- `role_file_map` (which agent instruction file to load) and `skills_role` (which domain skill
  list to load) are two separate keying decisions inside `build_role_prompt` — adding a role to
  one without the other silently resolves to an empty skill list instead of the intended reuse
  (see `architect_reviewer` and `arch_init`, both aliased to `architect`'s skills).
- `load_status`/`load_project_config` raise `FileNotFoundError` if `status.json` /
  `project_config.json` are missing — every ticket-scoped helper assumes `init`/`epic-init` (or,
  for `arch-init`, `ensure_arch_init_status()`) has already run.
- The runner never auto-commits; every `git commit` happens only from within an agent's task
  instructions (Developer, dev-fix), never from Python. `arch-init` is explicitly forbidden from
  running `git add`/`git commit`/`git push` (per AC-7) — all its edits land as working-tree
  changes only.
- `*-complete` functions must never trigger a WezTerm spawn — only `*-prepare` steps do, and only
  when `--run-auto` is passed.
- Wrapper orchestrator must not write under `.ai/runs/`/`.ai/epics/`, commit, or use `next --run`
  (it re-routes from mutated `current_stage`); confirm every complete from `status.json`, not exit
  code (distill retry and `[BLOCK]` exit 0). `ai_wrap.py` stays read-only.
- Import order is acyclic: constants -> paths -> state -> context -> prompts -> stage modules -> routing -> wezterm/autoflow -> cli. Put new code in the owning module; do not re-grow `ai_run.py`.
- A function moved between `ai_runner` modules must stay re-exported from `ai_run`; patch the defining module, not the facade.
- Never hardcode model/effort in Python; `step_models.json` keys must equal `KNOWN_PREPARE_STEPS` (test-enforced). `ai_wrap.py` stays read-only but calls `ai_run.get_step_model`.
- `epic-generate-tickets` needs an approved breakdown review once any breakdown review/fix exists (warn-only otherwise); `epic-breakdown-complete`/`-fix-complete` share `validate_breakdown` (tracker ids <-> ticket files one-to-one); `epic_next_action` never returns `done` before breakdown review approval; no numeric sizing in prompts.
- Multi-domain tickets: distill refreshes only the primary domain's module doc.
