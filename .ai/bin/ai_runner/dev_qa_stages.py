"""Developer, reviewer and QA prepare/complete handlers."""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from .paths import (
    acceptance_criteria_path, assumptions_path, design_note_path, dev_fix_prompt_path,
    dev_prompt_path, fix_dir, implementation_report_path, previous_review_report_path,
    qa_prompt_path, qa_report_path, review_fix_context_path, review_prompt_path,
    review_report_path, task_spec_path,
)
from .state import (
    complete_stage, fail_stage, get_base_branch, read, set_artifact, set_runner,
    update_stage, write,
)
from .context import ensure_non_empty_files, ensure_section_present, file_ref_list
from .prompts import build_fix_context, build_qa_fix_context, build_role_prompt


def _epic_story_status_block(ticket: str) -> str:
    """Return epic story status update instructions if ticket matches EPIC-NNN-STORY-NNN pattern."""
    match = re.match(r"^(EPIC-\d+)-([A-Z]+-\d+)-", ticket, re.IGNORECASE)
    if not match:
        return ""
    epic_prefix = match.group(1).upper()
    story_id = match.group(2).upper()
    report_link = f".ai/runs/{ticket}/dev/implementation_report.md"
    return f"""
## Epic story status update

Ticket `{ticket}` belongs to epic `{epic_prefix}`, story `{story_id}`.

After committing:
1. Find the epic folder: look in `.ai/epics/` for a directory whose name starts with `{epic_prefix.lower()}` (e.g. `{epic_prefix.lower()}-mvp`).
2. Open `.ai/epics/<epic-folder>/breakdown/epic_story_status.md`.
3. Find the table row for `{story_id}` and update:
   - Status column: `✅`
   - Branch column: `` `{ticket}` ``
   - Report column: `[report]({report_link})`
4. Update the "Last updated" header line (e.g. `Last updated: YYYY-MM-DD ({story_id} done)`).
5. Recalculate the Progress Summary counts at the bottom.
"""


def dev_prepare(ticket: str) -> None:
    update_stage(ticket, "dev_prepare")
    set_runner(ticket, "dev-prepare")

    required_inputs = [
        task_spec_path(ticket),
        design_note_path(ticket),
        acceptance_criteria_path(ticket),
        assumptions_path(ticket),
    ]
    ensure_non_empty_files(required_inputs, "dev_prepare", ticket)

    base_branch = get_base_branch()

    task_instruction = f"""Work inside the current repository.

Read these files:
{file_ref_list(required_inputs)}

Implement the required code changes in the repository.

Git context:
- The current working branch contains the ticket changes
- If useful, compare the current branch against {base_branch} to understand the full ticket delta

Then write your implementation report directly to:
- {implementation_report_path(ticket).as_posix()}

The report must include:
1. Summary of changes
2. Files modified
3. Key decisions
4. Assumptions followed
5. Commands/tests you ran

## Git commit (required after writing the report)

1. Run `git branch --show-current` to check the current branch.
2. If on `{base_branch}`: create a new branch: `git checkout -b {ticket.lower()}`
3. Stage all changes except for files inside `.ai` folder
4. Commit: `git commit -m "feat({ticket}): <one-line summary>"`
{_epic_story_status_block(ticket)}
Important:
- Make the code changes directly in the repo.
- Write the report directly to the file above.
- Keep the report concise and factual.
- Always commit after writing the report.
"""
    prompt = build_role_prompt(ticket, "developer", task_instruction)
    write(dev_prompt_path(ticket), prompt)
    set_artifact(ticket, "dev_prompt", dev_prompt_path(ticket))
    complete_stage(ticket, "dev_prepare", "Generated dev prompt.")
    print(f"[OK] Wrote {dev_prompt_path(ticket)}")
    print(
        "[NEXT] Paste this prompt into Claude/Copilot. Let it change code and write implementation_report.md, then run next --run."
    )


def archive_file(ticket: str, source: Path, archive_name: str) -> Optional[Path]:
    if not source.exists() or not read(source).strip():
        return None

    archived = fix_dir(ticket) / archive_name
    write(archived, read(source))
    source.unlink(missing_ok=True)
    return archived


