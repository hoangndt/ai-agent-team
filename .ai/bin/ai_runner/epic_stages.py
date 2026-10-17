"""Epic prepare/complete handlers, ADR distill and ticket generation."""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

from .paths import (
    adr_distill_prompt_path, epic_analysis_path, epic_analysis_prompt_path,
    epic_breakdown_prompt_path, epic_design_fix_prompt_path, epic_design_path,
    epic_design_prompt_path, epic_input_file, epic_path, epic_review_fix_context_path,
    epic_review_prompt_path, epic_review_report_path, epic_story_map_path,
    epic_story_status_path, epic_tickets_dir, input_file, now,
    previous_epic_review_path,
)
from .state import (
    complete_epic_stage, ensure_base_dirs, ensure_epic_dirs,
    ensure_non_empty_epic_files, fail_epic_stage, init_epic_status, init_ticket,
    load_epic_status, load_project_config, read, save_epic_status, set_epic_artifact,
    set_epic_runner, update_epic_stage, write,
)
from .context import file_ref_list, get_epic_domains, next_adr_id, vault_root
from .prompts import build_epic_review_fix_context, build_epic_role_prompt


# ── EPIC WORKFLOW ──────────────────────────────────────────────────────────────

def epic_init(epic: str, requirement: str, domains: str = "") -> None:
    ensure_base_dirs()
    config = load_project_config()

    resolved_domains = [d.strip() for d in domains.split(",") if d.strip()]
    if not resolved_domains:
        resolved_domains = list(config.get("domains", {}).keys())

    valid_domains = set(config.get("domains", {}).keys())
    if resolved_domains:
        # Validate regardless of whether any valid domains exist in the config.
        # An empty config means there are no valid domains, so any explicit request
        # for a specific domain must be rejected with a clear error.
        unknown = [d for d in resolved_domains if d not in valid_domains]
        if unknown:
            valid_label = ", ".join(sorted(valid_domains)) if valid_domains else "(none defined in project_config.json)"
            print(
                f"[ERROR] Unknown domain(s): {', '.join(unknown)}. "
                f"Valid domains: {valid_label}"
            )
            sys.exit(1)

    ensure_epic_dirs(epic)

    write(epic_input_file(epic), requirement.strip() + "\n")
    save_epic_status(epic, init_epic_status(epic, resolved_domains))
    set_epic_artifact(epic, "epic_input", epic_input_file(epic))
    print(f"[OK] Initialized epic {epic} at {epic_path(epic)} (domains={resolved_domains})")


def epic_analysis_prepare(epic: str) -> None:
    update_epic_stage(epic, "epic_analysis_prepare")
    set_epic_runner(epic, "epic-analysis-prepare")

    ensure_non_empty_epic_files([epic_input_file(epic)], "epic_analysis_prepare", epic)

    task_instruction = f"""Work inside the current repository.

Read these files:
{file_ref_list([epic_input_file(epic)])}

Analyze the epic requirement and write a comprehensive analysis directly to:
- {epic_analysis_path(epic).as_posix()}

The analysis must include:
1. Problem statement — restate the epic in your own words
2. Goals — primary objectives and success metrics
3. Scope — what is in and out of scope
4. Key stakeholders or user personas affected
5. High-level solution areas — major functional areas to address
6. Open questions — unknowns that must be resolved before design

Important:
- Write the analysis directly to the file above.
- Do not reply in chat with the final content.
- Keep the analysis concise but thorough.
"""
    prompt = build_epic_role_prompt(epic, "epic_analyst", task_instruction)
    write(epic_analysis_prompt_path(epic), prompt)
    set_epic_artifact(epic, "epic_analysis_prompt", epic_analysis_prompt_path(epic))
    complete_epic_stage(epic, "epic_analysis_prepare", "Generated epic analysis prompt.")
    print(f"[OK] Wrote {epic_analysis_prompt_path(epic)}")
    print(
        "[NEXT] Paste this prompt into Claude. Let it write epic_analysis.md, then run epic-next --run."
    )


