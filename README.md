# AI Agent Team Template

A file-driven AI dev workflow. Specialised agents (Architect, Architect Reviewer, Developer, Reviewer, QA, Distiller, and Epic Analyst / Designer / Reviewer / Planner) each read a generated prompt and write their output files straight into your repo. A small Python runner (`.ai/bin/ai_run.py`) builds the prompts, verifies the outputs and tracks state in `status.json`.

**The easiest way to run the team is from Claude Code with the slash commands** (`/create-ticket`, `/start-ticket`, `/create-epic`, `/start-epic`, ...). One Claude session orchestrates; every stage runs in a fresh sub-agent. The runner CLI and WezTerm automation (see [Advanced](#7-advanced-runner-cli-and-wezterm)) remain available.

This repo is the **source template**. You clone it once, then **install** it into each project you want to work on.

```
this repo (template) --install.py--> your-project/.ai/      engine, agents, vault skeleton, step_models.json
                                     ~/.claude/commands,agents   slash commands (global, optional)
```

---

## 1. Prerequisites

| Tool | Why | Check |
|---|---|---|
| Python 3.9+ | runs `install.py` and the runner (stdlib only, nothing to pip install) | `python3 --version` |
| Git | clone the template, review results | `git --version` |
| [Claude Code](https://docs.claude.com/en/docs/claude-code) | runs the slash commands and is the default engine; log in once by running `claude` | `claude --version` |
| [WezTerm](https://wezterm.org/install/macos.html) (optional) | only for the advanced `--auto` / `--auto-flow` modes; `wezterm` must be on `$PATH` | `wezterm --version` |
| Codex CLI (optional) | alternative engine for the advanced modes (`--engine codex`) | `codex --version` |

---

## 2. Quick start

### Step 1. Clone the template

```bash
git clone <this-repo-url> ~/agent-team-template
cd ~/agent-team-template
```

Keep this clone somewhere permanent. To upgrade later: `git pull`, then re-run the install commands from step 2.

### Step 2. Install into your project and into global Claude

Run from the **template repo root** (the installer refuses to run elsewhere).

```bash
# 1. preview, writes nothing
python3 install.py --target /path/to/my-project --global-claude --dry-run

# 2. real install: .ai/ into the project + slash commands/agents into ~/.claude
python3 install.py --target /path/to/my-project --global-claude
```

What this does:

- `--target` installs the engine into the project: `.ai/bin/`, `.ai/agents/`, `.ai/templates/` (managed, overwritten on every install) plus project-owned starter files (`.ai/project_config.json`, `.ai/step_models.json`, `.ai/CLAUDE.md`, vault skeleton) that are created only if missing.
- `--global-claude` writes the 9 slash-command / sub-agent files to `~/.claude/commands` and `~/.claude/agents` once, instead of into every project's `.claude/`. It asks for confirmation separately because it writes outside the project (add `--yes` to skip all prompts).
- The commands call `.ai/bin/ai_wrap.py` and `ai_run.py` by relative path, so **every project still needs its own `.ai/`**; the global install only shares the commands.

Prefer per-project commands? Drop `--global-claude`: the same 9 files go into `my-project/.claude/` instead. Project-level copies override global ones with the same name.

Installer options:

| Flag | Effect |
|---|---|
| `--target <path>` | project directory to install into (required unless `--sync-all`) |
| `--global-claude` | install the slash commands/agents into `~/.claude` instead of the project's `.claude/` |
| `--claude-home <path>` | with `--global-claude`: use this directory instead of `$CLAUDE_CONFIG_DIR` / `~/.claude` |
| `--dry-run` | print planned actions, write nothing |
| `--yes` | skip confirmation prompts |
| `--backup` | copy files about to be overwritten to `.ai_backup_<timestamp>/` (global files: inside the Claude dir) |
| `--with-skills <profile>` | also copy `examples/<profile>/skills/` into `.ai/skills/` (profiles: `mi-portal`, `pclab`, `shopify-jp`) |
| `--force-project-files` | also overwrite the project-owned files listed below |
| `--sync-all [--config <file>]` | install into every project in `projects.json` (see [Upgrading](#8-upgrading-and-syncing-many-projects)) |

What lands in your project:

| Path | Type | On re-install |
|---|---|---|
| `.ai/bin/` (includes the `ai_runner/` package), `.ai/agents/`, `.ai/templates/` | managed engine | overwritten |
| `.ai/project_config.json` | project-owned | kept if it exists |
| `.ai/step_models.json` | project-owned (model/effort per step, see [section 6](#6-choose-the-claude-model-per-step)) | kept if it exists |
| `.ai/CLAUDE.md` | project-owned operating guide | kept if it exists |
| `.ai/vault/architecture/{system-overview.md, modules/_domain.template.md, decisions/ADR-NNN-template.md}` | project-owned skeleton | kept if it exists |
| `.ai/skills/...` | only with `--with-skills` | existing files kept |
| `.claude/commands/{create,start}-{ticket,epic}.md`, `{ticket,epic}-status.md`, `.claude/agents/workflow-step*.md` | managed (9 files); in `~/.claude` with `--global-claude` | overwritten; other files in `.claude/` are never touched |

Your project's root `CLAUDE.md` is handled later by `arch-init`.

### Step 3. Configure the project and initialise the vault (once per project)

All commands run from the **project root** (the runner uses relative `.ai/` paths).

```bash
cd /path/to/my-project
```

**3a. Review `.ai/project_config.json`.** The installer writes a minimal default; set `git.base_branch` and, if you know them, your domains. You can also let `arch-init` infer domains for you (next step).

| Field | Meaning |
|---|---|
| `project_name` | used in prompts |
| `default_domain` | domain used when a ticket is created without `--domain` |
| `git.base_branch` | branch diffed against in review (`develop`, etc.) |
| `engine.default` | `claude` (default) or `codex` (advanced modes only) |
| `autoflow.poll_interval_seconds` / `timeout_seconds` | how `--auto-flow` waits for an agent (defaults 15s / 1800s) |
| `vault.enabled` / `vault.path` | architecture vault on/off (default on, `.ai/vault`) |
| `domains.<name>.paths` | code paths of a domain, shown in prompt context |
| `domains.<name>.skills.<role>` | skill files injected into that role's prompt; roles: `architect`, `developer`, `reviewer`, `qa` |

Optional skills (coding conventions, test rules) are markdown files injected verbatim into role prompts: install a starter set with `--with-skills <profile>`, or write `.ai/skills/<domain>/<skill>/SKILL.md` and list it under `domains.<domain>.skills.<role>`. See `examples/*/project_config.json` for full examples.

**3b. Seed the architecture vault with `arch-init` (do this when the project has existing code and the vault is still the empty skeleton).** The vault (`.ai/vault/architecture/`) is living architecture documentation injected into architect, developer and epic prompts so agents know your system. Skip this for a brand-new empty project; the distill stage fills the vault as tickets land. Don't set `vault.enabled: false` if you want it.

```bash
python3 .ai/bin/ai_run.py arch-init-prepare      # writes the prompt, prints its path
```

Then, in Claude Code opened in the project root, ask it to run the prompt:

```
Read and execute .ai/runs/_arch-init/arch_init/arch_init_prompt.md
```

When Claude finishes:

```bash
python3 .ai/bin/ai_run.py arch-init-complete     # verifies the outputs
```

The agent works in two phases: (1) if `project_config.json` has no `domains`, it infers domains and paths and wires existing skill files; (2) it sweeps the code, fills `system-overview.md` and `modules/<domain>.md`, migrates architecture prose out of `CLAUDE.md`, and adds `@.ai/vault/architecture/system-overview.md` to your root `CLAUDE.md`. Review with `git diff`, fix anything wrong, and commit it yourself. The `system-overview.md` headings (Components, Data Flows, Invariants / Constraints, ADR Index) must keep their names and order; tooling reads them.

Later, when code changes outside the workflow, check for drift: `arch-refresh-prepare` (agent writes a drift report, never edits the overview), run it the same way, then `arch-refresh-complete`.

### Step 4. Run the team with Claude slash commands

Open Claude Code in the project root.

```
/create-ticket "fix-login-bug: users cannot log in with SSO"   # creates the run, asks for the ID
/start-ticket fix-login-bug                                    # runs the whole pipeline
```

That is the whole loop for a ticket. Full command list in [section 3](#3-slash-command-reference); epics in [section 4](#4-epics).

---

## 3. Slash command reference

Slash commands orchestrate from **one** Claude Code session. Each stage (Architect, Architect Review, Developer, Reviewer, QA, Distill) runs in a **fresh sub-agent** that reads the generated prompt file, so roles stay independent. Handoff between stages is files under `.ai/runs/<TICKET>/`; `ai_run.py` owns all state.

| Command | What it does |
|---|---|
| `/create-ticket <source> [--domain d]` | `source` = local epic ticket name (`.ai/epics/*/breakdown/tickets/`), Shortcut id/URL, Jira key/URL, or inline text. Runs `ai_run.py init`; never overwrites an existing run |
| `/start-ticket <TICKET> [--until <stage>]` | drives the whole pipeline, resumable. `--until`: `architect`, `architect-review`, `dev`, `review`, `qa`, `distill` |
| `/ticket-status <TICKET>` | read-only state and next step |
| `/create-epic <source> [--domains a,b]` | inline text / Shortcut / Jira, then `epic-init` |
| `/start-epic <EPIC> [--until <stage>]` | analysis, design, review (with fix loop), ADR distill, breakdown; then asks before `epic-generate-tickets` and lists `/start-ticket` commands (starts none) |
| `/epic-status <EPIC>` | read-only |

```
/create-ticket EPIC-001-US-001-add-schema        # local epic ticket
/create-ticket sc-12345                          # Shortcut story (needs a Shortcut MCP server)
/create-ticket PROJ-42 --domain backend          # Jira issue (needs an Atlassian MCP server)
/create-ticket "fix-login-bug: users cannot log in with SSO"   # inline text
/start-ticket EPIC-001-US-001-add-schema
```

Shortcut/Jira MCP tools are discovered at runtime; if missing or failing, the command stops with an explicit error and creates nothing.

**When the orchestrator pauses.** On any non-empty QUESTIONS, ASSUMPTIONS or BLOCKERS from a sub-agent (relayed to you verbatim; the same stage is re-dispatched with your answers, or for assumptions only you may accept and continue), on a malformed or missing report, before a third fix round on a gate (extra round or abort), and on runner errors. Each dispatch uses the step's `model` and `effort` from `.ai/step_models.json` and echoes `[step] model=... effort=...`.

**What each ticket stage produces** (under `.ai/runs/<TICKET>/`, git-ignored):

| Stage | Output |
|---|---|
| Architect | `architect/task_spec.md`, `design_note.md`, `acceptance_criteria.md`, `assumptions.md` |
| Architect Review | `architect/architect_review.json` (`approve` / `request_changes` / `block`; rejection loops through architect fix) |
| Developer | code in the repo + `dev/implementation_report.md` |
| Reviewer | `review/review_report.json` (`approve` / `request_changes` / `block`) |
| QA | `qa/qa_report.json` (`pass` / `fail`) |
| Distill | refreshes the vault `system-overview.md` + `modules/<domain>.md` |

The ticket is done when review is `approve`, QA is `pass`, and distill completes. If review requests changes or QA fails, the pipeline enters a fix loop: the Developer fixes and **appends** a `## Fix Round N` section to `implementation_report.md`, then review and QA run again (cap of two rounds per gate before it asks you).

**Commits.** The runner and the orchestrator never run `git add/commit/push`. The Developer prompt itself tells the Developer agent to commit code (never `.ai/` files) to a ticket branch; review everything with `git diff` / `git log` before merging.

**Permissions.** Sub-agents inherit the session's permission mode and the wrapper never escalates to bypass. Until you have confirmed how permission prompts inside a sub-agent behave in your setup, add an allow-list, e.g. in `.claude/settings.local.json`:

```json
{ "permissions": { "allow": [
  "Bash(python .ai/bin/ai_run.py *)", "Bash(python3 .ai/bin/ai_run.py *)",
  "Bash(python .ai/bin/ai_wrap.py *)", "Bash(python3 .ai/bin/ai_wrap.py *)",
  "Bash(git status *)", "Bash(git diff *)", "Bash(git log *)", "Edit", "Write"
] } }
```

Add `git add`/`git commit` rules only if you accept the Developer's commits. A sub-agent stalled on a permission prompt shows up as a failed step.

Known unknowns (verify once in your environment): whether per-call `effort` is honored (if the tool rejects it, the commands fall back to the `workflow-step-medium` / `workflow-step-high` agents), whether permission prompts inside a sub-agent surface to you or are auto-denied, and whether `SendMessage` can continue a finished sub-agent (otherwise a fresh agent runs on the same prompt file, still correct). With the `rtk` hook installed, `ai_wrap.py ... --json` output is retried via `rtk proxy` if it comes back non-JSON.

---

## 4. Epics

An **epic** is a larger feature. The epic pipeline is **planning only** (no code): it analyses, designs and reviews the feature, then breaks it into feature-slice ticket files that seed the ticket workflow. Analysis, design and breakdown each pass a review gate with its own fix loop.

```
epic-init -> Analyst -> Analysis Reviewer (fix loop) -> Designer -> Design Reviewer (fix loop)
          -> ADR distill -> Planner -> Breakdown Reviewer (fix loop) -> epic-generate-tickets
```

```
/create-epic "Multi-tenant billing support" --domains backend,frontend
/start-epic EPIC-001
```

`/start-epic` stops after the approved breakdown review and asks before generating tickets (`epic-generate-tickets` refuses while a breakdown review exists and is not approved). Then work each story like any ticket, in story-map order (later stories may depend on earlier ones):

```
/start-ticket EPIC-001-US-001-<slug>
```

Epic outputs under `.ai/epics/<EPIC>/`:

| Stage | Output |
|---|---|
| Analysis | `analysis/epic_analysis.md` |
| Analysis review | `review/epic_analysis_review.json` (`approve` / `request_changes` / `block`) |
| Analysis fix (on rejection) | corrected `epic_analysis.md`; previous review archived in `fix/` |
| Design | `design/epic_design.md` |
| Design review | `review/epic_review.json` |
| Design fix (on rejection) | corrected `epic_design.md`; previous review archived in `fix/` |
| ADR distill (after approve) | architecture decisions in `.ai/vault/architecture/decisions/` |
| Breakdown | `breakdown/epic_story_map.md`, `breakdown/epic_story_status.md` + `breakdown/tickets/EPIC-NNN-US-NNN-<slug>.md` |
| Breakdown review | `review/epic_breakdown_review.json` |
| Breakdown fix (on rejection) | corrected story map, tracker and tickets; previous review archived in `fix/` |

`--domains` is a comma-separated list; it defaults to all domains in the config.

**Tickets are feature slices.** A ticket is one independently verifiable feature/outcome, delivered across every domain it needs (never split by domain, layer or file). Each ticket lists its `## Domains` (primary first), a `## Domain Checklist` with a `### <domain>` subsection per domain (required when there is more than one), and a `## Verification` section a manager can run on dev/stage. Sizing is qualitative; there are no day estimates or ticket-count targets. `epic-breakdown-complete` checks the ticket shape and that every ticket file has exactly one row in `epic_story_status.md` (and vice versa).

`epic-generate-tickets` seeds each run with `domain` = the primary domain and, for multi-domain tickets, `domains` = the full list, so ticket prompts carry the paths, skills and vault modules of every listed domain. Developer, Reviewer and QA check the checklist and verification items (the Developer records evidence under `## Verification Evidence`). Distill still refreshes only the primary domain's module doc for a multi-domain ticket. Ticket runs that were already seeded are never overwritten; a changed ticket file is reported as `[STALE]`.

---

## 5. Slash commands vs WezTerm automation

| | slash commands | `--auto-flow` (advanced) |
|---|---|---|
| Sessions | one Claude Code session, fresh sub-agent per stage | one WezTerm pane + `claude` per step |
| Questions / blockers | asked in your session | you watch each pane |
| Ticket source | local epic ticket / Shortcut / Jira / text | `input.md` by hand |
| Unattended | no (gates need you) | yes |
| Needs WezTerm | no | yes |

Both use the same runner, state files and `.ai/step_models.json`; you can switch between them at any time.

---

## 6. Choose the Claude model per step

Each `*-prepare` step has its own model and effort, defined in **`.ai/step_models.json`** (project-owned; created by `install.py` from `.ai/templates/step_models.template.json`). The values are used by:

- the slash commands (passed to each sub-agent dispatch), and
- the WezTerm auto modes, which launch `claude --dangerously-skip-permissions --model <model> --effort <effort>`.

Defaults (Opus is used for epic analysis and design; Sonnet elsewhere, effort tuned per step):

```json
{
  "default": { "model": "sonnet", "effort": "high" },
  "steps": {
    "architect-prepare":        { "model": "sonnet", "effort": "high" },
    "architect-fix-prepare":    { "model": "sonnet", "effort": "medium" },
    "epic-analysis-prepare":    { "model": "opus",   "effort": "high" },
    "epic-design-prepare":      { "model": "opus",   "effort": "high" },
    "epic-design-fix-prepare":  { "model": "sonnet", "effort": "high" },
    "architect-review-prepare": { "model": "sonnet", "effort": "high" },
    "dev-prepare":              { "model": "sonnet", "effort": "high" },
    "review-prepare":           { "model": "sonnet", "effort": "high" },
    "dev-fix-prepare":          { "model": "sonnet", "effort": "medium" },
    "qa-prepare":               { "model": "sonnet", "effort": "medium" },
    "distill-prepare":          { "model": "sonnet", "effort": "medium" },
    "epic-review-prepare":      { "model": "sonnet", "effort": "medium" },
    "epic-breakdown-prepare":   { "model": "sonnet", "effort": "high" },
    "adr-distill-prepare":      { "model": "sonnet", "effort": "medium" },
    "epic-analysis-review-prepare":  { "model": "sonnet", "effort": "medium" },
    "epic-analysis-fix-prepare":     { "model": "sonnet", "effort": "high" },
    "epic-breakdown-review-prepare": { "model": "sonnet", "effort": "medium" },
    "epic-breakdown-fix-prepare":    { "model": "sonnet", "effort": "high" }
  }
}
```

`default` applies to any step not listed under `steps`.

### To change it

1. Edit `.ai/step_models.json` in the project, e.g. run the developer on Opus:
   ```json
   "dev-prepare": { "model": "opus", "effort": "high" }
   ```
2. Save. The file is read every time a step starts; nothing to rebuild or restart.
3. The next run echoes the choice, e.g. `[AUTO] Step 'dev-prepare' -> model=opus, effort=high` (WezTerm modes) or `[dev-prepare] model=opus effort=high` (slash commands).

`model` accepts aliases (`sonnet`, `opus`, `haiku`) or full model IDs; `effort` accepts the levels your Claude Code version supports (`low`, `medium`, `high`, ...; check `claude --help`). The runner only checks that both are non-empty strings; a bad value fails when Claude launches. The slash commands hand `model` to the Agent tool, which accepts aliases; use aliases there rather than full model IDs.

### Gotchas

- **Re-install keeps your edits.** `install.py` creates the file only when it is missing; `--force-project-files` resets it to the shipped template (use `--backup` to keep a copy). To change the shipped defaults for all projects, edit `.ai/templates/step_models.template.json` and `.ai/step_models.json` in this template repo (keep them identical) and re-run install on new projects.
- **Validation is strict.** A malformed file, a missing `default`, an empty `model`/`effort`, or a `steps` key that is not a real `*-prepare` step name stops the run with `[ERROR] .ai/step_models.json: ...` (checked before a step starts, so run state is not half-advanced).
- **Missing file** is not fatal: the runner prints one `[WARN]` and uses `sonnet` / `high` for every step. Re-run `install.py` to restore the file.
- **Manual flow** (pasting a prompt into your own Claude session) uses whatever model that session runs; switch with `/model`.
- **Claude engine only.** `--engine codex` passes no model/effort flags and never reads the file.
- Only `*-prepare` steps spawn an agent, so only those keys matter.

---

## 7. Advanced: runner CLI and WezTerm

Everything the slash commands do goes through `python3 .ai/bin/ai_run.py`, which you can also use directly, run from the project root. Every stage is **prepare, act, complete**: `*-prepare` writes a prompt file, an agent writes the outputs, `*-complete` verifies they are non-empty and advances `status.json`.

The auto modes launch the engine with permission checks disabled (`claude --dangerously-skip-permissions`, `codex --dangerously-bypass-approvals-and-sandbox`) and need WezTerm. Only use them in repos you trust, ideally on a branch.

### Tickets

```bash
# create the ticket and run the first step
python3 .ai/bin/ai_run.py ticket TICKET-1 "Add CSV export to the orders page" --domain backend

python3 .ai/bin/ai_run.py ticket TICKET-1 --next        # advance one step
python3 .ai/bin/ai_run.py ticket TICKET-1 --auto        # each step opens a WezTerm tab with the prompt pre-loaded (you press Enter)
python3 .ai/bin/ai_run.py ticket TICKET-1 --auto-flow   # hands-off: spawn Claude, wait, advance until done
```

Extra flags: `--engine codex`, `--no-prompt` (skip confirmations), `--domain <name>`. Shortest form: `python3 .ai/bin/ai_run.py TICKET-1 "requirement"`.

Step by step:

```bash
python3 .ai/bin/ai_run.py init TICKET-1 "requirement text" --domain backend
python3 .ai/bin/ai_run.py next TICKET-1             # show the next step
python3 .ai/bin/ai_run.py next TICKET-1 --run       # run the next prepare/complete step
python3 .ai/bin/ai_run.py next TICKET-1 --run-auto  # same, and open a WezTerm pane
python3 .ai/bin/ai_run.py status TICKET-1           # status.json
```

A `prepare` step run without an auto mode prints a prompt file path. Open Claude in the project root, ask it to read and execute that file, then run `next` again (it runs the matching `*-complete`). Individual stages: `architect-prepare|complete`, `architect-review-prepare|complete`, `architect-fix-prepare|complete`, `dev-prepare|complete`, `dev-fix-prepare|complete`, `review-prepare|complete`, `qa-prepare|complete`, `distill-prepare|complete`.

### Epics

```bash
python3 .ai/bin/ai_run.py epic EPIC-001 "Multi-tenant billing support" --domains backend,frontend
python3 .ai/bin/ai_run.py epic EPIC-001 --next          # one step
python3 .ai/bin/ai_run.py epic EPIC-001 --auto          # WezTerm pane per step
python3 .ai/bin/ai_run.py epic EPIC-001 --auto-flow     # whole epic hands-off

python3 .ai/bin/ai_run.py epic-generate-tickets EPIC-001             # seed input.md per story
python3 .ai/bin/ai_run.py epic-generate-tickets EPIC-001 --init-dirs # also create full run dirs
python3 .ai/bin/ai_run.py ticket EPIC-001-US-001-<slug> --auto-flow
```

Manual equivalents: `epic-init`, `epic-next <EPIC> [--run|--run-auto]`, `epic-status <EPIC>`, and per-stage `epic-analysis-*`, `epic-analysis-review-*`, `epic-analysis-fix-*`, `epic-design-*`, `epic-review-*` (design review), `epic-design-fix-*`, `adr-distill-*`, `epic-breakdown-*`, `epic-breakdown-review-*`, `epic-breakdown-fix-*` (each `-prepare` / `-complete`).

### Read-only helper

`python3 .ai/bin/ai_wrap.py next <TICKET> --json`, `epic-next <EPIC> --json` and `validate-id <ID>` print routing data (step, prompt path, model, effort, fix round) without changing any state. The slash commands are built on it.

---

## 8. Upgrading and syncing many projects

After `git pull` in the template repo, re-run install to refresh the managed engine, the Claude commands and `ai_runner/`. Project-owned files (config, `step_models.json`, vault content) are preserved.

```bash
python3 install.py --target /path/to/my-project --global-claude
```

To push updates to many projects, copy `example.projects.json` to `projects.json` (git-ignored) and list absolute paths (or paths relative to the template repo):

```json
{ "projects": ["/path/to/project-a", "../project-b"] }
```

```bash
python3 install.py --sync-all --global-claude   # uses ./projects.json; asks once for the global write
python3 install.py --sync-all --config other.json --backup
```

`--sync-all` skips the per-project confirmations (the `--global-claude` write still asks unless `--yes`).

---

## 9. Troubleshooting

| Symptom | Fix |
|---|---|
| `Source files not found. Run this script from the ai-agent-team repo root.` | run `install.py` from the template repo root |
| `Skills profile '<x>' not found` | pick a name under `examples/` |
| `/start-ticket` etc. not found in Claude Code | install with `--global-claude` or into the project; restart Claude Code; check the 9 files exist |
| `Ticket not found. Create it with /create-ticket.` | run `/create-ticket` first (or `ai_run.py init`) |
| `Vault missing or disabled` on `arch-init-prepare` | re-run install; make sure `.ai/vault/` exists and `vault.enabled` is not `false` |
| `[ERROR] .ai/step_models.json: ...` | fix the named key, or restore with `install.py --force-project-files --backup` |
| `[WARN] .ai/step_models.json not found` | re-run `install.py` for the project |
| `[WARN] wezterm spawn failed` | WezTerm is not on `$PATH` or not running; use the slash commands or the manual flow |
| `[ERROR] Unknown engine` | `engine.default` / `--engine` must be `claude` or `codex` |
| `*-complete` fails with an empty file | the agent did not write the required file; re-run the stage, then `*-complete` |
| Auto-flow times out | raise `autoflow.timeout_seconds` in `project_config.json` |
| Stuck or wrong stage | `/ticket-status <TICKET>` or `python3 .ai/bin/ai_run.py status <TICKET>`; state lives in `.ai/runs/<TICKET>/status.json` |
| Command cannot find `.ai/` | run from the project root, not a subfolder |

---

## 10. Quick command reference

```text
# install (template repo root)
python3 install.py --target <path> [--global-claude] [--with-skills P] [--dry-run] [--backup] [--yes] [--force-project-files]
python3 install.py --sync-all [--global-claude] [--config projects.json]

# project setup (project root)
python3 .ai/bin/ai_run.py arch-init-prepare | arch-init-complete
python3 .ai/bin/ai_run.py arch-refresh-prepare | arch-refresh-complete

# Claude slash commands (inside Claude Code)
/create-ticket <source> [--domain d]    /start-ticket <TICKET> [--until stage]    /ticket-status <TICKET>
/create-epic <source> [--domains a,b]   /start-epic <EPIC> [--until stage]        /epic-status <EPIC>

# runner CLI (advanced)
python3 .ai/bin/ai_run.py ticket <ID> "<req>" [--domain D] [--next|--auto|--auto-flow] [--engine E]
python3 .ai/bin/ai_run.py next <ID> [--run|--run-auto]       status <ID>
python3 .ai/bin/ai_run.py epic <ID> "<req>" [--domains a,b] [--next|--auto|--auto-flow] [--engine E]
python3 .ai/bin/ai_run.py epic-next <ID> [--run|--run-auto]  epic-status <ID>
python3 .ai/bin/ai_run.py epic-generate-tickets <ID> [--init-dirs]
```

See `.ai/CLAUDE.md` (installed into your project) for the operating guide the agents follow, and `.ai/agents/*.md` for each role's instructions.
