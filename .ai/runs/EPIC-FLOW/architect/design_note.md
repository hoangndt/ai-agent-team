# Design Note — Epic Workflow Support

## Implementation Approach

Follow the exact same structural pattern used by the ticket flow. The epic system is a self-contained parallel pipeline within `ai_run.py`. All new functions mirror their ticket counterparts in naming, structure, and behavior — but operate on `.ai/epics/<EPIC>/` instead of `.ai/runs/<TICKET>/`.

---

## Main Flow

```
epic-init
  → epic-analysis-prepare  → [agent writes epic_analysis.md]  → epic-analysis-complete
  → epic-design-prepare    → [agent writes epic_design.md]    → epic-design-complete
  → epic-review-prepare    → [agent writes epic_review.json]  → epic-review-complete
       ↓ if request_changes/block
  → epic-design-fix-prepare → [agent fixes epic_design.md, updates fix context]
                            → epic-design-fix-complete
       ↑ loop back to epic-review-prepare
       ↓ if approve
  → epic-breakdown-prepare → [agent writes epic_story_map.md + tickets/*.md]
                           → epic-breakdown-complete
  → done
```

---

## Directory Structure

```
EPICS = BASE / "epics"         # .ai/epics/

.ai/epics/<EPIC>/
  status.json
  input/
    epic_input.md              # Written by epic-init
  analysis/
    epic_analysis_prompt.md    # Written by epic-analysis-prepare
    epic_analysis.md           # Written by agent
  design/
    epic_design_prompt.md
    epic_design.md
  review/
    epic_review_prompt.md
    epic_review.json
  fix/
    epic_design_fix_prompt.md
    epic_review_fix_context.md   # Built from epic_review.json
    previous_epic_review.json    # Archived before fix round
  breakdown/
    epic_breakdown_prompt.md
    epic_story_map.md
    tickets/
      US-001-<slug>.md
      US-002-<slug>.md
      ...
```

---

## New Constants and Path Helpers

Add after the existing path helpers block:

```python
EPICS = BASE / "epics"

def epic_path(epic: str) -> Path:
    return EPICS / epic

def epic_status_file(epic: str) -> Path:
    return epic_path(epic) / "status.json"

def epic_input_dir(epic: str) -> Path:
    return epic_path(epic) / "input"

def epic_input_file(epic: str) -> Path:
    return epic_input_dir(epic) / "epic_input.md"

def epic_analysis_dir(epic: str) -> Path:
    return epic_path(epic) / "analysis"

def epic_analysis_prompt_path(epic: str) -> Path:
    return epic_analysis_dir(epic) / "epic_analysis_prompt.md"

def epic_analysis_path(epic: str) -> Path:
    return epic_analysis_dir(epic) / "epic_analysis.md"

def epic_design_dir(epic: str) -> Path:
    return epic_path(epic) / "design"

def epic_design_prompt_path(epic: str) -> Path:
    return epic_design_dir(epic) / "epic_design_prompt.md"

def epic_design_path(epic: str) -> Path:
    return epic_design_dir(epic) / "epic_design.md"

def epic_review_dir(epic: str) -> Path:
    return epic_path(epic) / "review"

def epic_review_prompt_path(epic: str) -> Path:
    return epic_review_dir(epic) / "epic_review_prompt.md"

def epic_review_report_path(epic: str) -> Path:
    return epic_review_dir(epic) / "epic_review.json"

def epic_fix_dir(epic: str) -> Path:
    return epic_path(epic) / "fix"

def epic_design_fix_prompt_path(epic: str) -> Path:
    return epic_fix_dir(epic) / "epic_design_fix_prompt.md"

def epic_review_fix_context_path(epic: str) -> Path:
    return epic_fix_dir(epic) / "epic_review_fix_context.md"

def previous_epic_review_path(epic: str) -> Path:
    return epic_fix_dir(epic) / "previous_epic_review.json"

def epic_breakdown_dir(epic: str) -> Path:
    return epic_path(epic) / "breakdown"

def epic_breakdown_prompt_path(epic: str) -> Path:
    return epic_breakdown_dir(epic) / "epic_breakdown_prompt.md"

def epic_story_map_path(epic: str) -> Path:
    return epic_breakdown_dir(epic) / "epic_story_map.md"

def epic_tickets_dir(epic: str) -> Path:
    return epic_breakdown_dir(epic) / "tickets"
```

---

## Status Management

