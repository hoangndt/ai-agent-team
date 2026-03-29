#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

BASE = Path(".ai")
RUNS = BASE / "runs"
AGENTS = BASE / "agents"


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def run_path(ticket: str) -> Path:
    return RUNS / ticket


def status_file(ticket: str) -> Path:
    return run_path(ticket) / "status.json"


def project_config_path() -> Path:
    return BASE / "project_config.json"


def input_dir(ticket: str) -> Path:
    return run_path(ticket) / "input"


def architect_dir(ticket: str) -> Path:
    return run_path(ticket) / "architect"


def dev_dir(ticket: str) -> Path:
    return run_path(ticket) / "dev"


def fix_dir(ticket: str) -> Path:
    return run_path(ticket) / "fix"


def review_dir(ticket: str) -> Path:
    return run_path(ticket) / "review"


def qa_dir(ticket: str) -> Path:
    return run_path(ticket) / "qa"


def input_file(ticket: str) -> Path:
    return input_dir(ticket) / "input.md"


def architect_prompt_path(ticket: str) -> Path:
    return architect_dir(ticket) / "architect_prompt.md"


def task_spec_path(ticket: str) -> Path:
    return architect_dir(ticket) / "task_spec.md"


def design_note_path(ticket: str) -> Path:
    return architect_dir(ticket) / "design_note.md"


def acceptance_criteria_path(ticket: str) -> Path:
    return architect_dir(ticket) / "acceptance_criteria.md"


def assumptions_path(ticket: str) -> Path:
    return architect_dir(ticket) / "assumptions.md"


def dev_prompt_path(ticket: str) -> Path:
    return dev_dir(ticket) / "dev_prompt.md"


def implementation_report_path(ticket: str) -> Path:
    return dev_dir(ticket) / "implementation_report.md"


def dev_fix_prompt_path(ticket: str) -> Path:
    return fix_dir(ticket) / "dev_fix_prompt.md"


def review_fix_context_path(ticket: str) -> Path:
    return fix_dir(ticket) / "review_fix_context.md"


def qa_fix_context_path(ticket: str) -> Path:
    return fix_dir(ticket) / "qa_fix_context.md"


def previous_review_report_path(ticket: str) -> Path:
    return fix_dir(ticket) / "previous_review_report.json"


def previous_qa_report_path(ticket: str) -> Path:
    return fix_dir(ticket) / "previous_qa_report.json"


def review_prompt_path(ticket: str) -> Path:
    return review_dir(ticket) / "review_prompt.md"


def review_report_path(ticket: str) -> Path:
    return review_dir(ticket) / "review_report.json"


def qa_prompt_path(ticket: str) -> Path:
    return qa_dir(ticket) / "qa_prompt.md"


def qa_report_path(ticket: str) -> Path:
    return qa_dir(ticket) / "qa_report.json"


def read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def ensure_base_dirs() -> None:
    for path in [BASE, RUNS, AGENTS, BASE / "templates", BASE / "bin"]:
        path.mkdir(parents=True, exist_ok=True)


def ensure_ticket_dirs(ticket: str) -> None:
    for path in [
        run_path(ticket),
        input_dir(ticket),
        architect_dir(ticket),
        dev_dir(ticket),
        fix_dir(ticket),
        review_dir(ticket),
        qa_dir(ticket),
    ]:
        path.mkdir(parents=True, exist_ok=True)


def load_status(ticket: str) -> Dict:
    sf = status_file(ticket)
    if not sf.exists():
        raise FileNotFoundError(
            f"Status file not found for ticket '{ticket}'. Run init first."
        )
    return json.loads(sf.read_text(encoding="utf-8"))


