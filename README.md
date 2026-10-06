# AI Agent Team Template

A file-driven AI dev workflow. A Python runner (`.ai/bin/ai_run.py`) generates prompts for each role (Architect, Developer, Reviewer, QA, Distiller, Epic Analyst/Designer/Reviewer/Planner). An AI engine (Claude Code or Codex) reads each prompt and writes output files straight into your repo. The runner verifies outputs and advances state.

This repo is the **source template**. You clone it once, then **install** it into each project you want to work on.

```
this repo (template)  --install.py-->  your-project/.ai/   (engine + agents + vault skeleton)
```

---

## 1. Prerequisites

| Tool | Why | Check |
|---|---|---|
| Python 3.9+ | runs `ai_run.py` and `install.py` (stdlib only, no pip install) | `python3 --version` |
| Git | clone template, diff results | `git --version` |
| [WezTerm](https://wezterm.org/install/macos.html) | `--auto` / `--auto-flow` open a pane and paste prompts; `wezterm` must be on `$PATH` | `wezterm --version` |
| [Claude Code CLI](https://docs.claude.com/en/docs/claude-code) | default AI engine (`claude`) | `claude --version` |
| Codex CLI (optional) | alternative engine, `--engine codex` | `codex --version` |

Notes:

- WezTerm is only needed for auto modes. Without it you can still run `prepare` steps and paste the prompt into Claude yourself.
- Auto modes launch the engine with permission checks disabled (`claude --dangerously-skip-permissions`, `codex --dangerously-bypass-approvals-and-sandbox`). Only run in repos you trust, ideally on a branch.
- Log in to Claude Code once before first use: run `claude` and follow the login flow.
- The runner never runs `git add/commit/push`. All agent edits stay as working-tree changes for you to review with `git diff`.

---

## 2. Get the template

```bash
git clone <this-repo-url> agent-team-template
cd agent-team-template
```

Keep this clone somewhere permanent (e.g. `~/Projects/agent-team-template`). To upgrade later: `git pull`, then re-run install (see §3.3).

---

## 3. Install into a project

Run from the **template repo root** (installer refuses to run elsewhere).

### 3.1 Single project

```bash
# preview first, writes nothing
python3 install.py --target /path/to/my-project --dry-run

# real install
python3 install.py --target /path/to/my-project
```

Options:

| Flag | Effect |
|---|---|
| `--target <path>` | project directory to install into |
| `--dry-run` | show planned actions only |
| `--yes` | skip the confirm prompt |
| `--backup` | copy existing managed files to `.ai_backup_<timestamp>/` before overwrite |
| `--with-skills <profile>` | also copy `examples/<profile>/skills/` into `.ai/skills/` (profiles: `mi-portal`, `pclab`, `shopify-jp`; see `examples/`) |
| `--force-project-files` | overwrite project-owned files (`project_config.json`, `.ai/CLAUDE.md`, vault skeleton) |

### 3.2 What gets installed

| Path in your project | Type | On re-install |
|---|---|---|
| `.ai/bin/`, `.ai/agents/`, `.ai/templates/` | managed (engine) | **overwritten** |
| `.ai/project_config.json` | project-owned | skipped if exists |
| `.ai/CLAUDE.md` | project-owned (operating guide) | skipped if exists |
| `.ai/vault/architecture/{system-overview.md, modules/_domain.template.md, decisions/ADR-NNN-template.md}` | project-owned skeleton | skipped if exists |
| `.ai/skills/...` | only with `--with-skills` | existing files skipped |

Nothing outside `.ai/` is touched. Your project's root `CLAUDE.md` is handled later by `arch-init`.

### 3.3 Sync many projects / upgrade

Copy `example.projects.json` to `projects.json` (git-ignored) and list your projects (absolute paths, or relative to the template repo):

```json
{ "projects": ["/path/to/project-a", "../project-b"] }
```

```bash
python3 install.py --sync-all                 # uses ./projects.json
python3 install.py --sync-all --config other.json --backup
```

`--sync-all` skips confirmation. Use after `git pull` to push engine updates to every project. Your project-owned files (config, vault content) are preserved.

---

## 4. First-time setup in each project

All commands below run **from the project root** (the runner uses relative `.ai/` paths).

```bash
cd /path/to/my-project
```

### 4.1 Configure `.ai/project_config.json`

Installer writes a minimal default:

```json
{
  "project_name": "my-project",
  "default_domain": "default",
  "git": { "base_branch": "main" },
  "domains": { "default": { "paths": [], "skills": {} } }
}
```

Fields you will care about:

| Field | Meaning |
|---|---|
| `project_name` | used in prompts |
| `default_domain` | domain used when `init` gets no `--domain` |
| `git.base_branch` | branch diffed against in review (set to `develop` etc. if needed) |
| `engine.default` | `claude` (default) or `codex` |
| `autoflow.poll_interval_seconds` / `timeout_seconds` | how `--auto-flow` waits for an agent to finish (defaults 15s / 1800s) |
| `vault.enabled` / `vault.path` | architecture vault on/off (default on, `.ai/vault`) |
| `domains.<name>.paths` | code paths belonging to a domain (shown in prompt context) |
| `domains.<name>.skills.<role>` | skill files injected into that role's prompt. Roles: `architect`, `developer`, `reviewer`, `qa` |

You can hand-edit it, or let `arch-init` fill `domains` for you (next step). A full example lives in this repo's `.ai/project_config.json` and `examples/*/project_config.json`.

### 4.2 (Optional) Add skills

Skills are markdown files injected verbatim into role prompts (coding conventions, testing rules, etc.).

- Start from an example: `python3 install.py --target . --with-skills <profile>` (run from template repo), or
- write your own at `.ai/skills/<domain>/<skill>/SKILL.md` and list the path under `domains.<domain>.skills.<role>`.

### 4.3 Initialize the architecture vault (`arch-init`)

The vault (`.ai/vault/architecture/`) is living architecture documentation injected into architect/developer/epic prompts so agents know your system. `arch-init` seeds it from your actual code.

```bash
python3 .ai/bin/ai_run.py arch-init-prepare     # writes the prompt
# open Claude Code in the project root, paste/read the printed prompt file, let it run
python3 .ai/bin/ai_run.py arch-init-complete    # verifies outputs
```

What the agent does:

1. **Phase 1**: if `project_config.json` has no `domains`, infers domains + paths and wires existing skill files.
2. **Phase 2**: sweeps the code, fills `system-overview.md` and `modules/<domain>.md`, migrates architecture prose out of `CLAUDE.md`, and adds this import line to your root `CLAUDE.md`:
   `@.ai/vault/architecture/system-overview.md`

Review with `git diff`, edit anything wrong, commit it yourself. Requires vault skeleton from install (do not set `vault.enabled: false`).

`system-overview.md` headings (Components, Data Flows, Invariants / Constraints, ADR Index) must keep their names and order. Tooling reads them.

### 4.4 Later: check for drift

When code evolves outside the workflow:

```bash
python3 .ai/bin/ai_run.py arch-refresh-prepare   # agent re-derives overview and writes drift report
python3 .ai/bin/ai_run.py arch-refresh-complete  # verifies report written, overview unchanged
```

---

## 5. Working with tickets

A **ticket** = one unit of work, run through: Architect → Architect Review → Developer → Reviewer → QA → Distill.

Every stage is **prepare → act → complete**:

1. `*-prepare`: runner writes a prompt file.
2. act: Claude reads the prompt, writes output files in the repo.
3. `*-complete`: runner verifies outputs are non-empty and advances `status.json`.

### 5.1 Fastest path: one command

```bash
# create ticket + run first step
python3 .ai/bin/ai_run.py ticket TICKET-1 "Add CSV export to the orders page" --domain backend

# advance one step at a time
python3 .ai/bin/ai_run.py ticket TICKET-1 --next

# open each step in a new WezTerm tab with the prompt pre-loaded (you press Enter)
python3 .ai/bin/ai_run.py ticket TICKET-1 --auto

# hands-off: spawn Claude, wait for finish, advance through all stages until done
python3 .ai/bin/ai_run.py ticket TICKET-1 --auto-flow
```

Extra flags: `--engine codex`, `--no-prompt` (skip confirmations), `--domain <name>`.

Shortest form: `python3 .ai/bin/ai_run.py TICKET-1 "requirement"` (inits and runs; no flags).

### 5.2 Manual step-by-step

```bash
python3 .ai/bin/ai_run.py init TICKET-1 "requirement text" --domain backend
python3 .ai/bin/ai_run.py next TICKET-1            # show next step
python3 .ai/bin/ai_run.py next TICKET-1 --run      # run next prepare/complete step
python3 .ai/bin/ai_run.py next TICKET-1 --run-auto # same + open WezTerm pane
python3 .ai/bin/ai_run.py status TICKET-1          # current stage
```

When a `prepare` step runs without auto mode, it prints a prompt file path. Open Claude in the project root, point it at that file (e.g. "read and execute `.ai/runs/TICKET-1/architect/architect_prompt.md`"), wait until files are written, then run `next` again (it runs the `*-complete` step).

Individual stage commands also exist (`architect-prepare`, `architect-complete`, `architect-review-prepare/complete`, `dev-prepare/complete`, `review-prepare/complete`, `qa-prepare/complete`, `distill-prepare/complete`).

### 5.3 Stages and outputs

All under `.ai/runs/<TICKET>/` (git-ignored):

| Stage | Agent writes |
|---|---|
| Architect | `architect/task_spec.md`, `design_note.md`, `acceptance_criteria.md`, `assumptions.md` |
| Architect Review | approve / request_changes / block (loops through architect fix on rejection) |
| Developer | code in repo + `dev/implementation_report.md` |
| Reviewer | `review/review_report.json` (`approve` / `request_changes` / `block`) |
| QA | `qa/qa_report.json` (`pass` / `fail`) |
| Distill | refreshes vault `system-overview.md` + `modules/<domain>.md` |

Done when review = `approve` and QA = `pass` (and distill completes).

### 5.4 Fix loops

If review says `request_changes`/`block`, or QA says `fail`, `next` routes you to `dev-fix-prepare`. Developer fixes and **appends** a `## Fix Round N` section to `implementation_report.md`, then `dev-fix-complete`, then back to review. Architect review rejections use `architect-fix-prepare/complete`. Distill has a bounded retry if vault line caps are exceeded.

---

## 6. Working with epics

An **epic** is a larger feature. The epic pipeline is **planning only** (no code): it analyzes, designs, reviews, then breaks the epic into ticket files, which seed the ticket workflow.

```
epic-init → Analyst → Designer → Reviewer ⟲ design fix → (ADR distill) → Planner → epic-generate-tickets
```

### 6.1 Run an epic

```bash
# create + run first step
python3 .ai/bin/ai_run.py epic EPIC-001 "Multi-tenant billing support" --domains backend,frontend

python3 .ai/bin/ai_run.py epic EPIC-001 --next        # one step
python3 .ai/bin/ai_run.py epic EPIC-001 --auto        # WezTerm pane per step
python3 .ai/bin/ai_run.py epic EPIC-001 --auto-flow   # run the full epic hands-off
```

Manual equivalents: `epic-init`, `epic-next <EPIC> [--run|--run-auto]`, `epic-status <EPIC>`, plus per-stage `epic-analysis-*`, `epic-design-*`, `epic-review-*`, `epic-design-fix-*`, `adr-distill-*`, `epic-breakdown-*` (each with `-prepare` / `-complete`).

`--domains` is a comma-separated list; defaults to all domains in config.

### 6.2 Epic outputs

Under `.ai/epics/<EPIC>/`:

| Stage | Output |
|---|---|
| Analysis | `analysis/epic_analysis.md` |
| Design | `design/epic_design.md` |
| Review | `review/epic_review.json` (`approve` / `request_changes` / `block`) |
| Design fix (on rejection) | corrected `epic_design.md`, previous review archived in `fix/` |
| ADR distill (after approve) | records architecture decisions in `.ai/vault/architecture/decisions/` |
| Breakdown | `breakdown/epic_story_map.md` + `breakdown/tickets/US-NNN-<slug>.md` |

### 6.3 Turn the breakdown into tickets

```bash
python3 .ai/bin/ai_run.py epic-generate-tickets EPIC-001            # seed input.md per story
python3 .ai/bin/ai_run.py epic-generate-tickets EPIC-001 --init-dirs # also create full run dirs
```

Each story becomes ticket `EPIC-001-US-001-<slug>` etc. Work them like any ticket:

```bash
python3 .ai/bin/ai_run.py ticket EPIC-001-US-001-<slug> --auto-flow
```

Run stories in story-map order; later stories may depend on earlier ones.

---

## 7. Typical end-to-end flow for a new project

```bash
# once: clone template
git clone <this-repo-url> ~/agent-team-template

# install into project
cd ~/agent-team-template
python3 install.py --target ~/work/my-project --with-skills <profile-if-any>

# in project
cd ~/work/my-project
git checkout -b ai/setup
# edit .ai/project_config.json (base_branch, domains)
python3 .ai/bin/ai_run.py arch-init-prepare      # run in Claude, then:
python3 .ai/bin/ai_run.py arch-init-complete
git diff                                          # review, then commit yourself

# small task
python3 .ai/bin/ai_run.py ticket FIX-1 "Describe the bug/feature" --auto-flow

# big feature
python3 .ai/bin/ai_run.py epic EPIC-001 "Describe the epic" --auto-flow
python3 .ai/bin/ai_run.py epic-generate-tickets EPIC-001
python3 .ai/bin/ai_run.py ticket EPIC-001-US-001-<slug> --auto-flow
```

Tip: use a feature branch per ticket. Runner leaves everything uncommitted, so commit after reviewing `git diff`.

---

## 8. Change the Claude model per step

In auto modes (`--auto`, `--auto-flow`, `--run-auto`) the runner launches Claude as
`claude --dangerously-skip-permissions --model <model> --effort <effort>`, picking the model and effort **per step**. Defaults live in `.ai/bin/ai_run.py`:

```python
_DEFAULT_STEP_MODEL = ("sonnet", "high")      # fallback for unlisted steps
STEP_MODEL = {
    "architect-prepare":        ("sonnet", "high"),
    "architect-fix-prepare":    ("sonnet", "medium"),
    "epic-analysis-prepare":    ("opus",   "high"),
    "epic-design-prepare":      ("opus",   "high"),
    "epic-design-fix-prepare":  ("sonnet", "high"),
    "architect-review-prepare": ("sonnet", "high"),
    "dev-prepare":              ("sonnet", "high"),
    "review-prepare":           ("sonnet", "high"),
    "dev-fix-prepare":          ("sonnet", "medium"),
    "qa-prepare":               ("sonnet", "medium"),
    "distill-prepare":          ("sonnet", "medium"),
    "epic-review-prepare":      ("sonnet", "medium"),
    "epic-breakdown-prepare":   ("sonnet", "high"),
    "adr-distill-prepare":      ("sonnet", "medium"),
}
```

Each key is a `*-prepare` step name, each value is `(model, effort)`. Rationale of the defaults: Opus only for deep design reasoning (epic analysis/design), Sonnet elsewhere to save tokens, effort tuned per step.

### To change it

1. Open `.ai/bin/ai_run.py`, find `STEP_MODEL` (near the top, ~line 50).
2. Edit the tuple for the step, e.g. run the developer on Opus:
   ```python
   "dev-prepare": ("opus", "high"),
   ```
3. Or change the fallback for every unlisted step via `_DEFAULT_STEP_MODEL`.
4. Next auto run prints `[AUTO] Step 'dev-prepare' -> model=opus, effort=high` so you can confirm.

Valid values: `--model` accepts aliases (`sonnet`, `opus`, `haiku`) or full model IDs (check `claude --help` for your version). `--effort` accepts the levels your Claude Code version supports (`low`, `medium`, `high`, ...; verify with `claude --help`). A bad value fails when Claude launches, not in Python.

### Gotchas

- **Re-install overwrites it.** `.ai/bin/` is a managed dir. `install.py` / `--sync-all` replaces `ai_run.py`, so a per-project edit is lost on upgrade. To make a change stick everywhere: edit `STEP_MODEL` in **this template repo** (`.ai/bin/ai_run.py`), then run `python3 install.py --sync-all`. For a one-project override, use `--backup` on upgrade and re-apply the edit.
- **Auto modes only.** Manual flow (paste prompt into your own Claude session) uses whatever model that session runs. Switch with `/model` inside Claude Code.
- **Claude engine only.** `--engine codex` ignores `STEP_MODEL` (no model/effort flags are passed).
- **Only `*-prepare` steps** spawn an agent, so only those keys matter. `*-complete` steps never open a pane.
- Not configurable from `project_config.json` today; the table is hardcoded.

---

## 9. Troubleshooting

| Symptom | Fix |
|---|---|
| `Source files not found. Run this script from the ai-agent-team repo root.` | run `install.py` from the template repo root |
| `Skills profile '<x>' not found` | pick a name under `examples/` |
| `Vault missing or disabled` on `arch-init-prepare` | re-run install; make sure `.ai/vault/` exists and `vault.enabled` is not `false` |
| `[WARN] wezterm spawn failed` | WezTerm not on `$PATH` or not running; use manual prompt paste instead, or fix `$PATH` |
| `[ERROR] Unknown engine` | `engine.default` / `--engine` must be `claude` or `codex` |
| `*-complete` fails with empty file | agent did not write the required file; re-run the agent step, then `*-complete` |
| Auto-flow times out | raise `autoflow.timeout_seconds` in `project_config.json` |
| Stuck/wrong stage | `python3 .ai/bin/ai_run.py status <TICKET>` (or `epic-status <EPIC>`); state lives in `.ai/runs/<TICKET>/status.json` |
| Command can't find `.ai/` | run from the project root, not a subfolder |

---

## 10. Quick command reference

```text
# install (template repo root)
python3 install.py --target <path> [--with-skills P] [--dry-run] [--backup] [--yes] [--force-project-files]
python3 install.py --sync-all [--config projects.json]

# project-level (project root)
python3 .ai/bin/ai_run.py arch-init-prepare | arch-init-complete
python3 .ai/bin/ai_run.py arch-refresh-prepare | arch-refresh-complete

# tickets
python3 .ai/bin/ai_run.py ticket <ID> "<req>" [--domain D] [--next|--auto|--auto-flow] [--engine E]
python3 .ai/bin/ai_run.py next <ID> [--run|--run-auto]
python3 .ai/bin/ai_run.py status <ID>

# epics
python3 .ai/bin/ai_run.py epic <ID> "<req>" [--domains a,b] [--next|--auto|--auto-flow] [--engine E]
python3 .ai/bin/ai_run.py epic-next <ID> [--run|--run-auto]
python3 .ai/bin/ai_run.py epic-status <ID>
python3 .ai/bin/ai_run.py epic-generate-tickets <ID> [--init-dirs]
```

See `.ai/CLAUDE.md` (installed into your project) for the full operating guide the agents follow, and `.ai/agents/*.md` for each role's instructions.
