# Assumptions — Epic Workflow Support

## Explicit Assumptions

1. **Agent files already exist.** All four epic agent files (`.ai/agents/epic_analyst.md`, `epic_designer.md`, `epic_reviewer.md`, `epic_planner.md`) are present and non-empty. No new agent files need to be created in this ticket.

2. **`ai_run.py` remains a single file.** Per the python_orchestration skill rule, the runner stays as one script. Epic code is added within the same file, separated by a clear comment block.

3. **Status helpers can be shared.** The existing `load_status`, `save_status`, `update_stage`, `complete_stage`, etc. can be generalized to accept a `Path` argument instead of deriving the path from a ticket ID. This avoids duplicating all status management functions for epics.

4. **Epic skills use the same project_config.json lookup.** The `get_role_skills` / `load_skill_contents` functions are reused. If `project_config.json` does not define skill mappings for epic roles (e.g. `epic_analyst`, `epic_designer`), skill content is silently omitted from the prompt — no error.

5. **`epic_design_fix_prepare` updates `epic_design.md` in-place.** Unlike the ticket fix flow which appends to `implementation_report.md`, the epic design fix overwrites `epic_design.md` with the corrected design. There is no append-only constraint on `epic_design.md`.

6. **Breakdown ticket filenames are agent-generated.** The epic_planner agent is responsible for naming ticket files (e.g. `US-001-add-cli-commands.md`). The `epic-breakdown-complete` step only verifies at least one `.md` file exists in `tickets/` — it does not enforce naming format.

7. **WezTerm integration is unchanged.** `spawn_claude_wezterm()` is reused as-is. Epic prepare steps are simply added to a new `_EPIC_PREPARE_STEP_PROMPT` dict.

8. **Domain for epic is the same as the project default.** Epic status is initialized with the same domain as ticket workflow (i.e. `workflow`). No separate domain resolution is needed for epics.

---

## Unknowns

1. **Should epic skills be added to `project_config.json`?** The input does not specify skill files for epic roles. If the same skills apply (e.g. `python_orchestration`, `agent_prompts`), they should be added to `project_config.json` under each epic role key. The developer should confirm with the requester or make a pragmatic call.

2. **What triggers `epic-design-fix-complete` to verify?** The current ticket flow verifies the implementation report on fix complete. For epics, the fix complete step should verify that `epic_design.md` is still non-empty after the fix. This is assumed — the input does not specify explicitly.

3. **Can the review loop run more than once?** The fix loop is designed to be repeatable (identical to ticket flow). The `previous_epic_review.json` is overwritten each fix round. If preserving all prior review rounds is important, the developer should add round-indexed archiving. This is not specified in the input — left as a pragmatic decision.

4. **Should `epic-next --run-auto` work when WezTerm is not installed?** Existing behavior for ticket flow is to print a warning and continue. Epic flow should match this behavior.

5. **Is `epic_input.md` written verbatim or trimmed?** Ticket flow writes `requirement.strip() + "\n"`. Epic init should do the same. This is assumed but not specified.
