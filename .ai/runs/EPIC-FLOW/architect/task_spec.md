# Task Spec — Epic Workflow Support

## Technical Summary

Extend `ai_run.py` with a parallel epic-level planning pipeline. The epic flow covers high-level requirement analysis, solution design, design review (with fix loop), and ticket breakdown. It is purely a planning pipeline — no code execution, no dev/review/qa stages.

The implementation adds:
- New CLI subcommands (`epic-*`)
- A new directory root `.ai/epics/<EPIC>/` for all epic artifacts
- Dedicated prepare/complete functions for each epic stage
- `epic-next` command with `--run` / `--run-auto` support
- Prompt generation for four new agent roles (files already exist)

---

## Scope

- Add epic path helpers (`EPICS` constant, `epic_path()`, `epic_status_file()`, etc.) to `ai_run.py`
- Add `ensure_epic_dirs()` to create the required directory structure
- Add `init_epic_status()` for epic-specific status shape
- Add `epic_init` command that writes `epic_input.md` and initializes `status.json`
- Add prepare/complete function pairs for: `epic_analysis`, `epic_design`, `epic_design_fix`, `epic_review`, `epic_breakdown`
- Add `epic_next_action()` routing logic based on file existence and review decision
- Add `epic_next_step()` with WezTerm spawning support (reuse `spawn_claude_wezterm`)
- Add `build_epic_role_prompt()` (or extend `build_role_prompt`) for epic agent file names
- Add `build_epic_review_fix_context()` to generate `epic_review_fix_context.md` from `epic_review.json`
- Register all new subcommands in `build_parser()`

---

## Out of Scope

- Auto-creating ticket runs (`.ai/runs/<TICKET>/`) from epic breakdown output
- JSON ticket export format
- Jira or Shortcut API integration
- Changes to the existing ticket workflow (`init`, `architect-*`, `dev-*`, `review-*`, `qa-*`)

---

## Impacted Modules / Files

| File | Change type |
|------|-------------|
| `.ai/bin/ai_run.py` | Primary — add epic constants, path helpers, prepare/complete functions, parser commands |
| `.ai/agents/epic_analyst.md` | Already exists — used by `epic_analysis_prepare` |
| `.ai/agents/epic_designer.md` | Already exists — used by `epic_design_prepare` and `epic_design_fix_prepare` |
| `.ai/agents/epic_reviewer.md` | Already exists — used by `epic_review_prepare` |
| `.ai/agents/epic_planner.md` | Already exists — used by `epic_breakdown_prepare` |
| `.ai/project_config.json` | May need epic agent skill mappings added (if skills are defined) |
