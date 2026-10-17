"""Review and fix gates for the epic analysis and breakdown phases.

Both phases share one implementation driven by `_PHASES`; the public functions are thin
wrappers so the CLI, routing tables and the `ai_run` facade can reference them by name.
"""

import json
from pathlib import Path
from typing import Dict, List

from .paths import (
    epic_analysis_fix_prompt_path, epic_analysis_path, epic_analysis_review_fix_context_path,
    epic_analysis_review_prompt_path, epic_analysis_review_report_path,
    epic_breakdown_fix_prompt_path, epic_breakdown_review_fix_context_path,
    epic_breakdown_review_prompt_path, epic_breakdown_review_report_path, epic_design_path,
    epic_input_file, epic_story_map_path, epic_story_status_path, epic_tickets_dir,
    previous_epic_analysis_review_path, previous_epic_breakdown_review_path,
)
from .state import (
    complete_epic_stage, ensure_non_empty_epic_files, fail_epic_stage, read,
    set_epic_artifact, set_epic_runner, update_epic_stage, write,
)
from .context import file_ref_list
from .epic_breakdown_checks import seeded_ticket_runs, validate_breakdown
from .prompts import build_epic_review_fix_context, build_epic_role_prompt
from .epic_stages import breakdown_ticket_rules

_DECISIONS = ("approve", "request_changes", "block")

_PHASES: Dict[str, Dict] = {
    "analysis": {
        "stage": "epic_analysis",
        "step": "epic-analysis",
        "label": "analysis",
        "reviewer": "epic_analysis_reviewer",
        "fixer": "epic_analyst",
        "report": epic_analysis_review_report_path,
        "prompt": epic_analysis_review_prompt_path,
        "fix_prompt": epic_analysis_fix_prompt_path,
        "previous": previous_epic_analysis_review_path,
        "fix_context": epic_analysis_review_fix_context_path,
    },
    "breakdown": {
        "stage": "epic_breakdown",
        "step": "epic-breakdown",
        "label": "breakdown",
        "reviewer": "epic_breakdown_reviewer",
        "fixer": "epic_planner",
        "report": epic_breakdown_review_report_path,
        "prompt": epic_breakdown_review_prompt_path,
        "fix_prompt": epic_breakdown_fix_prompt_path,
        "previous": previous_epic_breakdown_review_path,
        "fix_context": epic_breakdown_review_fix_context_path,
    },
}


def _inputs(epic: str, phase: str) -> List[Path]:
    required = [epic_input_file(epic), epic_analysis_path(epic)]
    if phase == "breakdown":
        required += [epic_design_path(epic), epic_story_map_path(epic), epic_story_status_path(epic)]
    return required


def _ticket_files(epic: str) -> List[Path]:
    tickets_dir = epic_tickets_dir(epic)
    return sorted(tickets_dir.glob("*.md")) if tickets_dir.exists() else []


def _require_tickets(epic: str, stage: str) -> List[Path]:
    tickets = _ticket_files(epic)
    if not tickets:
        fail_epic_stage(epic, stage, "No ticket files found in breakdown/tickets/")
        raise FileNotFoundError(
            f"No ticket files found in {epic_tickets_dir(epic).as_posix()}."
        )
    return tickets


def _warn_seeded(epic: str) -> List[str]:
    seeded = seeded_ticket_runs(epic)
    if seeded:
        print(
            f"[WARN] {len(seeded)} ticket run(s) already seeded for {epic}: "
            + ", ".join(seeded)
        )
    return seeded


