# Workflow

## Responsibility

Owns the entire structured AI dev-team pipeline: ticket and epic run-state tracking, prompt
generation for every agent role, output verification, and stage routing. Everything under
`.ai/bin/`, `.ai/agents/`, `.ai/templates/`, and `examples/` belongs to this domain.

## Key Components

- `.ai/bin/ai_run.py` — single-file CLI runner; path/status helpers, prompt builders, prepare/
  complete handlers, next-action routers, WezTerm auto-spawn, argparse wiring.
- `.ai/agents/*.md` — role instruction files (architect, architect_reviewer, developer, reviewer,
  qa, epic_analyst, epic_designer, epic_reviewer, epic_planner, arch_init) injected verbatim into
  generated prompts.
- `.ai/project_config.json` — project name, base branch, engine default, vault settings, and
  `domains.<name>.{paths, skills}` used to scope prompts per domain/role.
- `.ai/skills/<domain>/<skill>/SKILL.md` — domain skill files wired into role prompts via
  `project_config.json`'s `skills` lists.
- `.ai/templates/` — example architect artifact/report templates (not injected automatically).
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

The `arch-init` command is the one project-level, ticket-less exception: it reuses this same
prepare/act/complete + status.json machinery via a fixed sentinel ticket id (`_arch-init`,
`.ai/runs/_arch-init/`) instead of forking ticket-less helper variants.

## Entry Points

- CLI: `python .ai/bin/ai_run.py <subcommand> ...` (see `KNOWN_SUBCOMMANDS`, `build_parser`,
  `main`).
- Positional shortcut: `python .ai/bin/ai_run.py <TICKET> [inline_req]` (auto-inits or advances).
- `next` / `epic-next` — print or execute the next pipeline step for a ticket/epic.
- `ticket --auto-flow` / `epic --auto-flow` — run the full pipeline unattended via WezTerm +
  sentinel polling.
- `arch-init-prepare` / `arch-init-complete` — project-level bootstrap, no ticket id.

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
  instructions (Developer, arch-init), never from Python.
- `*-complete` functions must never trigger a WezTerm spawn — only `*-prepare` steps do, and only
  when `--run-auto` is passed.
