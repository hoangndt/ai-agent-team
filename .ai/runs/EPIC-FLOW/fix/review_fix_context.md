# Review Fix Context

Use this file to fix review findings without re-implementing the whole feature.

Reviewer decision: request_changes

## High Severity Issues
1. File: .ai/bin/ai_run.py
   Issue: The primary deliverable is not committed. `git diff HEAD -- .ai/bin/ai_run.py` shows ~900 lines of uncommitted working-tree modifications. The implementation report states the work is done, but the changes are not staged or committed. Until committed, the epic workflow commands do not exist in the repository's git history and cannot be reproduced or deployed from source.
2. File: .ai/bin/ai_run.py:1611-1614 (epic_next_action)
   Issue: Routing bug in the design fix loop. After `epic-design-fix-prepare` runs, it deletes `epic_review.json` (via `unlink`) and sets `current_stage = 'epic_design_fix_prepare'`. On the next call to `epic_next_action`, `review_decision` is None (no review file), so the guard `if review_decision in {'request_changes', 'block'}` evaluates to False. The inner check `if current_stage == 'epic_design_fix_prepare': return 'epic-design-fix-complete'` is never reached. The function then falls to the review check, finds no `epic_review.json`, and returns `'epic-review-prepare'` instead of `'epic-design-fix-complete'`. Running `epic-next --run` after the designer has fixed the design would skip the fix-complete verification and jump straight to a new review prepare — violating the prepare/complete contract. Fix: add an explicit `current_stage == 'epic_design_fix_prepare'` branch BEFORE or OUTSIDE the `review_decision` guard.

## Medium Severity Issues
1. File: .ai/agents/epic_planner.md
   Issue: There is a staged but uncommitted modification to `epic_planner.md` (the `Suggested Order` template section was changed). This is a post-commit modification that diverges from the version in git history without a commit. This should either be committed with an explanation or reverted if unintentional.

## Low Severity Issues
1. File: .ai/bin/ai_run.py:1634-1635 (epic_next_action)
   Issue: Dead-code path in breakdown routing. The second `if current_stage == 'epic_breakdown_prepare': return 'epic-breakdown-complete'` block (lines 1634-1635) is only reachable if `epic_story_map_path` already exists AND `current_stage` is `'epic_breakdown_prepare'`. In normal flow, `epic_breakdown_prepare` is called before the Claude agent writes the story map, so both conditions cannot be simultaneously true. The block is effectively unreachable and should be removed to avoid confusion.
2. File: .ai/bin/ai_run.py (epic_design_fix_prepare + build_epic_review_fix_context)
   Issue: `build_epic_review_fix_context` is called twice during the fix cycle: once in `epic_review_complete` (writing the initial fix context) and again at the top of `epic_design_fix_prepare` before archiving. The second call reads the same `epic_review.json` and overwrites the same context file with identical content. This is harmless but redundant. The call in `epic_design_fix_prepare` can be removed since the context was already written by `epic_review_complete`.

## Reviewer Summary
The implementation is functionally complete in terms of code structure — all epic pipeline stages (init, analysis, design, review, fix loop, breakdown), routing logic, parser commands, and WezTerm integration are present and largely correct. However, two blockers prevent approval: (1) the entire `ai_run.py` change is uncommitted and not staged, making the primary deliverable absent from git; (2) there is a concrete routing bug in `epic_next_action` where `epic-design-fix-prepare` → `epic-design-fix-complete` routing fails because the `current_stage` guard is nested inside a `review_decision` check that evaluates to False once `epic_review.json` is deleted. The fix loop would silently skip the complete step and jump to a new review. Fix both issues and re-submit for review.