def epic_analysis_complete(epic: str) -> None:
    update_epic_stage(epic, "epic_analysis_complete")
    set_epic_runner(epic, "epic-analysis-complete")

    ensure_non_empty_epic_files([epic_analysis_path(epic)], "epic_analysis_complete", epic)
    set_epic_artifact(epic, "epic_analysis", epic_analysis_path(epic))

    complete_epic_stage(epic, "epic_analysis_complete", "Epic analysis verified.")
    print(f"[OK] Epic analysis verified for {epic}")


def epic_design_prepare(epic: str) -> None:
    update_epic_stage(epic, "epic_design_prepare")
    set_epic_runner(epic, "epic-design-prepare")

    required_inputs = [epic_input_file(epic), epic_analysis_path(epic)]
    ensure_non_empty_epic_files(required_inputs, "epic_design_prepare", epic)

    task_instruction = f"""Work inside the current repository.

Read these files:
{file_ref_list(required_inputs)}

Produce a detailed epic design document and write it directly to:
- {epic_design_path(epic).as_posix()}

The design must include:
1. Solution overview — high-level approach and architecture
2. Key design decisions — rationale for major choices
3. Component breakdown — major components or services involved
4. Data flow — how information moves through the system
5. Integration points — external systems or APIs affected
6. Risks and trade-offs — known risks and mitigation strategies
7. Out of scope — explicit exclusions from this epic

Important:
- Write the design directly to the file above.
- Do not reply in chat with the final content.
"""
    prompt = build_epic_role_prompt(epic, "epic_designer", task_instruction)
    write(epic_design_prompt_path(epic), prompt)
    set_epic_artifact(epic, "epic_design_prompt", epic_design_prompt_path(epic))
    complete_epic_stage(epic, "epic_design_prepare", "Generated epic design prompt.")
    print(f"[OK] Wrote {epic_design_prompt_path(epic)}")
    print(
        "[NEXT] Paste this prompt into Claude. Let it write epic_design.md, then run epic-next --run."
    )


def epic_design_complete(epic: str) -> None:
    update_epic_stage(epic, "epic_design_complete")
    set_epic_runner(epic, "epic-design-complete")

    ensure_non_empty_epic_files([epic_design_path(epic)], "epic_design_complete", epic)
    set_epic_artifact(epic, "epic_design", epic_design_path(epic))

    complete_epic_stage(epic, "epic_design_complete", "Epic design verified.")
    print(f"[OK] Epic design verified for {epic}")


def epic_review_prepare(epic: str) -> None:
    update_epic_stage(epic, "epic_review_prepare")
    set_epic_runner(epic, "epic-review-prepare")

    required_inputs = [
        epic_input_file(epic),
        epic_analysis_path(epic),
        epic_design_path(epic),
    ]
    ensure_non_empty_epic_files(required_inputs, "epic_review_prepare", epic)

    followup_mode = (
        previous_epic_review_path(epic).exists()
        and read(previous_epic_review_path(epic)).strip()
    )

    followup_block = ""
    if followup_mode:
        extra_files = [previous_epic_review_path(epic)]
        if (
            epic_review_fix_context_path(epic).exists()
            and read(epic_review_fix_context_path(epic)).strip()
        ):
            extra_files.append(epic_review_fix_context_path(epic))

        followup_block = f"""

This is a follow-up review after a designer fix round.

Also read these files:
{file_ref_list(extra_files)}

Follow-up review rules:
- Verify whether previous review issues were addressed in the updated design
- Do not repeat already fixed issues
- Keep only unresolved previous issues
- Add any new issues introduced by the revisions
- In the summary, explicitly state whether previous high-severity issues were resolved
"""

    task_instruction = f"""Work inside the current repository.

Read these files:
{file_ref_list(required_inputs)}{followup_block}

Review the epic design for completeness, feasibility, and alignment with the stated requirements.

Write valid JSON only directly to:
- {epic_review_report_path(epic).as_posix()}

Required JSON format:
{{
  "decision": "approve|request_changes|block",
  "issues": [
    {{
      "severity": "high|medium|low",
      "area": "...",
      "message": "..."
    }}
  ],
  "summary": "..."
}}

Review rules:
- List high severity issues first
- Tie findings to feasibility, completeness, or alignment with requirements
- Prefer concrete, actionable comments

Important:
- Do not reply in chat with the final JSON.
- Write the JSON directly to the target file.
"""
    prompt = build_epic_role_prompt(epic, "epic_reviewer", task_instruction)
    write(epic_review_prompt_path(epic), prompt)
    set_epic_artifact(epic, "epic_review_prompt", epic_review_prompt_path(epic))
    complete_epic_stage(epic, "epic_review_prepare", "Generated epic review prompt.")
    print(f"[OK] Wrote {epic_review_prompt_path(epic)}")
    print(
        "[NEXT] Paste this prompt into Claude. Let it write epic_review.json, then run epic-next --run."
    )


