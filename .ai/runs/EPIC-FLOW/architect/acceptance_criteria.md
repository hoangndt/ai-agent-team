# Acceptance Criteria — Epic Workflow Support

## Functional Criteria

### 1. Epic Init

- `python .ai/bin/ai_run.py epic-init <EPIC> "<requirement>"` creates:
  - `.ai/epics/<EPIC>/input/epic_input.md` with the requirement text
  - `.ai/epics/<EPIC>/status.json` with `current_stage: "init"` and correct domain

### 2. Analysis Stage

- `epic-analysis-prepare <EPIC>` writes a non-empty `epic_analysis_prompt.md` to `.ai/epics/<EPIC>/analysis/`
- The prompt includes: epic_analyst.md role content, project context, skill sections (if configured), and instruction to write `epic_analysis.md`
- `epic-analysis-complete <EPIC>` succeeds only if `epic_analysis.md` is non-empty; fails with a clear error if missing

### 3. Design Stage

- `epic-design-prepare <EPIC>` requires `epic_analysis.md` to exist and be non-empty
- Writes a non-empty `epic_design_prompt.md` referencing the epic_designer role
- `epic-design-complete <EPIC>` succeeds only if `epic_design.md` is non-empty

### 4. Review Stage

- `epic-review-prepare <EPIC>` requires `epic_analysis.md` and `epic_design.md` to be non-empty
- Writes `epic_review_prompt.md` referencing the epic_reviewer role
- The prompt instructs the agent to write strict JSON to `epic_review.json`
- `epic-review-complete <EPIC>`:
  - Verifies `epic_review.json` is valid, parseable JSON
  - Pretty-prints and re-saves the JSON
  - Extracts and records the `decision` field in status
  - Triggers `build_epic_review_fix_context` regardless of decision

### 5. Design Fix Stage (Review Loop)

- When review decision is `request_changes` or `block`:
  - `epic-next --run` routes to `epic-design-fix-prepare`
- `epic-design-fix-prepare <EPIC>`:
  - Archives `epic_review.json` to `fix/previous_epic_review.json`
  - Writes `epic_review_fix_context.md` from archived review issues
  - Writes `epic_design_fix_prompt.md` with context referencing the fix files
- `epic-design-fix-complete <EPIC>` verifies `epic_design.md` is still non-empty
- After fix complete, `epic-next --run` routes back to `epic-review-prepare`
- The fix loop can repeat multiple times without breaking status

### 6. Breakdown Stage

- `epic-breakdown-prepare <EPIC>` requires approved review (`decision == "approve"`)
- Writes `epic_breakdown_prompt.md` referencing the epic_planner role
- Prompt instructs agent to write:
  - `breakdown/epic_story_map.md`
  - One or more files in `breakdown/tickets/*.md` using the defined format
- `epic-breakdown-complete <EPIC>`:
  - Verifies `epic_story_map.md` is non-empty
  - Verifies at least one `.md` file exists in `breakdown/tickets/`
  - Fails with a clear error if either condition is not met

### 7. epic-next Command

- `epic-next <EPIC>` (no flags) prints the next step name without executing it
- `epic-next <EPIC> --run` executes the next step
- `epic-next <EPIC> --run-auto` executes the prepare step and spawns a WezTerm pane with the prompt pre-loaded
- `--run-auto` only spawns WezTerm for prepare steps, not complete steps
- `epic-status <EPIC>` prints the current `status.json` as formatted JSON

### 8. No Regression

- All existing ticket workflow commands (`init`, `architect-prepare`, `dev-prepare`, etc.) continue to work correctly and unmodified
- No shared global state between epic and ticket flows
- Running `epic-*` commands does not affect files under `.ai/runs/`

---

## Validation Cases

- Running `epic-analysis-prepare` before `epic-init` raises a `FileNotFoundError` or exits with a clear error message
- Running `epic-review-prepare` when `epic_design.md` is missing fails with a descriptive error
- Running `epic-breakdown-prepare` when review is `request_changes` routes to fix instead
- Running `epic-next` on a finished epic prints `"done"`
- `epic_review.json` written with invalid JSON causes `epic-review-complete` to raise a `json.JSONDecodeError` (not silently pass)

---

## Failure Cases

- `epic-breakdown-complete` fails if `tickets/` directory is empty (no ticket files generated)
- `epic-analysis-complete` fails if `epic_analysis.md` is empty or missing
- `epic-design-fix-prepare` fails if no `epic_review.json` exists to derive fix context from
- All `*-complete` stages update status to `"failed"` state when verification fails, matching existing behavior