def _review_prepare(epic: str, phase: str) -> None:
    cfg = _PHASES[phase]
    stage = f"{cfg['stage']}_review_prepare"
    update_epic_stage(epic, stage)
    set_epic_runner(epic, f"{cfg['step']}-review-prepare")

    required = _inputs(epic, phase)
    tickets: List[Path] = []
    if phase == "breakdown":
        tickets = _require_tickets(epic, stage)
    ensure_non_empty_epic_files(required + tickets, stage, epic)
    if phase == "breakdown":
        _warn_seeded(epic)

    previous = cfg["previous"](epic)
    followup_block = ""
    if previous.exists() and read(previous).strip():
        extra = [previous]
        fix_ctx = cfg["fix_context"](epic)
        if fix_ctx.exists() and read(fix_ctx).strip():
            extra.append(fix_ctx)
        followup_block = f"""

This is a follow-up review after a fix round.

Also read these files:
{file_ref_list(extra)}

Follow-up review rules:
- Verify whether previous review issues were addressed in the updated {cfg['label']}
- Do not repeat already fixed issues
- Keep only unresolved previous issues
- Add any new issues introduced by the revisions
- In the summary, explicitly state whether previous high-severity issues were resolved
"""

    if phase == "analysis":
        subject = "Review the epic analysis for completeness, clarity, and traceability to the stated requirement."
        rules = """- Check that every analysis section is present and concrete
- Check that success criteria are measurable and scope/out-of-scope are unambiguous
- Flag open questions that would block design as high severity
- Do not review or propose a design"""
    else:
        subject = (
            "Review the epic breakdown (story map, story status tracker, and every ticket file) "
            "against the analysis and design."
        )
        rules = """- Check that every design component and goal is covered by a ticket
- Flag per-domain or per-layer ticket sets that fragment one feature (too fine) and tickets that bundle several unrelated verifiable outcomes (too coarse); judge qualitatively, never by ticket count or duration
- Check that multi-domain tickets have a Domain Checklist per domain and a runnable Verification section
- Check dependency order for cycles, overlap between tickets, and consistency of story map, status tracker, and ticket IDs"""

    task_instruction = f"""Work inside the current repository.

Read these files:
{file_ref_list(required + tickets)}{followup_block}

{subject}

Write valid JSON only directly to:
- {cfg['report'](epic).as_posix()}

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
- Use `approve` only when there are no high severity issues
{rules}
- Prefer concrete, actionable comments

Important:
- Do not reply in chat with the final JSON.
- Write the JSON directly to the target file.
"""
    prompt = build_epic_role_prompt(epic, cfg["reviewer"], task_instruction)
    write(cfg["prompt"](epic), prompt)
    set_epic_artifact(epic, f"{cfg['stage']}_review_prompt", cfg["prompt"](epic))
    complete_epic_stage(epic, stage, f"Generated epic {cfg['label']} review prompt.")
    print(f"[OK] Wrote {cfg['prompt'](epic)}")
    print(
        f"[NEXT] Paste this prompt into Claude. Let it write {cfg['report'](epic).name}, "
        "then run epic-next --run."
    )


def _review_complete(epic: str, phase: str) -> None:
    cfg = _PHASES[phase]
    stage = f"{cfg['stage']}_review_complete"
    update_epic_stage(epic, stage)
    set_epic_runner(epic, f"{cfg['step']}-review-complete")

    report = cfg["report"](epic)
    ensure_non_empty_epic_files([report], stage, epic)

    try:
        parsed = json.loads(read(report))
    except Exception as exc:
        fail_epic_stage(epic, stage, f"{report.name} is not valid JSON: {exc}")
        raise
    decision = parsed.get("decision") if isinstance(parsed, dict) else None
    if decision not in _DECISIONS:
        msg = (
            f"{report.name} decision {decision!r} is invalid "
            f"(must be one of {', '.join(_DECISIONS)})"
        )
        fail_epic_stage(epic, stage, msg)
        raise ValueError(msg)

    write(report, json.dumps(parsed, indent=2, ensure_ascii=False) + "\n")
    set_epic_artifact(epic, f"{cfg['stage']}_review_report", report)
    build_epic_review_fix_context(epic, phase)

    complete_epic_stage(epic, stage, f"Epic {cfg['label']} reviewer decision: {decision}")
    print(f"[OK] Epic {cfg['label']} review verified for {epic} ({decision})")