def epic_review_complete(epic: str) -> None:
    update_epic_stage(epic, "epic_review_complete")
    set_epic_runner(epic, "epic-review-complete")

    ensure_non_empty_epic_files([epic_review_report_path(epic)], "epic_review_complete", epic)

    parsed = json.loads(read(epic_review_report_path(epic)))
    write(
        epic_review_report_path(epic),
        json.dumps(parsed, indent=2, ensure_ascii=False) + "\n",
    )
    set_epic_artifact(epic, "epic_review_report", epic_review_report_path(epic))

    build_epic_review_fix_context(epic)

    decision = parsed.get("decision", "unknown")
    complete_epic_stage(epic, "epic_review_complete", f"Epic reviewer decision: {decision}")
    print(f"[OK] Epic review verified for {epic} ({decision})")

    # Deliberately NOT auto-calling adr_distill_prepare here (unlike qa_complete's
    # ticket-side distill_prepare call): epic_next_action (below) already returns
    # "adr-distill-prepare" as its own distinct step once decision == "approve" and
    # no ADR-distill prompt exists yet. Calling it synchronously here would advance
    # current_stage to "adr_distill_prepare" before the router/autoflow ever sees
    # "adr-distill-prepare" as the next step, so --auto-flow/--run-auto could never
    # spawn a WezTerm pane for it. epic_next_action drives this stage instead.


# ── EPIC ADR DISTILL WORKFLOW (write path) ──────────────────────────────────────
# Epic-level ADR lifecycle, auto-triggered via epic_next_action's routing once a
# review is approved (see the "adr-distill-prepare" branch below) rather than
# synchronously inside epic_review_complete, so --auto-flow/--run-auto still see
# "adr-distill-prepare" as its own step and spawn a WezTerm pane for it.
# Mirrors the ticket-side distill prepare/complete shape. ADR selection is
# filename-id-based rather than trusting each ADR's own `epic:` field.

_ADR_VALID_STATUSES = {"proposed", "accepted", "superseded"}