def save_status(ticket: str, data: Dict) -> None:
    write(status_file(ticket), json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def load_project_config() -> Dict:
    path = project_config_path()
    if not path.exists():
        raise FileNotFoundError("Missing .ai/project_config.json")
    return json.loads(path.read_text(encoding="utf-8"))


def get_base_branch() -> str:
    cfg = load_project_config()
    return cfg.get("git", {}).get("base_branch", "main")


def init_status(ticket: str, domain: str) -> Dict:
    ts = now()
    return {
        "ticket": ticket,
        "domain": domain,
        "current_stage": "init",
        "state": "ready",
        "updated_at": ts,
        "artifacts": {},
        "history": [{"stage": "init", "status": "done", "time": ts}],
        "runner": {"mode": "file_referenced_prompts", "last_command": None},
    }


def add_history(ticket: str, stage: str, status: str, note: str = "") -> None:
    s = load_status(ticket)
    s.setdefault("history", []).append(
        {"stage": stage, "status": status, "time": now(), "note": note}
    )
    s["updated_at"] = now()
    save_status(ticket, s)


def update_stage(ticket: str, stage: str, state: str = "running") -> None:
    s = load_status(ticket)
    s["current_stage"] = stage
    s["state"] = state
    s["updated_at"] = now()
    save_status(ticket, s)


def complete_stage(ticket: str, stage: str, note: str = "") -> None:
    s = load_status(ticket)
    s["current_stage"] = stage
    s["state"] = "ready"
    s["updated_at"] = now()
    save_status(ticket, s)
    add_history(ticket, stage, "done", note)


def fail_stage(ticket: str, stage: str, note: str = "") -> None:
    s = load_status(ticket)
    s["current_stage"] = stage
    s["state"] = "failed"
    s["updated_at"] = now()
    save_status(ticket, s)
    add_history(ticket, stage, "failed", note)


def set_artifact(ticket: str, key: str, path: Path) -> None:
    s = load_status(ticket)
    s.setdefault("artifacts", {})[key] = str(path)
    s["updated_at"] = now()
    save_status(ticket, s)


def set_runner(ticket: str, detail: str) -> None:
    s = load_status(ticket)
    s.setdefault("runner", {})["last_command"] = detail
    s["updated_at"] = now()
    save_status(ticket, s)


def init_ticket(ticket: str, requirement: str, domain: str = "") -> None:
    ensure_base_dirs()
    config = load_project_config()
    resolved_domain = domain or config.get("default_domain", "backend")

    ensure_ticket_dirs(ticket)

    write(input_file(ticket), requirement.strip() + "\n")
    save_status(ticket, init_status(ticket, resolved_domain))
    set_artifact(ticket, "input", input_file(ticket))
    print(f"[OK] Initialized {ticket} at {run_path(ticket)} (domain={resolved_domain})")


def require_agent_file(name: str) -> str:
    content = read(AGENTS / name)
    if not content.strip():
        raise FileNotFoundError(f"Missing .ai/agents/{name}")
    return content.strip()


def file_ref_list(paths: List[Path], require_exists: bool = True) -> str:
    lines = []
    for path in paths:
        if require_exists and not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")
        lines.append(f"- {path.as_posix()}")
    return "\n".join(lines)


def ensure_non_empty_files(paths: List[Path], stage: str, ticket: str) -> None:
    missing = [p.as_posix() for p in paths if not p.exists() or not read(p).strip()]
    if missing:
        fail_stage(ticket, stage, f"Missing files: {', '.join(missing)}")
        raise FileNotFoundError(f"Missing or empty files: {', '.join(missing)}")


def get_ticket_domain(ticket: str) -> str:
    s = load_status(ticket)
    if s.get("domain"):
        return s["domain"]
    return load_project_config().get("default_domain", "backend")


def get_domain_config(ticket: str) -> Dict:
    config = load_project_config()
    domain = get_ticket_domain(ticket)
    return config.get("domains", {}).get(domain, {})


def get_role_skills(ticket: str, role: str) -> List[Path]:
    domain_cfg = get_domain_config(ticket)
    skill_paths = domain_cfg.get("skills", {}).get(role, [])
    return [Path(p) for p in skill_paths]


def load_skill_contents(paths: List[Path]) -> str:
    chunks = []
    for path in paths:
        content = read(path).strip()
        if not content:
            continue
        chunks.append(f"## Skill: {path.parent.name}\n\n{content}")
    return "\n\n".join(chunks)


def build_project_context(ticket: str) -> str:
    config = load_project_config()
    domain = get_ticket_domain(ticket)
    domain_cfg = config.get("domains", {}).get(domain, {})
    lines = [
        f"Project: {config.get('project_name', 'Unknown')}",
        f"Domain: {domain}",
        f"Base branch: {get_base_branch()}",
    ]
    paths = domain_cfg.get("paths", [])
    if paths:
        lines.append("Relevant paths:")
        for p in paths:
            lines.append(f"- {p}")
    return "\n".join(lines)


def build_role_prompt(ticket: str, role: str, task_instruction: str) -> str:
    role_file_map = {
        "architect": "architect.md",
        "developer": "developer.md",
        "reviewer": "reviewer.md",
        "qa": "qa.md",
    }
    role_prompt = require_agent_file(role_file_map[role])
    project_context = build_project_context(ticket)
    skill_content = load_skill_contents(get_role_skills(ticket, role))
    parts = [
        "# Role Instruction",
        role_prompt,
        "",
        "# Project Context",
        project_context,
    ]
    if skill_content:
        parts.extend(["", "# Domain Skills", skill_content])
    parts.extend(["", "# Task Instruction", task_instruction.strip()])
    return "\n".join(parts) + "\n"


def build_fix_context(ticket: str) -> Optional[Path]:
    path = review_report_path(ticket)
    if not path.exists() or not read(path).strip():
        return None

    try:
        review = json.loads(read(path))
    except Exception:
        return None

    issues = review.get("issues", [])
    if not isinstance(issues, list) or not issues:
        return None

    buckets = {"high": [], "medium": [], "low": [], "unknown": []}
    for item in issues:
        sev = str(item.get("severity", "unknown")).lower()
        if sev not in buckets:
            sev = "unknown"
        buckets[sev].append(item)

    lines = [
        "# Review Fix Context",
        "",
        "Use this file to fix review findings without re-implementing the whole feature.",
        "",
        f"Reviewer decision: {review.get('decision', 'unknown')}",
        "",
    ]

    for sev in ["high", "medium", "low", "unknown"]:
        if not buckets[sev]:
            continue
        lines.append(f"## {sev.capitalize()} Severity Issues")
        for idx, issue in enumerate(buckets[sev], start=1):
            lines.append(f"{idx}. File: {issue.get('file', 'unknown')}")
            lines.append(f"   Issue: {str(issue.get('message', '')).strip()}")
        lines.append("")

    summary = str(review.get("summary", "")).strip()
    if summary:
        lines.extend(["## Reviewer Summary", summary, ""])

    path = review_fix_context_path(ticket)
    write(path, "\n".join(lines).strip() + "\n")
    set_artifact(ticket, "review_fix_context", path)
    return path


def build_qa_fix_context(ticket: str) -> Optional[Path]:
    path = qa_report_path(ticket)
    if not path.exists() or not read(path).strip():
        return None

    try:
        qa = json.loads(read(path))
    except Exception:
        return None

    missing_tests = qa.get("missing_tests", [])
    risks = qa.get("risks", [])
    summary = str(qa.get("summary", "")).strip()

    if not missing_tests and not risks and not summary:
        return None

    lines = [
        "# QA Fix Context",
        "",
        "Use this file to address QA failures, missing tests, real defects, and delivery gaps.",
        "",
        f"QA decision: {qa.get('decision', 'unknown')}",
        "",
    ]

    if missing_tests:
        lines.append("## Missing Tests")
        for idx, item in enumerate(missing_tests, start=1):
            lines.append(f"{idx}. {item}")
        lines.append("")

    if risks:
        lines.append("## Risks Requiring Attention")
        for idx, item in enumerate(risks, start=1):
            lines.append(f"{idx}. {item}")
        lines.append("")

    if summary:
        lines.extend(["## QA Summary", summary, ""])

    path = qa_fix_context_path(ticket)
    write(path, "\n".join(lines).strip() + "\n")
    set_artifact(ticket, "qa_fix_context", path)
    return path


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

Important:
- Make the code changes directly in the repo.
- Write the report directly to the file above.
- Keep the report concise and factual.
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

Important:
- Preserve all existing content in implementation_report.md — only append.
- Make the code changes directly in the repo.
- Be explicit about how each critical issue was fixed.
- If QA identified missing tests, add them when feasible and report them clearly.
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
    set_artifact(ticket, "implementation_report", implementation_report_path(ticket))

    complete_stage(ticket, "dev_complete", "Implementation report verified.")
    print(f"[OK] Dev files verified for {ticket}")


def dev_fix_complete(ticket: str) -> None:
    update_stage(ticket, "dev_fix_complete")
    set_runner(ticket, "dev-fix-complete")

    ensure_non_empty_files(
        [implementation_report_path(ticket)], "dev_fix_complete", ticket
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


def current_outcome(ticket: str) -> Dict[str, Optional[str]]:
    review_decision = None
    qa_decision = None

    try:
        if review_report_path(ticket).exists():
            review_decision = json.loads(read(review_report_path(ticket))).get(
                "decision"
            )
    except Exception:
        pass

    try:
        if qa_report_path(ticket).exists():
            qa_decision = json.loads(read(qa_report_path(ticket))).get("decision")
    except Exception:
        pass

    return {"review": review_decision, "qa": qa_decision}


def next_action(ticket: str) -> str:
    outcome = current_outcome(ticket)
    current_stage = load_status(ticket).get("current_stage", "")

    # Architect
    if not task_spec_path(ticket).exists() or not read(task_spec_path(ticket)).strip():
        return "architect-prepare"

    if (
        not design_note_path(ticket).exists()
        or not read(design_note_path(ticket)).strip()
    ):
        return "architect-complete"

    if current_stage == "architect_prepare":
        return "architect-complete"

    # Review fail -> fix loop
    if outcome["review"] in {"request_changes", "block"}:
        if current_stage == "dev_fix_prepare":
            return "dev-fix-complete"
        return "dev-fix-prepare"

    # QA fail -> fix loop
    if current_stage == "dev_fix_complete":
        return "review-prepare"
    if outcome["qa"] == "fail":
        if current_stage == "dev_fix_prepare":
            return "dev-fix-complete"
        return "dev-fix-prepare"

    # After fix complete, always go back to review
    if current_stage == "dev_fix_complete":
        return "review-prepare"

    # Initial dev
    if (
        not implementation_report_path(ticket).exists()
        or not read(implementation_report_path(ticket)).strip()
    ):
        return "dev-prepare"

    if current_stage == "dev_prepare":
        return "dev-complete"

    # Review
    if (
        not review_report_path(ticket).exists()
        or not read(review_report_path(ticket)).strip()
    ):
        return "review-prepare"

    if current_stage == "review_prepare":
        return "review-complete"

    # QA after approved review
    if outcome["review"] == "approve":
        if (
            not qa_report_path(ticket).exists()
            or not read(qa_report_path(ticket)).strip()
        ):
            return "qa-prepare"

        if current_stage == "qa_prepare":
            return "qa-complete"

        if outcome["qa"] == "pass":
            return "done"

        if outcome["qa"] is None:
            return "qa-complete"

    return "done"


def run_named_step(ticket: str, step: str) -> None:
    mapping = {
        "architect-prepare": architect_prepare,
        "architect-complete": architect_complete,
        "dev-prepare": dev_prepare,
        "dev-fix-prepare": dev_fix_prepare,
        "dev-fix-complete": dev_fix_complete,
        "dev-complete": dev_complete,
        "review-prepare": review_prepare,
        "review-complete": review_complete,
        "qa-prepare": qa_prepare,
        "qa-complete": qa_complete,
    }
    if step == "done":
        print("Ticket looks ready. Review and merge manually.")
        return
    if step not in mapping:
        raise ValueError(f"Unknown step: {step}")
    mapping[step](ticket)


_PREPARE_STEP_PROMPT: Dict[str, object] = {
    "architect-prepare": architect_prompt_path,
    "dev-prepare": dev_prompt_path,
    "dev-fix-prepare": dev_fix_prompt_path,
    "review-prepare": review_prompt_path,
    "qa-prepare": qa_prompt_path,
}


def spawn_claude_wezterm(
    prompt_path: Path, cwd: str, wait_seconds: float = 4.0
) -> None:
    result = subprocess.run(
        [
            "wezterm",
            "cli",
            "spawn",
            "--cwd",
            cwd,
            "--",
            "claude",
            "--dangerously-skip-permissions",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[WARN] wezterm spawn failed: {result.stderr.strip()}", file=sys.stderr)
        return

    pane_id = result.stdout.strip()
    if not pane_id:
        print(
            "[WARN] Could not get WezTerm pane ID, skipping auto-paste.",
            file=sys.stderr,
        )
        return

    print(
        f"[AUTO] Spawned Claude in WezTerm pane {pane_id}. Waiting {wait_seconds}s for it to load..."
    )
    time.sleep(wait_seconds)

    prompt_text = prompt_path.read_text(encoding="utf-8").rstrip("\n")
    subprocess.run(
        ["wezterm", "cli", "send-text", "--pane-id", pane_id, "--no-paste"],
        input=prompt_text,
        text=True,
    )
    print(f"[AUTO] Prompt pasted into pane {pane_id}. Press Enter in Claude to submit.")


def next_step(ticket: str, execute: bool = False, run_auto: bool = False) -> None:
    step = next_action(ticket)
    if run_auto or execute:
        run_named_step(ticket, step)
        if run_auto and step in _PREPARE_STEP_PROMPT:
            prompt_path = _PREPARE_STEP_PROMPT[step](ticket)  # type: ignore[operator]
            spawn_claude_wezterm(prompt_path, str(Path.cwd()))
    else:
        print(step)


def show_status(ticket: str) -> None:
    print(json.dumps(load_status(ticket), indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reusable file-referenced prepare/complete workflow for local AI agent team."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Initialize a ticket run.")
    p_init.add_argument("ticket", help="Ticket ID, e.g. TICKET-123")
    p_init.add_argument("requirement", help="Initial input text")
    p_init.add_argument(
        "--domain",
        default="",
        help="Optional domain override, e.g. backend or frontend",
    )

    for cmd in [
        "architect-prepare",
        "architect-complete",
        "dev-prepare",
        "dev-fix-prepare",
        "dev-fix-complete",
        "dev-complete",
        "review-prepare",
        "review-complete",
        "qa-prepare",
        "qa-complete",
        "status",
    ]:
        p = sub.add_parser(cmd, help=f"Run {cmd}")
        p.add_argument("ticket", help="Ticket ID, e.g. TICKET-123")

    p_next = sub.add_parser("next", help="Show or run the next step.")
    p_next.add_argument("ticket", help="Ticket ID, e.g. TICKET-123")
    p_next.add_argument(
        "--run",
        action="store_true",
        help="Execute the next step instead of only printing it.",
    )
    p_next.add_argument(
        "--run-auto",
        action="store_true",
        help="Execute the next step and automatically open Claude in a new WezTerm tab with the prompt pre-loaded.",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "init":
            init_ticket(args.ticket, args.requirement, domain=args.domain)
        elif args.command == "architect-prepare":
            architect_prepare(args.ticket)
        elif args.command == "architect-complete":
            architect_complete(args.ticket)
        elif args.command == "dev-prepare":
            dev_prepare(args.ticket)
        elif args.command == "dev-fix-prepare":
            dev_fix_prepare(args.ticket)
        elif args.command == "dev-fix-complete":
            dev_fix_complete(args.ticket)
        elif args.command == "dev-complete":
            dev_complete(args.ticket)
        elif args.command == "review-prepare":
            review_prepare(args.ticket)
        elif args.command == "review-complete":
            review_complete(args.ticket)
        elif args.command == "qa-prepare":
            qa_prepare(args.ticket)
        elif args.command == "qa-complete":
            qa_complete(args.ticket)
        elif args.command == "status":
            show_status(args.ticket)
        elif args.command == "next":
            next_step(args.ticket, execute=args.run, run_auto=args.run_auto)
        else:
            parser.print_help()
            return 2
    except KeyboardInterrupt:
        print("\n[ABORTED]")
        return 130
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
