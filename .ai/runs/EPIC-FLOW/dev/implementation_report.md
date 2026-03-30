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

---

## Fix Round 1 — Routing bug fix, dead code removal, redundant call cleanup

### Summary of Changes

Fixed three issues reported by the Reviewer:

1. **Routing bug in `epic_next_action`** (HIGH): After `epic-design-fix-prepare` runs, it deletes `epic_review.json` and sets `current_stage = "epic_design_fix_prepare"`. On the next routing call, `review_decision` was `None`, so the `review_decision in {"request_changes", "block"}` guard evaluated to `False` — the inner `current_stage == "epic_design_fix_prepare"` check was never reached. The function fell through and returned `"epic-review-prepare"` instead of `"epic-design-fix-complete"`, skipping the complete step entirely. Fixed by moving both stage-based checks (`epic_design_fix_prepare` → complete, `epic_design_fix_complete` → review-prepare) BEFORE the `review_decision` guard.

2. **Dead-code path in breakdown routing** (LOW): The second `if current_stage == "epic_breakdown_prepare": return "epic-breakdown-complete"` block was unreachable in normal flow — the story map exists only after the agent writes it, which happens after prepare completes. Removed the dead block.

3. **Redundant `build_epic_review_fix_context` call** (LOW): `epic_design_fix_prepare` was calling `build_epic_review_fix_context` before archiving. This was identical to the call already made by `epic_review_complete`. Removed the builder call; the function now just checks whether the already-written context file exists at `epic_review_fix_context_path(epic)`.

### Files Modified

| File | Change |
|------|--------|
| `.ai/bin/ai_run.py` | Fixed routing logic in `epic_next_action`; removed dead breakdown branch; removed redundant fix context call in `epic_design_fix_prepare` |

### Key Decisions

- The routing fix keeps stage-based checks at the top level of `epic_next_action` before any `review_decision` guard, matching the linear-stage pattern used throughout the function.
- The redundant call fix reads `epic_review_fix_context_path(epic)` directly and checks `.exists()` rather than calling the builder again. Safe because `epic_review_complete` always builds the context before this function runs.

### Review Issues Addressed

1. **HIGH — ai_run.py not committed**: Already committed in branch commits (`ae951d5`, `9e6e300`). Confirmed by `git diff HEAD -- .ai/bin/ai_run.py` producing no output and `git diff main...HEAD --stat` showing +856 lines in `ai_run.py`.
2. **HIGH — Routing bug** (`.ai/bin/ai_run.py:1611-1614 epic_next_action`): Fixed. `current_stage == "epic_design_fix_prepare"` now checked before `review_decision` guard so it correctly returns `"epic-design-fix-complete"` when the review file has been archived/deleted.
3. **MEDIUM — Staged but uncommitted `epic_planner.md`**: Already committed in the branch. `git status -- .ai/agents/epic_planner.md` shows no modifications. No further action needed.
4. **LOW — Dead-code breakdown branch** (`.ai/bin/ai_run.py:1634-1635`): Removed.
5. **LOW — Redundant `build_epic_review_fix_context` call**: Removed from `epic_design_fix_prepare`; function now checks whether context file exists instead of rebuilding it.

### QA Issues Addressed

None reported by QA in this cycle.

### Commands/Tests Run

```bash
# Syntax check
python .ai/bin/ai_run.py --help
# → all epic-* subcommands present, no errors

# Routing fix validation: set stage=epic_design_fix_prepare with no review file present
python .ai/bin/ai_run.py epic-init TEST-EPIC-ROUTING "Test routing fix"
# (manually set current_stage=epic_design_fix_prepare, create analysis+design files, no review)
python .ai/bin/ai_run.py epic-next TEST-EPIC-ROUTING
# → epic-design-fix-complete  ✓  (previously returned epic-analysis-prepare or epic-review-prepare)

# Cleanup
rm -rf .ai/epics/TEST-EPIC-ROUTING

# Commit changes
git add .ai/bin/ai_run.py
git commit -m "fix epic_next_action routing bug and clean up dead code"
# → [feature/epic-flow c73a2b7] ...
```