def _parse_adr_frontmatter(text: str) -> Dict[str, object]:
    """Minimal stdlib-only frontmatter parser for ADR files (VC-1: no yaml import).

    Parses the leading '---' block into key: value pairs. A bracketed value (e.g.
    `tickets: []` or `tickets: [US-001, US-002]`) is parsed as a list; everything
    else is a stripped string. Returns {} if there is no leading '---' block.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}

    fm: Dict[str, object] = {}
    pending_list_key: Optional[str] = None
    for raw_line in lines[1:end]:
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        # Multi-line YAML list continuation, e.g. `tickets:\n  - US-001`.
        stripped = line.strip()
        if pending_list_key is not None and stripped.startswith("- "):
            item = stripped[2:].strip().strip('"').strip("'")
            existing = fm.get(pending_list_key)
            fm[pending_list_key] = (existing if isinstance(existing, list) else []) + [item]
            continue
        pending_list_key = None
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            fm[key] = (
                [v.strip().strip('"').strip("'") for v in inner.split(",") if v.strip()]
                if inner
                else []
            )
        elif not value:
            # Could be a multi-line list continuation on the following lines,
            # or a genuinely empty scalar field — resolved once we see the next line.
            fm[key] = []
            pending_list_key = key
        else:
            fm[key] = value.strip('"').strip("'")
    return fm


def _adr_frontmatter_errors(fm: Dict[str, object]) -> List[str]:
    errors = []
    for field in ("id", "status", "epic", "tickets"):
        if field not in fm:
            errors.append(f"missing '{field}'")
    if "status" in fm and fm["status"] not in _ADR_VALID_STATUSES:
        errors.append(
            f"invalid status '{fm['status']}' (must be one of {sorted(_ADR_VALID_STATUSES)})"
        )
    return errors


def _epic_stage_completed_in_history(epic: str, stage: str) -> bool:
    history = load_epic_status(epic).get("history", [])
    return any(h.get("stage") == stage and h.get("status") == "done" for h in history)


def adr_distill_prepare(epic: str) -> None:
    root = vault_root()
    if root is None:
        # Vault-disabled contract: no-op without mutating current_stage or
        # artifacts, mirroring ticket-side distill_prepare.
        print(f"[SKIP] Vault disabled; adr_distill_prepare no-op for {epic}")
        return

    update_epic_stage(epic, "adr_distill_prepare")
    set_epic_runner(epic, "adr-distill-prepare")

    # Persist the start id on epic status *before* building the prompt, so
    # adr_distill_complete can select ADRs by filename id even if the agent
    # writes a malformed/missing `epic:` field.
    start_id = next_adr_id()
    s = load_epic_status(epic)
    s["adr_distill_start_id"] = start_id
    s["updated_at"] = now()
    save_epic_status(epic, s)

    adr_id = f"ADR-{start_id}"

    task_instruction = f"""Work inside the current repository.

This epic's design review was approved. Distill its architecture decisions into
the vault's ADR log (epic-approval mode).

Read these files:
{file_ref_list([epic_design_path(epic)])}

Next free ADR id for this epic: {adr_id}

Write one or more `proposed` ADR files under
`.ai/vault/architecture/decisions/`, one per distinct decision worth recording
from epic_design.md's Risks / Trade-offs section (§7) and its alternatives
considered. Use {adr_id} for the first ADR; increment sequentially for any
additional ADRs from this epic. If nothing in this epic warrants a recorded
decision, write no ADR files and say so in chat (this is a valid outcome).

Each ADR file must follow `ADR-NNN-template.md`'s frontmatter shape exactly:
- `id`: the ADR id (e.g. {adr_id})
- `status: proposed`
- `epic: {epic}`
- `tickets: []`
- `supersedes:` (empty unless this decision supersedes an existing ADR)

Also mark the module-doc entry (or entries) this decision will affect in the
relevant `.ai/vault/architecture/modules/<domain>.md` file `status: planned`,
linking back to the ADR id.

Prune signal:
- While you're in the decisions directory, if you notice any existing
  `proposed` ADR with an empty `tickets:` list, print a `[PRUNE]` line naming
  that ADR id and its associated `planned` module entry.

