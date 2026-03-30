# Implementation Report — Epic Workflow Support

## Summary of Changes

Extended `.ai/bin/ai_run.py` with a complete epic-level planning pipeline. The epic flow mirrors the ticket workflow in structure but operates on `.ai/epics/<EPIC>/` and covers: analysis → design → review (with fix loop) → breakdown. No changes were made to existing ticket workflow code.

---

## Files Modified

| File | Change |
|------|--------|
| `.ai/bin/ai_run.py` | Added ~350 lines: epic path helpers, status helpers, role prompt builders, all prepare/complete functions, routing logic, parser commands, and main dispatch |

---

## Key Decisions

1. **No refactor of existing status helpers.** The design note suggested generalizing `load_status`/`save_status` to accept a `Path` argument. Instead, parallel `load_epic_status`/`save_epic_status`/etc. helpers were added. This avoids any regression risk to the ticket workflow since the existing functions are untouched.

2. **`complete_epic_stage` is one atomic write.** Unlike the ticket `complete_stage` which calls `add_history` (a second load+save), the epic version mutates the dict once and saves once. This avoids a redundant status read.

3. **`build_epic_review_fix_context` does not archive.** Archiving `epic_review.json` → `previous_epic_review.json` is done in `epic_design_fix_prepare`, not inside `build_epic_review_fix_context`. This matches the structure of the ticket flow (`build_fix_context` builds context; archiving is separate in `dev_fix_prepare`). It also allows `epic_review_complete` to call `build_epic_review_fix_context` without inadvertently archiving the review.

4. **`epic_next_action` routing.** Follows the design note exactly: analysis → design → fix loop guard → review → breakdown. The fix loop clears the review report path (via `unlink`), so the routing correctly falls through to `epic-review-prepare` after `epic-design-fix-complete`.

5. **Epic skills fall back gracefully.** `get_epic_role_skills` looks up role names like `epic_analyst` in `project_config.json` under the same domain. No epic skills are currently defined there, so skill blocks are silently omitted from prompts — no error raised.

6. **`_EPIC_PREPARE_STEP_PROMPT` is a separate dict.** Keeps ticket and epic prepare-step maps isolated. WezTerm spawning reuses `spawn_claude_wezterm` unchanged.

---

## Assumptions Followed

- All four epic agent files already existed and are non-empty (verified via `Glob`).
- `ai_run.py` stays as a single file per the python_orchestration skill rule.
- `epic_design.md` is overwritten (not appended) on fix rounds.
- `project_config.json` does not define epic role skills — graceful fallback applied.
- Epic init writes `requirement.strip() + "\n"` matching ticket flow behavior.

---

## Commands/Tests Run

```
# Syntax check
python .ai/bin/ai_run.py --help

# Smoke test: init
python .ai/bin/ai_run.py epic-init TEST-EPIC-1 "Test epic requirement"
# → [OK] Initialized epic TEST-EPIC-1 at .ai/epics/TEST-EPIC-1 (domain=workflow)

# Smoke test: status + next routing
python .ai/bin/ai_run.py epic-status TEST-EPIC-1
# → prints status.json with current_stage="init"
python .ai/bin/ai_run.py epic-next TEST-EPIC-1
# → "epic-analysis-prepare"

# Smoke test: prepare and routing
python .ai/bin/ai_run.py epic-analysis-prepare TEST-EPIC-1
# → [OK] Wrote .ai/epics/TEST-EPIC-1/analysis/epic_analysis_prompt.md
python .ai/bin/ai_run.py epic-next TEST-EPIC-1
# → "epic-analysis-complete"

# Smoke test: complete guard
python .ai/bin/ai_run.py epic-analysis-complete TEST-EPIC-1
# → [ERROR] Missing or empty files: .ai/epics/TEST-EPIC-1/analysis/epic_analysis.md

# Regression check: existing ticket workflow
python .ai/bin/ai_run.py status EPIC-flow
# → prints status.json correctly (domain=workflow, no errors)

# Cleanup
rm -rf .ai/epics/TEST-EPIC-1
```
