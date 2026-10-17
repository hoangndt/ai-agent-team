"""Architect, architect-review and architect-fix prepare/complete handlers."""

import json
import sys
from pathlib import Path
from typing import List

from .paths import (
    acceptance_criteria_path, architect_fix_context_path, architect_fix_prompt_path,
    architect_prompt_path, architect_review_prompt_path, architect_review_report_path,
    assumptions_path, design_note_path, fix_dir, input_file,
    previous_architect_review_path, task_spec_path,
)
from .state import (
    complete_stage, fail_stage, read, set_artifact, set_runner, update_stage, write,
)
from .context import ensure_non_empty_files, file_ref_list
from .prompts import build_architect_fix_context, build_role_prompt


def architect_prepare(ticket: str) -> None:
    update_stage(ticket, "architect_prepare")
    set_runner(ticket, "architect-prepare")

    task_instruction = f"""Work inside the current repository.

Read these files:
{file_ref_list([input_file(ticket)])}

You may inspect other relevant repository files if needed.

Do NOT reply in chat with the actual result.
Write the outputs directly to these files:

- {task_spec_path(ticket).as_posix()}
- {design_note_path(ticket).as_posix()}
- {acceptance_criteria_path(ticket).as_posix()}
- {assumptions_path(ticket).as_posix()}

File requirements:
- task_spec.md: Restate the task in technical terms, define scope and out-of-scope, and list impacted modules/files if known
- design_note.md: Proposed implementation approach, main flow, data/API considerations, risks and trade-offs
- acceptance_criteria.md: Clear, testable acceptance criteria including success cases, validation cases, and failure cases
- assumptions.md: Explicit assumptions, unknowns, and ambiguities that could affect implementation

Important:
- Write each file directly.
- Do not create extra output files unless necessary.
- Keep content concise but precise.
"""
    prompt = build_role_prompt(ticket, "architect", task_instruction)
    write(architect_prompt_path(ticket), prompt)
    set_artifact(ticket, "architect_prompt", architect_prompt_path(ticket))
    complete_stage(ticket, "architect_prepare", "Generated architect prompt.")
    print(f"[OK] Wrote {architect_prompt_path(ticket)}")
    print(
        "[NEXT] Paste this prompt into Claude/Copilot. Let it write the 4 files directly, then run next --run."
    )


def architect_complete(ticket: str) -> None:
    update_stage(ticket, "architect_complete")
    set_runner(ticket, "architect-complete")

    required = [
        task_spec_path(ticket),
        design_note_path(ticket),
        acceptance_criteria_path(ticket),
        assumptions_path(ticket),
    ]
    ensure_non_empty_files(required, "architect_complete", ticket)

    set_artifact(ticket, "task_spec", task_spec_path(ticket))
    set_artifact(ticket, "design_note", design_note_path(ticket))
    set_artifact(ticket, "acceptance_criteria", acceptance_criteria_path(ticket))
    set_artifact(ticket, "assumptions", assumptions_path(ticket))

    complete_stage(ticket, "architect_complete", "Architect files verified.")
    print(f"[OK] Architect files verified for {ticket}")


def architect_review_prepare(ticket: str) -> None:
    update_stage(ticket, "architect_review_prepare")
    set_runner(ticket, "architect-review-prepare")

    required_inputs = [
        task_spec_path(ticket),
        design_note_path(ticket),
        acceptance_criteria_path(ticket),
        assumptions_path(ticket),
    ]
    ensure_non_empty_files(required_inputs, "architect_review_prepare", ticket)

    followup_mode = (
        previous_architect_review_path(ticket).exists()
        and read(previous_architect_review_path(ticket)).strip()
    )

    followup_block = ""
    if followup_mode:
        extra_files = [previous_architect_review_path(ticket)]
        if (
            architect_fix_context_path(ticket).exists()
            and read(architect_fix_context_path(ticket)).strip()
        ):
            extra_files.append(architect_fix_context_path(ticket))

        followup_block = f"""

This is a follow-up review after an architect fix round.

Also read these files:
{file_ref_list(extra_files)}

Follow-up review rules:
- Verify whether previous review issues were addressed in the updated design artifacts
- Do not repeat already fixed issues
- Keep only unresolved previous issues
- Add any new issues introduced by the revisions
- In the summary, explicitly state whether previous high-severity issues were resolved
"""

    task_instruction = f"""Work inside the current repository.

Read these files:
{file_ref_list(required_inputs)}{followup_block}

Review the architect design artifacts for correctness, completeness, and alignment with the requirement.

Write valid JSON only directly to:
- {architect_review_report_path(ticket).as_posix()}

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

Review focus areas:
- Design correctness: Is the proposed approach sound and implementable?
- Scope completeness: Does the task_spec cover everything needed? Are out-of-scope items clear?
- Acceptance criteria quality: Are criteria testable and unambiguous? Are failure cases covered?
- Assumption validity: Are assumptions reasonable? Are unknowns clearly called out?
- Missing edge cases: Are there scenarios the design doesn't address?
- Over/under-specification: Is the design too vague or too prescriptive?

Decision guidance:
- approve: Design is solid, criteria are testable, assumptions are reasonable, no important gaps
- request_changes: There are meaningful gaps but they are fixable within the current approach
- block: The design has severe flaws, dangerous assumptions, or is fundamentally misaligned with the requirement

Rules:
- List high severity issues first
- Tie findings to correctness, completeness, or feasibility
- Prefer concrete, actionable comments

Important:
- Do not reply in chat with the final JSON.
- Write the JSON directly to the target file.
"""
    prompt = build_role_prompt(ticket, "architect_reviewer", task_instruction)
    write(architect_review_prompt_path(ticket), prompt)
    set_artifact(ticket, "architect_review_prompt", architect_review_prompt_path(ticket))
    complete_stage(ticket, "architect_review_prepare", "Generated architect review prompt.")
    print(f"[OK] Wrote {architect_review_prompt_path(ticket)}")
    print(
        "[NEXT] Paste this prompt into Claude/Copilot. Let it write architect_review.json directly, then run next --run."
    )