Important:
- Do not run git add/commit/push — leave all edits as working-tree changes.
- Write the ADR/module files directly. Do not reply in chat with their final content.
"""
    prompt = build_epic_role_prompt(epic, "distiller", task_instruction)
    write(adr_distill_prompt_path(epic), prompt)
    set_epic_artifact(epic, "adr_distill_prompt", adr_distill_prompt_path(epic))
    complete_epic_stage(epic, "adr_distill_prepare", "Generated ADR distill prompt.")
    print(f"[OK] Wrote {adr_distill_prompt_path(epic)}")
    print(
        "[NEXT] Paste this prompt into Claude. Let it write the ADR file(s), then run epic-next --run."
    )


def adr_distill_complete(epic: str) -> None:
    update_epic_stage(epic, "adr_distill_complete")
    set_epic_runner(epic, "adr-distill-complete")

    root = vault_root()
    if root is None:
        # Defensive only — epic_next_action's ADR-distill block is itself guarded
        # on vault_root(), but a manual CLI invocation shouldn't crash.
        complete_epic_stage(epic, "adr_distill_complete", "Vault disabled; nothing to verify.")
        print(f"[OK] Vault disabled; adr_distill_complete no-op for {epic}")
        return

    start_id_raw = load_epic_status(epic).get("adr_distill_start_id")
    if not start_id_raw:
        complete_epic_stage(
            epic, "adr_distill_complete", "No adr_distill_start_id recorded; nothing to verify."
        )
        print(f"[OK] No ADR distill start id recorded for {epic}; nothing to verify.")
        return
    start_id = int(start_id_raw)

    # Selection is by filename id (>= start_id), not by each file's own `epic:`
    # field, so a missing/malformed `epic:` cannot hide an ADR from verification.
    # Uses the same `^ADR-(\d{3})` regex next_adr_id() scans with, so ADR-NNN-template.md is
    # skipped the same way.
    decisions_dir = root / "architecture" / "decisions"
    selected: List[Path] = []
    if decisions_dir.is_dir():
        for path in sorted(decisions_dir.iterdir()):
            if not path.is_file():
                continue
            match = re.match(r"^ADR-(\d{3})", path.name)
            if match and int(match.group(1)) >= start_id:
                selected.append(path)

    if not selected:
        # Zero epic-linked ADRs is pass-with-note, not a failure.
        complete_epic_stage(
            epic, "adr_distill_complete", "No new ADRs written for this epic; pass-with-note."
        )
        print(f"[OK] No new ADRs for {epic}; pass-with-note.")
        return

    errors: List[str] = []
    pruned: List[str] = []
    for path in selected:
        fm = _parse_adr_frontmatter(read(path))
        field_errors = _adr_frontmatter_errors(fm)
        if field_errors:
            errors.append(f"{path.name}: {'; '.join(field_errors)}")
            continue
        if fm.get("status") == "proposed" and not fm.get("tickets"):
            pruned.append(str(fm.get("id", path.name)))

    for adr_id in pruned:
        print(f"[PRUNE] {adr_id} is proposed with no implementing tickets yet.")

    if errors:
        msg = "Malformed ADR frontmatter:\n" + "\n".join(f"  {e}" for e in errors)
        fail_epic_stage(epic, "adr_distill_complete", msg)
        print(f"[BLOCK] {msg}")
        raise ValueError(msg)

    note = f"{len(selected)} ADR(s) verified"
    if pruned:
        note += f"; {len(pruned)} pending tickets"
    complete_epic_stage(epic, "adr_distill_complete", note)
    print(f"[OK] ADR distill verified for {epic} ({len(selected)} ADR(s))")


def epic_design_fix_prepare(epic: str) -> None:
    update_epic_stage(epic, "epic_design_fix_prepare")
    set_epic_runner(epic, "epic-design-fix-prepare")

    required_inputs = [
        epic_input_file(epic),
        epic_analysis_path(epic),
        epic_design_path(epic),
    ]
    ensure_non_empty_epic_files(required_inputs, "epic_design_fix_prepare", epic)

    if not epic_review_report_path(epic).exists() or not read(epic_review_report_path(epic)).strip():
        fail_epic_stage(epic, "epic_design_fix_prepare", "No epic_review.json found")
        raise FileNotFoundError("No epic_review.json found for epic design fix mode")

    # Archive the review report (fix context was already written by epic_review_complete)
    archived_review = previous_epic_review_path(epic)
    write(archived_review, read(epic_review_report_path(epic)))
    epic_review_report_path(epic).unlink(missing_ok=True)
    set_epic_artifact(epic, "previous_epic_review", archived_review)

    fix_ctx = epic_review_fix_context_path(epic)
    extra_paths: List[Path] = [archived_review]
    if fix_ctx.exists():
        extra_paths.append(fix_ctx)

    task_instruction = f"""Work inside the current repository.

Read these files:
{file_ref_list(required_inputs + extra_paths)}

Your task is to revise the epic design to address all review findings.

Fix rules:
- Resolve all high severity issues identified in the review
- Address medium and low severity issues where feasible
- Do NOT redesign from scratch — revise the existing design document
- Preserve sections that were not flagged as problematic
- Be explicit in the design about how each major issue was addressed

Overwrite the epic design file with the corrected version:
- {epic_design_path(epic).as_posix()}