def _fix_prepare(epic: str, phase: str) -> None:
    cfg = _PHASES[phase]
    stage = f"{cfg['stage']}_fix_prepare"
    update_epic_stage(epic, stage)
    set_epic_runner(epic, f"{cfg['step']}-fix-prepare")

    report = cfg["report"](epic)
    if not report.exists() or not read(report).strip():
        fail_epic_stage(epic, stage, f"No {report.name} found")
        raise FileNotFoundError(f"No {report.name} found for epic {cfg['label']} fix mode")

    required = _inputs(epic, phase)
    tickets = _require_tickets(epic, stage) if phase == "breakdown" else []
    ensure_non_empty_epic_files(required + tickets, stage, epic)
    seeded = _warn_seeded(epic) if phase == "breakdown" else []

    archived = cfg["previous"](epic)
    write(archived, read(report))
    report.unlink(missing_ok=True)
    set_epic_artifact(epic, f"previous_{cfg['stage']}_review", archived)

    extra: List[Path] = [archived]
    fix_ctx = cfg["fix_context"](epic)
    if fix_ctx.exists():
        extra.append(fix_ctx)

    if phase == "analysis":
        rules = f"""Fix rules:
- Resolve all high severity issues identified in the review
- Address medium and low severity issues where feasible
- Do NOT rewrite from scratch; revise the existing analysis and keep sections that were not flagged
- Questions you cannot resolve stay under "Assumptions / Unknowns" and must also be listed in your final QUESTIONS

Overwrite the epic analysis file with the corrected version:
- {epic_analysis_path(epic).as_posix()}
"""
        done_hint = "update epic_analysis.md"
    else:
        seeded_block = ""
        if seeded:
            seeded_block = (
                "\nTicket runs already seeded for this epic (do not rename or delete these "
                "tickets silently; if a finding requires changing one, state it in your final "
                "QUESTIONS so the operator decides):\n"
                + "\n".join(f"- {run}" for run in seeded)
                + "\n"
            )
        rules = f"""Fix rules:
- Resolve all high severity issues identified in the review
- Address medium and low severity issues where feasible
- Revise the story map, the story status tracker, and the ticket files in place; do NOT regenerate the breakdown from scratch
- When tickets are merged or split, delete the obsolete ticket files and keep `epic_story_status.md` IDs and Progress Summary totals consistent with the ticket files
- Fixed tickets must satisfy the same ticket format and sizing rules as the initial breakdown (below)
{seeded_block}
Files to update:
- {epic_story_map_path(epic).as_posix()}
- {epic_story_status_path(epic).as_posix()}
- {epic_tickets_dir(epic).as_posix()}/<EPIC-ID>-<STORY-ID>-<short-slug>.md

{breakdown_ticket_rules(epic)}"""
        done_hint = "update the story map, status tracker and tickets"

    task_instruction = f"""Work inside the current repository.

Read these files:
{file_ref_list(required + tickets + extra)}

Your task is to revise the epic {cfg['label']} to address all review findings.

{rules}
Important:
- Write the updated files directly.
- Do not reply in chat with the final content.
"""
    prompt = build_epic_role_prompt(epic, cfg["fixer"], task_instruction)
    write(cfg["fix_prompt"](epic), prompt)
    set_epic_artifact(epic, f"{cfg['stage']}_fix_prompt", cfg["fix_prompt"](epic))
    complete_epic_stage(epic, stage, f"Generated epic {cfg['label']} fix prompt.")
    print(f"[OK] Wrote {cfg['fix_prompt'](epic)}")
    print(f"[NEXT] Paste this prompt into Claude. Let it {done_hint}, then run epic-next --run.")


def _fix_complete(epic: str, phase: str) -> None:
    cfg = _PHASES[phase]
    stage = f"{cfg['stage']}_fix_complete"
    update_epic_stage(epic, stage)
    set_epic_runner(epic, f"{cfg['step']}-fix-complete")

    if phase == "analysis":
        ensure_non_empty_epic_files([epic_analysis_path(epic)], stage, epic)
        set_epic_artifact(epic, "epic_analysis", epic_analysis_path(epic))
    else:
        validate_breakdown(epic, stage)
        set_epic_artifact(epic, "epic_story_map", epic_story_map_path(epic))
        set_epic_artifact(epic, "epic_story_status", epic_story_status_path(epic))
        set_epic_artifact(epic, "epic_tickets_dir", epic_tickets_dir(epic))

    complete_epic_stage(epic, stage, f"Epic {cfg['label']} fix verified.")
    print(f"[OK] Epic {cfg['label']} fix verified for {epic}")


def epic_analysis_review_prepare(epic: str) -> None:
    _review_prepare(epic, "analysis")


def epic_analysis_review_complete(epic: str) -> None:
    _review_complete(epic, "analysis")


def epic_analysis_fix_prepare(epic: str) -> None:
    _fix_prepare(epic, "analysis")


def epic_analysis_fix_complete(epic: str) -> None:
    _fix_complete(epic, "analysis")


def epic_breakdown_review_prepare(epic: str) -> None:
    _review_prepare(epic, "breakdown")


def epic_breakdown_review_complete(epic: str) -> None:
    _review_complete(epic, "breakdown")


def epic_breakdown_fix_prepare(epic: str) -> None:
    _fix_prepare(epic, "breakdown")


def epic_breakdown_fix_complete(epic: str) -> None:
    _fix_complete(epic, "breakdown")