def archive_quality_reports_for_fix(ticket: str) -> Dict[str, Optional[Path]]:
    review_archived = archive_file(
        ticket,
        review_report_path(ticket),
        "previous_review_report.json",
    )
    qa_archived = archive_file(
        ticket,
        qa_report_path(ticket),
        "previous_qa_report.json",
    )

    result = {
        "review": review_archived,
        "qa": qa_archived,
    }

    if review_archived:
        set_artifact(ticket, "previous_review_report", review_archived)
    if qa_archived:
        set_artifact(ticket, "previous_qa_report", qa_archived)

    return result


def dev_fix_prepare(ticket: str) -> None:
    update_stage(ticket, "dev_fix_prepare")
    set_runner(ticket, "dev-fix-prepare")

    core_inputs = [
        task_spec_path(ticket),
        design_note_path(ticket),
        acceptance_criteria_path(ticket),
        assumptions_path(ticket),
    ]
    ensure_non_empty_files(core_inputs, "dev_fix_prepare", ticket)

    review_exists = (
        review_report_path(ticket).exists() and read(review_report_path(ticket)).strip()
    )
    qa_exists = qa_report_path(ticket).exists() and read(qa_report_path(ticket)).strip()

    if not review_exists and not qa_exists:
        fail_stage(
            ticket,
            "dev_fix_prepare",
            "No review_report.json or qa_report.json found for fix mode",
        )
        raise FileNotFoundError(
            "No review_report.json or qa_report.json found for dev fix mode"
        )

    extra_paths: List[Path] = []
    issue_sources: List[str] = []

    if review_exists:
        fix_ctx = build_fix_context(ticket)
        if fix_ctx:
            extra_paths.append(fix_ctx)
        issue_sources.append("Review")

    if qa_exists:
        qa_fix_ctx = build_qa_fix_context(ticket)
        if qa_fix_ctx:
            extra_paths.append(qa_fix_ctx)
        issue_sources.append("QA")

    archived = archive_quality_reports_for_fix(ticket)

    archived_paths: List[Path] = []
    if archived.get("review"):
        archived_paths.append(archived["review"])
    if archived.get("qa"):
        archived_paths.append(archived["qa"])

    base_branch = get_base_branch()
    source_label = (
        " and/or ".join(issue_sources) if issue_sources else "Review and/or QA"
    )

    task_instruction = f"""Work inside the current repository.

Read these files:
{file_ref_list(core_inputs + archived_paths + extra_paths)}

Your task is to fix all unresolved quality findings reported by: {source_label}.

Fixing rules:
- Resolve all high severity review issues
- Resolve QA failures that indicate real code defects
- Add automated tests for missing scenarios identified by QA where appropriate
- Address delivery gaps required by acceptance criteria when feasible
- Do NOT re-implement the feature from scratch
- Do NOT introduce unrelated changes
- Prefer the minimal correct fix for each issue
- Preserve existing behavior unless it is explicitly identified as wrong

Git context:
- The current working branch contains the ticket changes
- If useful, compare the current branch against {base_branch}
- Focus on fixing the effective branch delta, not only uncommitted changes

Apply code changes directly in the repository.

Then update the implementation report by **appending** a new fix-round section to the existing file (do NOT overwrite or erase previous rounds):
- {implementation_report_path(ticket).as_posix()}

Steps:
1. Read the current content of implementation_report.md to determine how many fix rounds exist already.
2. Append a new section at the bottom using this heading (increment the round number accordingly):
   `## Fix Round N — <short description>`
3. The new section must include:
   - Summary of changes made in this round
   - Files modified
   - Key decisions
   - Commands/tests you ran
   - Review Issues Addressed (reference each issue explicitly)
   - QA Issues Addressed (reference each issue explicitly)

## Git commit (required after appending the fix-round section)

1. Run `git branch --show-current` to confirm you are on the ticket branch (not `{base_branch}`).
2. If somehow on `{base_branch}`: create the branch first: `git checkout -b {ticket.lower()}`
3. Stage all changes except for files inside `.ai` folder
4. Commit: `git commit -m "fix({ticket}): <one-line summary of fix round>"`
{_epic_story_status_block(ticket)}
Important:
- Preserve all existing content in implementation_report.md — only append.
- Make the code changes directly in the repo.
- Be explicit about how each critical issue was fixed.
- If QA identified missing tests, add them when feasible and report them clearly.
- Always commit after appending the fix-round section.
"""
    prompt = build_role_prompt(ticket, "developer", task_instruction)
    write(dev_fix_prompt_path(ticket), prompt)
    set_artifact(ticket, "dev_fix_prompt", dev_fix_prompt_path(ticket))
    complete_stage(ticket, "dev_fix_prepare", "Generated dev-fix prompt.")
    print(f"[OK] Wrote {dev_fix_prompt_path(ticket)}")
    print(
        "[NEXT] Paste this prompt into Claude/Copilot. Let it fix the issues and append a new fix-round section to implementation_report.md, then run next --run."
    )