Important:
- Write the updated design directly to the file above.
- Do not reply in chat with the final content.
"""
    prompt = build_epic_role_prompt(epic, "epic_designer", task_instruction)
    write(epic_design_fix_prompt_path(epic), prompt)
    set_epic_artifact(epic, "epic_design_fix_prompt", epic_design_fix_prompt_path(epic))
    complete_epic_stage(epic, "epic_design_fix_prepare", "Generated epic design fix prompt.")
    print(f"[OK] Wrote {epic_design_fix_prompt_path(epic)}")
    print(
        "[NEXT] Paste this prompt into Claude. Let it update epic_design.md, then run epic-next --run."
    )


def epic_design_fix_complete(epic: str) -> None:
    update_epic_stage(epic, "epic_design_fix_complete")
    set_epic_runner(epic, "epic-design-fix-complete")

    ensure_non_empty_epic_files([epic_design_path(epic)], "epic_design_fix_complete", epic)
    set_epic_artifact(epic, "epic_design", epic_design_path(epic))

    complete_epic_stage(epic, "epic_design_fix_complete", "Epic design fix verified.")
    print(f"[OK] Epic design fix verified for {epic}")


def epic_breakdown_prepare(epic: str) -> None:
    update_epic_stage(epic, "epic_breakdown_prepare")
    set_epic_runner(epic, "epic-breakdown-prepare")

    required_inputs = [
        epic_input_file(epic),
        epic_analysis_path(epic),
        epic_design_path(epic),
    ]
    ensure_non_empty_epic_files(required_inputs, "epic_breakdown_prepare", epic)

    if not epic_review_report_path(epic).exists() or not read(epic_review_report_path(epic)).strip():
        fail_epic_stage(epic, "epic_breakdown_prepare", "No approved epic_review.json found")
        raise FileNotFoundError(
            "No epic_review.json found. Run epic-review-complete first."
        )

    try:
        review = json.loads(read(epic_review_report_path(epic)))
    except Exception:
        fail_epic_stage(epic, "epic_breakdown_prepare", "epic_review.json is not valid JSON")
        raise

    if review.get("decision") != "approve":
        fail_epic_stage(
            epic,
            "epic_breakdown_prepare",
            f"Review decision is '{review.get('decision')}', not 'approve'",
        )
        raise ValueError(
            f"Cannot run breakdown: review decision is '{review.get('decision')}'. Must be 'approve'."
        )

    tickets_dir = epic_tickets_dir(epic)

    task_instruction = f"""Work inside the current repository.

Read these files:
{file_ref_list(required_inputs)}

Break the epic down into a structured set of user stories and tickets.

Write the story map directly to:
- {epic_story_map_path(epic).as_posix()}

Write individual ticket files directly to:
- {tickets_dir.as_posix()}/<EPIC-ID>-<STORY-ID>-<short-slug>.md
  Example: {tickets_dir.as_posix()}/EPIC-001-US-001-add-schema.md

Write the story status tracker directly to:
- {epic_story_status_path(epic).as_posix()}

## Story Map Requirements

1. List all user stories in priority order
2. Group stories by theme or functional area
3. Note dependencies between stories
4. If any quality concerns are detected (overlap, oversize, vague AC), add a `## Quality Notes` section listing each issue with: ticket ID, concern type, and severity (high/medium/low)

## Ticket File Requirements

- Filename format: `<EPIC-ID>-<STORY-ID>-<slug>.md` (e.g. `EPIC-001-US-001-add-cli-commands.md`)
- Each ticket file MUST contain all of the following sections using exact `##` level headers:

  ```
  ## Summary
  ## Goal
  ## Scope
  ## Out of Scope
  ## Acceptance Criteria
  ## Dependencies
  ## Suggested Order
  ## Domain
  ## Notes
  ## References
  ```

- `## Goal` — must be non-empty; state what this ticket achieves
- `## Scope` — must be non-empty; list exactly what is included
- `## Acceptance Criteria` — must contain at least two concrete, testable criteria (not placeholders like "works correctly")
- `## Domain` — must be set to one of the configured project domains
- `## References` — must contain links to the epic analysis, design, and story status files:
  ```
  - [Epic Analysis]({epic_analysis_path(epic).as_posix()})
  - [Epic Design]({epic_design_path(epic).as_posix()})
  - [Epic Story Status]({epic_story_status_path(epic).as_posix()})
  ```