def architect_review_complete(ticket: str) -> None:
    update_stage(ticket, "architect_review_complete")
    set_runner(ticket, "architect-review-complete")

    ensure_non_empty_files(
        [architect_review_report_path(ticket)], "architect_review_complete", ticket
    )

    try:
        parsed = json.loads(read(architect_review_report_path(ticket)))
    except json.JSONDecodeError as exc:
        fail_stage(ticket, "architect_review_complete", f"Invalid JSON in architect_review.json: {exc}")
        raise

    write(
        architect_review_report_path(ticket),
        json.dumps(parsed, indent=2, ensure_ascii=False) + "\n",
    )
    set_artifact(ticket, "architect_review_report", architect_review_report_path(ticket))

    decision = parsed.get("decision", "unknown")

    if decision not in {"approve", "request_changes", "block"}:
        print(
            f"[WARN] Unexpected architect review decision: '{decision}'. "
            "Treating as request_changes (safe default). Fix the JSON if this is wrong.",
            file=sys.stderr,
        )

    if decision in {"request_changes", "block"}:
        # Archive review and build fix context
        fix_dir(ticket).mkdir(parents=True, exist_ok=True)
        archived = previous_architect_review_path(ticket)
        write(archived, read(architect_review_report_path(ticket)))
        set_artifact(ticket, "previous_architect_review", archived)
        build_architect_fix_context(ticket)
        complete_stage(
            ticket, "architect_review_complete", f"Architect reviewer decision: {decision} — fix loop required"
        )
        print(f"[OK] Architect review verified for {ticket} ({decision})")
        print("[FIX] Decision requires changes. Run next --run to start architect fix loop.")
    else:
        complete_stage(ticket, "architect_review_complete", f"Architect reviewer decision: {decision}")
        print(f"[OK] Architect review verified for {ticket} ({decision})")


def architect_fix_prepare(ticket: str) -> None:
    update_stage(ticket, "architect_fix_prepare")
    set_runner(ticket, "architect-fix-prepare")

    required_inputs = [
        input_file(ticket),
        task_spec_path(ticket),
        design_note_path(ticket),
        acceptance_criteria_path(ticket),
        assumptions_path(ticket),
    ]
    ensure_non_empty_files(required_inputs, "architect_fix_prepare", ticket)

    fix_ctx = architect_fix_context_path(ticket)
    extra_paths: List[Path] = []
    if fix_ctx.exists() and read(fix_ctx).strip():
        extra_paths.append(fix_ctx)

    prev_review = previous_architect_review_path(ticket)
    if prev_review.exists() and read(prev_review).strip():
        extra_paths.append(prev_review)

    task_instruction = f"""Work inside the current repository.

Read these files:
{file_ref_list(required_inputs + extra_paths)}

Your task is to revise the architect design artifacts to address all review findings.

Fix rules:
- Resolve all high severity issues identified in the review
- Address medium and low severity issues where feasible
- Do NOT redesign from scratch — revise the existing design artifacts
- Preserve sections that were not flagged as problematic
- Be explicit in the artifacts about how each major issue was addressed
- Do NOT write production code in this step

Overwrite the design artifacts with the corrected versions:
- {task_spec_path(ticket).as_posix()}
- {design_note_path(ticket).as_posix()}
- {acceptance_criteria_path(ticket).as_posix()}
- {assumptions_path(ticket).as_posix()}

Important:
- Write the updated artifacts directly to the files above.
- Do not reply in chat with the final content.
- Only modify files needed to address the review findings.
"""
    prompt = build_role_prompt(ticket, "architect", task_instruction)
    write(architect_fix_prompt_path(ticket), prompt)
    set_artifact(ticket, "architect_fix_prompt", architect_fix_prompt_path(ticket))
    complete_stage(ticket, "architect_fix_prepare", "Generated architect fix prompt.")
    print(f"[OK] Wrote {architect_fix_prompt_path(ticket)}")
    print(
        "[NEXT] Paste this prompt into Claude/Copilot. Let it update the design artifacts, then run next --run."
    )


def architect_fix_complete(ticket: str) -> None:
    update_stage(ticket, "architect_fix_complete")
    set_runner(ticket, "architect-fix-complete")

    required = [
        task_spec_path(ticket),
        design_note_path(ticket),
        acceptance_criteria_path(ticket),
        assumptions_path(ticket),
    ]
    ensure_non_empty_files(required, "architect_fix_complete", ticket)

    # Clear previous architect review so next_action routes to architect-review-prepare
    architect_review_report_path(ticket).unlink(missing_ok=True)

    complete_stage(ticket, "architect_fix_complete", "Architect fix artifacts verified.")
    print(f"[OK] Architect fix verified for {ticket}")