def dev_complete(ticket: str) -> None:
    update_stage(ticket, "dev_complete")
    set_runner(ticket, "dev-complete")

    ensure_non_empty_files([implementation_report_path(ticket)], "dev_complete", ticket)
    ensure_section_present(
        implementation_report_path(ticket),
        "## Architecture Impact",
        "dev_complete",
        ticket,
    )
    set_artifact(ticket, "implementation_report", implementation_report_path(ticket))

    complete_stage(ticket, "dev_complete", "Implementation report verified.")
    print(f"[OK] Dev files verified for {ticket}")


def dev_fix_complete(ticket: str) -> None:
    update_stage(ticket, "dev_fix_complete")
    set_runner(ticket, "dev-fix-complete")

    ensure_non_empty_files(
        [implementation_report_path(ticket)], "dev_fix_complete", ticket
    )
    ensure_section_present(
        implementation_report_path(ticket),
        "## Architecture Impact",
        "dev_fix_complete",
        ticket,
    )
    set_artifact(ticket, "implementation_report", implementation_report_path(ticket))

    complete_stage(ticket, "dev_fix_complete", "Fix implementation verified.")
    print(f"[OK] Dev fix verified for {ticket}")


def review_prepare(ticket: str) -> None:
    update_stage(ticket, "review_prepare")
    set_runner(ticket, "review-prepare")

    required_inputs = [
        task_spec_path(ticket),
        acceptance_criteria_path(ticket),
        assumptions_path(ticket),
        implementation_report_path(ticket),
    ]
    ensure_non_empty_files(required_inputs, "review_prepare", ticket)

    base_branch = get_base_branch()
    followup_mode = (
        previous_review_report_path(ticket).exists()
        and read(previous_review_report_path(ticket)).strip()
    )

    followup_block = ""
    if followup_mode:
        extra_files = [previous_review_report_path(ticket)]
        if (
            review_fix_context_path(ticket).exists()
            and read(review_fix_context_path(ticket)).strip()
        ):
            extra_files.append(review_fix_context_path(ticket))

        followup_block = f"""

This is a follow-up review after a developer fix round.

Also read these files:
{file_ref_list(extra_files)}

Follow-up review rules:
- Verify whether previous review issues were fixed
- Do not repeat already fixed issues
- Keep only unresolved previous issues
- Add any new issues introduced by the fixes
- In the summary, explicitly state whether previous high-severity issues were resolved
- Treat this as a verification pass, not a blind fresh review
"""

    task_instruction = f"""Work inside the current repository.

Read these files:
{file_ref_list(required_inputs)}{followup_block}

Git review context:
- Compare the current branch against {base_branch}
- Review the effective ticket delta, including committed changes
- Use git diff, git log, and changed files as needed
- Do not limit review to uncommitted changes

Write valid JSON only directly to:
- {review_report_path(ticket).as_posix()}

Required JSON format:
{{
  "decision": "approve|request_changes|block",
  "issues": [
    {{
      "severity": "high|medium|low",
      "file": "...",
      "message": "..."
    }}
  ],
  "summary": "..."
}}

Review rules:
- List high severity issues first
- Tie findings to correctness, acceptance criteria, maintainability, or production risk
- Prefer concrete, actionable comments

Important:
- Do not reply in chat with the final JSON.
- Write the JSON directly to the target file.
"""
    prompt = build_role_prompt(ticket, "reviewer", task_instruction)
    write(review_prompt_path(ticket), prompt)
    set_artifact(ticket, "review_prompt", review_prompt_path(ticket))
    complete_stage(ticket, "review_prepare", "Generated review prompt.")
    print(f"[OK] Wrote {review_prompt_path(ticket)}")
    print(
        "[NEXT] Paste this prompt into Claude/Copilot. Let it write review_report.json directly, then run next --run."
    )