## Quality Requirements

Before writing output, apply the self-review checklist:
- Every ticket is estimable within 1–3 days
- No two tickets share overlapping scope (same files, same API endpoints, same data model fields)
- Every ticket has at least two concrete, testable Acceptance Criteria
- `## Goal` and `## Scope` are distinct and non-empty in every ticket
- No ticket title is a vague action phrase (e.g. "Improve X", "Refactor Y")
- Do NOT produce god tickets (covering multiple features) or layer-split tickets without independent user value

## Story Status Tracker Requirements

The `epic_story_status.md` file must follow this format exactly:

```
# Epic Story Status — <EPIC-ID> <Epic Title>

Epic: <one-liner>
Last updated: <YYYY-MM-DD> (initial breakdown)

---

## Status Key

| Symbol | Meaning |
|--------|---------|
| ✅ | Done — merged to branch |
| 🔄 | In progress |
| ⬜ | Not started |

---

## <Workstream Name>

| ID | Title | Status | Branch | Report |
|----|-------|--------|--------|--------|
| US-001 | <title> | ⬜ | — | — |

---

## Progress Summary

- Done: 0 / <total>
- In progress: 0 / <total>
- Not started: <total> / <total>
```

Rules:
- One section per workstream, matching the story map groupings
- All tickets start with status `⬜`, Branch `—`, Report `—`
- Progress Summary totals must be accurate
- Story IDs in the table match the ticket file prefixes (e.g. `US-001`)

## Important