Epic status reuses `load_status` / `save_status` signatures but calls `epic_status_file(epic)`.

Introduce parallel helpers: `load_epic_status`, `save_epic_status`, `update_epic_stage`, `complete_epic_stage`, `fail_epic_stage`, `set_epic_artifact`, `set_epic_runner`.

Alternatively, refactor existing status functions to accept a `path: Path` argument and reuse them for both tickets and epics. This is the preferred minimal approach to avoid duplication.

---

## Role Prompt Construction

Add `build_epic_role_prompt(epic, role, task_instruction)` that mirrors `build_role_prompt()`:

- Maps epic role names to agent files: `epic_analyst.md`, `epic_designer.md`, `epic_reviewer.md`, `epic_planner.md`
- Builds project context from `project_config.json` (same domain as ticket workflow)
- Loads skills via the same `get_role_skills` / `load_skill_contents` functions, keyed on role name

If `project_config.json` doesn't define epic role skills, the function falls back gracefully (no skill block injected).

---

## Epic Review Fix Context

`build_epic_review_fix_context(epic)` mirrors `build_fix_context(ticket)`:

- Reads `epic_review.json`
- Extracts issues bucketed by severity, using `area` instead of `file`
- Writes `fix/epic_review_fix_context.md`
- Archives current `epic_review.json` to `fix/previous_epic_review.json` before the fix round

---

## `epic_next_action(epic)` Routing Logic

```
if epic_analysis.md is missing        → "epic-analysis-prepare"
if epic_analysis_prompt exists but
  epic_analysis.md missing            → "epic-analysis-complete"
if epic_design.md is missing          → "epic-design-prepare"
if epic_design_prompt exists but
  epic_design.md missing              → "epic-design-complete"
if review decision in {request_changes, block}:
    if current_stage == "epic_design_fix_prepare"  → "epic-design-fix-complete"
    else                                            → "epic-design-fix-prepare"
if epic_review.json is missing        → "epic-review-prepare"
if current_stage == "epic_review_prepare"          → "epic-review-complete"
if review decision == "approve":
    if epic_story_map.md is missing   → "epic-breakdown-prepare"
    if current_stage == "epic_breakdown_prepare" → "epic-breakdown-complete"
    if epic_story_map.md exists       → "done"
→ "done"
```

---

## `epic_next_step()` and WezTerm Integration

Reuse `spawn_claude_wezterm(prompt_path, cwd)` unchanged.

Add epic prepare steps to a separate `_EPIC_PREPARE_STEP_PROMPT` dict:

```python
_EPIC_PREPARE_STEP_PROMPT = {
    "epic-analysis-prepare": epic_analysis_prompt_path,
    "epic-design-prepare": epic_design_prompt_path,
    "epic-design-fix-prepare": epic_design_fix_prompt_path,
    "epic-review-prepare": epic_review_prompt_path,
    "epic-breakdown-prepare": epic_breakdown_prompt_path,
}
```

---

## Breakdown Output Verification

`epic_breakdown_complete(epic)` must verify:
1. `epic_story_map.md` is non-empty
2. At least one file exists in `breakdown/tickets/`

Use `list(epic_tickets_dir(epic).glob("*.md"))` to enumerate ticket files.

---

## Parser Commands

New subcommands to register:

```
epic-init <EPIC> "<requirement>"
epic-analysis-prepare <EPIC>
epic-analysis-complete <EPIC>
epic-design-prepare <EPIC>
epic-design-complete <EPIC>
epic-review-prepare <EPIC>
epic-review-complete <EPIC>
epic-design-fix-prepare <EPIC>
epic-design-fix-complete <EPIC>
epic-breakdown-prepare <EPIC>
epic-breakdown-complete <EPIC>
epic-status <EPIC>
epic-next <EPIC> [--run] [--run-auto]
```

---

## Risks and Trade-offs

| Risk | Mitigation |
|------|------------|
| `ai_run.py` grows large | Keep all epic code in a clearly separated section with a `# ── EPIC WORKFLOW ──` header comment |
| Status functions duplicated | Refactor status helpers to accept a path argument instead of deriving from ticket ID — shared by both flows |
| `project_config.json` missing epic skill mappings | Gracefully skip skill injection when keys are absent |
| Breakdown produces zero ticket files | `epic_breakdown_complete` raises an error if `tickets/` is empty, preventing silent failures |
| Agent files for epic roles written after this ticket | Agent files already exist; no dependency on additional work |