def review_complete(ticket: str) -> None:
    update_stage(ticket, "review_complete")
    set_runner(ticket, "review-complete")

    ensure_non_empty_files([review_report_path(ticket)], "review_complete", ticket)

    parsed = json.loads(read(review_report_path(ticket)))
    write(
        review_report_path(ticket),
        json.dumps(parsed, indent=2, ensure_ascii=False) + "\n",
    )
    set_artifact(ticket, "review_report", review_report_path(ticket))

    build_fix_context(ticket)

    decision = parsed.get("decision", "unknown")
    complete_stage(ticket, "review_complete", f"Reviewer decision: {decision}")
    print(f"[OK] Review file verified for {ticket} ({decision})")


def qa_prepare(ticket: str) -> None:
    update_stage(ticket, "qa_prepare")
    set_runner(ticket, "qa-prepare")

    required_inputs = [
        acceptance_criteria_path(ticket),
        assumptions_path(ticket),
        implementation_report_path(ticket),
    ]
    ensure_non_empty_files(required_inputs, "qa_prepare", ticket)

    base_branch = get_base_branch()

    task_instruction = f"""Work inside the current repository.

Read these files:
{file_ref_list(required_inputs)}

Git QA context:
- Compare the current branch against {base_branch}
- Evaluate the effective ticket delta, including committed changes
- Use git diff, git log, and changed files as needed
- Check likely regression areas impacted by this branch

Write valid JSON only directly to:
- {qa_report_path(ticket).as_posix()}

Required JSON format:
{{
  "decision": "pass|fail",
  "missing_tests": [],
  "risks": [],
  "summary": "..."
}}

Important:
- Do not reply in chat with the final JSON.
- Write the JSON directly to the target file.
"""
    prompt = build_role_prompt(ticket, "qa", task_instruction)
    write(qa_prompt_path(ticket), prompt)
    set_artifact(ticket, "qa_prompt", qa_prompt_path(ticket))
    complete_stage(ticket, "qa_prepare", "Generated QA prompt.")
    print(f"[OK] Wrote {qa_prompt_path(ticket)}")
    print(
        "[NEXT] Paste this prompt into Claude/Copilot. Let it write qa_report.json directly, then run next --run."
    )


def qa_complete(ticket: str) -> None:
    update_stage(ticket, "qa_complete")
    set_runner(ticket, "qa-complete")

    ensure_non_empty_files([qa_report_path(ticket)], "qa_complete", ticket)

    parsed = json.loads(read(qa_report_path(ticket)))
    write(
        qa_report_path(ticket), json.dumps(parsed, indent=2, ensure_ascii=False) + "\n"
    )
    set_artifact(ticket, "qa_report", qa_report_path(ticket))

    build_qa_fix_context(ticket)

    decision = parsed.get("decision", "unknown")
    complete_stage(ticket, "qa_complete", f"QA decision: {decision}")
    print(f"[OK] QA file verified for {ticket} ({decision})")

    # Deliberately NOT auto-calling distill_prepare here: next_action (in
    # its QA-pass branch) already returns "distill-prepare" as its own distinct
    # step once decision == "pass" and no distill prompt exists yet. Calling it
    # synchronously here would advance current_stage to "distill_prepare" before
    # the router/autoflow ever sees "distill-prepare" as the next step, so
    # --auto-flow/--run-auto could never spawn a WezTerm pane for it. The epic side
    # does the same for adr_distill_prepare in epic_review_complete.