- Write the story map, all ticket files, and the story status tracker directly.
- Do not reply in chat with the final content.
- Create at least one ticket file in {tickets_dir.as_posix()}.
"""
    prompt = build_epic_role_prompt(epic, "epic_planner", task_instruction)
    write(epic_breakdown_prompt_path(epic), prompt)
    set_epic_artifact(epic, "epic_breakdown_prompt", epic_breakdown_prompt_path(epic))
    complete_epic_stage(epic, "epic_breakdown_prepare", "Generated epic breakdown prompt.")
    print(f"[OK] Wrote {epic_breakdown_prompt_path(epic)}")
    print(
        "[NEXT] Paste this prompt into Claude. Let it write epic_story_map.md and ticket files, then run epic-next --run."
    )


def epic_breakdown_complete(epic: str) -> None:
    update_epic_stage(epic, "epic_breakdown_complete")
    set_epic_runner(epic, "epic-breakdown-complete")

    ensure_non_empty_epic_files(
        [epic_story_map_path(epic), epic_story_status_path(epic)],
        "epic_breakdown_complete",
        epic,
    )

    ticket_files = list(epic_tickets_dir(epic).glob("*.md"))
    if not ticket_files:
        fail_epic_stage(
            epic,
            "epic_breakdown_complete",
            "No ticket files found in breakdown/tickets/",
        )
        raise FileNotFoundError(
            f"No ticket files found in {epic_tickets_dir(epic).as_posix()}. "
            "The epic_planner must write at least one *.md file there."
        )

    # Validate ticket filenames follow <EPIC-ID>-<STORY-ID>-<slug>.md format
    ticket_name_re = re.compile(r"^EPIC-\d+-[A-Z]+-\d+-.+\.md$", re.IGNORECASE)
    bad_names = [tf.name for tf in ticket_files if not ticket_name_re.match(tf.name)]
    if bad_names:
        msg = (
            "Ticket file(s) do not follow the required naming format "
            "`<EPIC-ID>-<STORY-ID>-<slug>.md` (e.g. EPIC-001-US-001-add-schema.md):\n"
            + "\n".join(f"  {n}" for n in bad_names)
        )
        fail_epic_stage(epic, "epic_breakdown_complete", msg)
        raise ValueError(msg)

    # Verify each ticket file has a non-empty ## Domain section
    initialized_domains = set(get_epic_domains(epic))
    domain_errors = []
    for tf in ticket_files:
        content = tf.read_text(encoding="utf-8")
        # Find ## Domain header and extract the value on the next non-blank line
        domain_value = ""
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if line.strip().lower().startswith("## domain"):
                # collect lines after the header until the next ## heading or EOF
                for j in range(i + 1, len(lines)):
                    stripped = lines[j].strip()
                    if stripped.startswith("#"):
                        break
                    if stripped:
                        domain_value = stripped
                        break
                break
        if not domain_value:
            domain_errors.append(f"  {tf.name}: missing or empty '## Domain' section")
        elif initialized_domains and domain_value not in initialized_domains:
            domain_errors.append(
                f"  {tf.name}: '## Domain' value '{domain_value}' is not one of the "
                f"initialized domains ({', '.join(sorted(initialized_domains))})"
            )

    if domain_errors:
        msg = "Ticket file(s) failed ## Domain validation:\n" + "\n".join(domain_errors)
        fail_epic_stage(epic, "epic_breakdown_complete", msg)
        raise ValueError(msg)

    # Validate ## Goal, ## Scope, ## Acceptance Criteria are non-empty in each ticket
    def _section_is_non_empty(lines: list, header: str) -> bool:
        """Return True if the named ## section exists and has at least one non-blank line."""
        header_lower = header.lower()
        in_section = False
        for line in lines:
            if line.strip().lower() == header_lower:
                in_section = True
                continue
            if in_section:
                if line.strip().startswith("##"):
                    return False  # reached next section without content
                if line.strip():
                    return True  # found non-blank content
        return False

    section_errors = []
    required_sections = ["## Goal", "## Scope", "## Acceptance Criteria", "## References"]
    for tf in ticket_files:
        lines = tf.read_text(encoding="utf-8").splitlines()
        for section in required_sections:
            if not _section_is_non_empty(lines, section):
                section_errors.append(f"  {tf.name}: missing or empty '{section}' section")

    if section_errors:
        msg = "Ticket file(s) failed section validation:\n" + "\n".join(section_errors)
        fail_epic_stage(epic, "epic_breakdown_complete", msg)
        raise ValueError(msg)

    set_epic_artifact(epic, "epic_story_map", epic_story_map_path(epic))
    set_epic_artifact(epic, "epic_story_status", epic_story_status_path(epic))
    set_epic_artifact(epic, "epic_tickets_dir", epic_tickets_dir(epic))

    complete_epic_stage(
        epic,
        "epic_breakdown_complete",
        f"Epic breakdown verified. {len(ticket_files)} ticket(s) found.",
    )
    print(f"[OK] Epic breakdown verified for {epic} ({len(ticket_files)} ticket(s))")


def epic_generate_tickets(epic: str, init_dirs: bool = False) -> None:
    epic_root = epic_path(epic)
    if not epic_root.exists():
        print(f"[ERROR] Epic '{epic}' not found at {epic_root.as_posix()}", file=sys.stderr)
        sys.exit(1)

    tickets_dir = epic_tickets_dir(epic)
    ticket_files = sorted(tickets_dir.glob("*.md")) if tickets_dir.exists() else []
    if not ticket_files:
        print(
            f"[ERROR] No ticket files found in {tickets_dir.as_posix()}. "
            "Run epic-breakdown-complete first.",
            file=sys.stderr,
        )
        sys.exit(1)

    created = skipped = errors = 0
    for tf in ticket_files:
        ticket_id = tf.stem
        run_ticket = f"{epic}-{ticket_id}"
        target = input_file(run_ticket)

        if target.exists() and target.read_text(encoding="utf-8").strip():
            print(f"[SKIP] {ticket_id}")
            skipped += 1
            continue

        try:
            content = tf.read_text(encoding="utf-8")
            init_ticket(run_ticket, content)
            print(f"[OK] {ticket_id}")
            created += 1
        except Exception as e:
            print(f"[ERROR] {ticket_id}: {e}")
            errors += 1

    print(f"Created: {created}  Skipped: {skipped}  Errors: {errors}")
